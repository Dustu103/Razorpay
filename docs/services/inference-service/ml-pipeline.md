# Machine Learning Pipeline (Inference Service)

The `inference-service` is entirely decoupled from the business logic orchestration. Its sole responsibility is to expose machine learning models for sub-10ms predictions via HTTP endpoints. 

This document outlines the pipeline, features, and algorithms for all ML models deployed in the Inference Gateway.

## 1. Layer 2: Payment Failure Root-Cause (XGBoost)
*(Handles the primary layer of failure classification)*

* **Algorithm**: Extreme Gradient Boosting (`xgboost`)
* **Objective**: Multi-class classification (Predicting `soft_decline`, `hard_decline`, `fraud_filter_block`, `gateway_fault`)
* **Input Features**:
  * `AmountPaise` (Continuous)
  * `StatusCode` (Categorical)
  * `RetryCountSoFar` (Ordinal)
* **Output**: Calibrated confidence scores.
* **Storage**: `/app/models/ml/layer2_payment_failure_model.pkl`
* **Performance Benchmark**: ~95% Accuracy, 5-8ms Latency

## 2. Feature B: Intelligent Retry Routing (Random Forest)
*(Determines if a soft decline should be retried automatically)*

* **Algorithm**: Scikit-Learn `RandomForestClassifier` (100 estimators)
* **Objective**: Binary classification (Predicts probability of a successful payment on retry)
* **Input Features**:
  * `hour_of_day`, `day_of_month` (Temporal trends)
  * `failure_cause_encoded` (Contextual severity)
  * `payment_method_encoded` (Method viability)
  * `retry_count`, `time_since_failure_mins` (Recency decay)
* **Threshold**: Success probability must exceed **0.60** to schedule a retry.
* **Storage**: `/app/models/ml/feature_b.joblib`
* **Performance Benchmark**: ~75% Accuracy on unseen data, ~15ms Latency

## 3. Feature C: Dunning Optimization (Random Forest)
*(Determines the optimal communication channel for revenue recovery)*

* **Algorithm**: Scikit-Learn `RandomForestClassifier` (100 estimators)
* **Objective**: Probability distribution over communication success.
* **Input Features**:
  * `channel_encoded` (Email vs. SMS vs. Push)
  * `time_since_failure_mins` (Urgency factor)
  * `customer_tenure_months` (Loyalty factor)
  * `prior_payment_success_rate` (Historical reliability)
* **Orchestration Rule**: If `EvaluateRetry` fails, this model determines whether to send an SMS or Email based on the highest yielded probability.
* **Storage**: `/app/models/ml/feature_c.joblib`
* **Performance Benchmark**: ~88% Accuracy on unseen data, ~15ms Latency

## 4. Feature D: False Decline Detection (Random Forest)
*(Overrides overly aggressive fraud filters)*

* **Algorithm**: Scikit-Learn `RandomForestClassifier`
* **Objective**: Identifies genuine customers who were incorrectly blocked by a `fraud_filter_block`.
* **Input Features**:
  * `amount` (Anomaly detection)
  * `transaction_velocity` (High velocity = higher true-fraud risk)
  * `is_known_device`, `ip_risk_score` (Identity validation)
  * `merchant_category`, `transaction_hour`
* **Orchestration Rule**: Requires a strict `0.85+` likelihood threshold to override a hard fraud block with a `reverify_and_reverse` action.
* **Storage**: `/app/models/ml/feature_d.joblib`
* **Performance Benchmark**: ~97.6% Accuracy on unseen data, ~10ms Latency

## 5. Feature E: Causal Net-EV Drop-Off Recovery Engine
*(Decoupled causal intervention scoring for checkout abandonments)*

* **Architecture**: Dual Causal Inference (S-Learner + Action-Conditioned RTO Model)
* **Algorithms**:
  * **S-Learner**: LightGBM Classifier with explicit base-feature $\times$ action interaction terms estimating $P(Y=1 \mid X, A)$ across $A \in \{\text{none}, \text{whatsapp}, \text{sms}, \text{email}\}$.
  * **RTO Risk Model**: LightGBM Classifier conditioned on action estimating $P(\text{RTO}=1 \mid X, A, Y=1)$ on converted checkouts.
  * **Propensity Estimator**: Multinomial Logistic Regression modeling logging policy $\hat{\pi}_0(A \mid X)$.
* **Input Features**:
  * Continuous: `cart_value`, `duration_sec`, `attempt_count`, `events_count`, `sequence_entropy`, `mean_inter_event_time`, `is_returning_customer`
  * Categorical: `payment_method` (OneHot), `device` (OneHot), `diagnosis` (OneHot)
* **Exact Economic Engine**:
  $$\Delta\Pi_a = P_a[(1 - r_a)(CM - D_a) - r_a K_{RTO}] - P_0[(1 - r_0)CM - r_0 K_{RTO}] - K_a$$
* **Orchestration Rule**: Recommends $\operatorname{argmax}_a(\Delta\Pi_a)$ if $\Delta\Pi_a > 0$; strictly commands `NO_ACTION` (suppression) otherwise to avoid cannibalizing organic checkout completions.
* **Storage**:
  * `/app/models/ml/causal_s_model.pkl`
  * `/app/models/ml/causal_rto_model.pkl`
  * `/app/models/ml/causal_preprocessor_encoder.pkl`
  * `/app/models/ml/causal_propensity_clf.pkl`
* **Performance Benchmark**: 0.711 ROC-AUC, 0.513 F1 (calibrated), 71.6% RTO Accuracy, ~88% of maximum Oracle profit captured.

---

## Offline Training Methodology
Models are strictly trained **offline** inside the `data/scripts/` directory to prevent out-of-memory errors on the production API.

**Directory Structure:**
* `data/scripts/chargeback/` → Dispute pre-emption models
* `data/scripts/classification/` → Root-cause classification models
* `data/scripts/revenue_recovery/` → Smart retries, dunning, false decline models
* `data/scripts/dropoffs/` → Causal drop-off simulator, S-Learner, and RTO models

**Example Training Pipeline:**
1. Generate causal data: `python data/scripts/dropoffs/generate_synthetic_dropoffs.py --samples 50000`
2. Train causal models: `python data/scripts/dropoffs/train_causal_recovery_pipeline.py`
3. Export using `joblib.dump()` to `models/ml/` (which mounts to `/app/models/ml` in the container)
4. Verify economic invariants: `python tests/e2e/dropoff-service/test_economic_invariants.py`
