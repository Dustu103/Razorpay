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

---

## Offline Training Methodology
Models are strictly trained **offline** inside the `data/scripts/` directory to prevent out-of-memory errors on the production API.

**Example Pipeline:**
1. Generate synthetic failure data (`data/scripts/revenue_recovery/train_feature_b.py`)
2. Fit `RandomForestClassifier` using `scikit-learn`
3. Export using `joblib.dump()` to `models/ml/`
4. The Inference Service loads all `.joblib` files into a global Python memory space on startup.
