# Machine Learning Pipeline Architecture

**Version:** 2.0  
**Status:** Implemented  
**Scope:** Layer 2 (Random Forest Classifier) & Layer 4 (Ensemble Tie-Breaker)

---

## 1. Executive Summary

This document details the Machine Learning lifecycle powering the **Layer 2 Classifier** in the Razorpay Payment Failure Classification system. To achieve sub-millisecond inference and 96%+ raw accuracy on structured transaction metadata, we employ a Random Forest model trained on synthetic payment failure data. 

This model operates within a **Mixture-of-Experts (MoE)** architecture, running concurrently with a General LLM (Layer 3) to provide domain-specific intelligence.

---

## 2. Data Engineering & Feature Pipeline

The ML model relies on structured tabular data extracted from the incoming webhook payload. 

### 2.1 Feature Selection
The following categorical and numerical features are extracted for the model:
- `amount_paise` (Numerical): The transaction amount. High-value transactions often trigger distinct issuer fraud filters.
- `retry_count_so_far` (Numerical): The number of attempts. Crucial for distinguishing between transient `soft_decline` and permanent `hard_decline`.
- `bank_response_code` (Categorical): The issuer's specific failure reason (e.g., `51` for Insufficient Funds, `59` for Fraud).
- `npci_response_code` (Categorical): The NPCI switch code (e.g., `U09`, `ZD`).
- `customer_bank` (Categorical): The issuing bank identifier, used to learn bank-specific decline behaviors.

### 2.2 Synthetic Data Generation (`datasets/scripts/generate_chaos_dataset.py`)
Because real payment failures are highly imbalanced (failures are rare, and `soft_decline` makes up 80%+ of failures), we bootstrap the initial model using a synthetically generated dataset.
1. **Base Generation:** We generate realistic transaction payloads across 5 target labels (`soft_decline`, `hard_decline`, `gateway_fault`, `fraud_filter_block`, `notification_compliance_block`).
2. **Chaos Injection:** We introduce realistic noise (null values, rare banks, unusual response codes) to prevent the model from overfitting to clean data.
3. **Class Balancing (SMOTE):** During training, if the dataset becomes highly skewed towards `soft_decline`, we apply Synthetic Minority Over-sampling Technique (SMOTE) to synthetically balance the minority classes (like `fraud_filter_block`).

---

## 3. Model Training & Validation

### 3.1 Algorithm Choice: Random Forest
We selected **Random Forest** (via `scikit-learn`) over Deep Learning or XGBoost for the following reasons:
1. **Explainability:** Tree-based models allow us to extract feature importance (e.g., proving that `bank_response_code` is the highest-weight feature).
2. **Inference Latency:** Random Forest inference on tabular data is deterministic and executes in microseconds, perfectly suiting our strict SLA for Layer 2.
3. **Confidence Calibration:** `predict_proba()` provides a mathematically sound confidence score for the Ensemble tie-breaker.

### 3.2 Training Pipeline (`datasets/scripts/train_layer2_model.py`)
1. **Preprocessing:** 
   - Categorical variables are One-Hot Encoded.
   - Numerical variables are standardized using `StandardScaler`.
2. **Pipeline Compilation:** The preprocessor and the `RandomForestClassifier` are bundled into a single `sklearn.pipeline.Pipeline` object.
3. **Training & Export:** The model is trained on the synthetic chaos dataset. The full pipeline is then serialized using `joblib` into `layer2_payment_failure_model.pkl`.

---

## 4. Inference & The Ensemble (Layer 4)

In production, the ML model is wrapped in a FastAPI service (`ml-service`). 

### 4.1 Concurrent Inference
When a job is picked up by the Go worker, it simultaneously issues two asynchronous RPC calls:
1. **Layer 2 (ML):** Returns `predicted_cause` and `confidence_score` in < 10ms.
2. **Layer 3 (LLM):** Returns `predicted_cause` and semantic `reasoning` in ~500ms-2s.

### 4.2 The Tie-Breaker Logic
The Go worker implements an **Ensemble Tie-Breaker (Layer 4)** to merge these results:
- **Agreement:** If both models output `soft_decline`, the confidence is artificially boosted to `0.99`.
- **ML Override:** If they disagree, but the ML model's confidence is very high (e.g., `> 0.85`), the ML model wins. *Why?* The ML model was explicitly trained on our domain-specific taxonomy, whereas the LLM is a generalist.
- **LLM Tie-Break:** If the ML model's confidence is low (`< 0.85`), it implies an out-of-distribution edge case. The system defers to the LLM's zero-shot reasoning capabilities.

---

## 5. Feedback Loop & Retraining (Future Scope)

To ensure the model degrades gracefully as bank response codes evolve:
1. **Shadow Logging:** The `classifications` table stores the actual Layer 2 confidence, Layer 3 output, and the final Layer 4 decision.
2. **Human-in-the-Loop:** Cases where the ML model had low confidence (`< 0.50`) are flagged for manual SRE review.
3. **Continuous Training:** Validated edge cases are appended to the training CSV, and a CI/CD pipeline triggers a nightly retraining of the `.pkl` artifact.
