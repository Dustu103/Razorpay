# Inference Gateway API Reference

Base URL: `http://inference-service:8000`

## Health Check
Validates that the service is running and all machine learning models have been successfully loaded into memory.

**Endpoint**: `GET /health`

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "models_loaded": {
    "payment_model": true,
    "chargeback_model": true
  }
}
```

---

## Predict Chargeback Win Probability
Runs the multi-model ensemble on transaction metadata and evidence flags to calculate the statistical probability of winning a chargeback dispute if represented.

**Endpoint**: `POST /predict/chargeback`

**Request Body**:
```json
{
  "reason_code": "visa_10.4",
  "network": "visa",
  "has_3ds_auth": 1,
  "has_delivery_proof": 0,
  "has_avs_cvv_match": 1,
  "has_ip_device_fingerprint": 1,
  "has_prior_comms": 0,
  "days_remaining": 14,
  "days_since_transaction": 12,
  "repeat_dispute_count": 0,
  "transaction_amount_inr": 4500.0,
  "merchant_category": "ecommerce"
}
```

**Response (200 OK)**:
```json
{
  "win_probability": 0.8539,
  "variance": 0.1052,
  "disagreement_flag": false,
  "individual_predictions": {
    "LogisticRegression": 0.8101,
    "RandomForest": 0.8992,
    "LightGBM": 0.8524
  },
  "recommended_action": "auto_submit",
  "top_features": ["has_3ds_auth", "days_remaining", "transaction_amount_inr"],
  "variance_threshold": 0.15
}
```

### Response Fields
- `win_probability`: The weighted average prediction across all active models in the ensemble.
- `variance`: The standard deviation of the predictions. High variance indicates structural disagreement between the underlying models.
- `disagreement_flag`: `true` if the variance exceeds the calibrated threshold, signaling uncertainty.
- `recommended_action`: Deterministic heuristic suggestion (`auto_submit`, `review`, `deflect_via_refund`, `await_merchant_approval`).
- `top_features`: The top 3 features extracted via TreeSHAP that influenced the positive probability. Useful for LLM context injection.

---

## Predict Payment Failure (Layer 2)
*(Currently used by the classification service)*

**Endpoint**: `POST /predict/payment`

**Request Body**:
```json
{
  "id": "txn_P8xL9a",
  "status_code": "FAILED",
  "bank_response_code": "51",
  "npci_response_code": "U09",
  "amount_paise": 2500,
  "issuer_bank": "HDFC",
  "retry_count_so_far": 1
}
```

**Response (200 OK)**:
```json
{
  "transaction_id": "txn_P8xL9a",
  "layer": 2,
  "cause": "soft_decline",
  "confidence": 0.89,
  "reasoning": "L2_ML_PREDICTION_SOFT_DECLINE",
  "recommended_action": "retry_scheduled",
  "model_version": "scikit-learn-rf-v1"
}
```
