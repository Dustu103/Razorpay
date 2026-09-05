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

---

## Predict False Decline (Layer 2)
*(Used to identify genuine transactions that were mistakenly blocked by fraud filters)*

**Endpoint**: `POST /predict/false-decline`

**Request Body**:
```json
{
  "amount": 1000,
  "transaction_velocity": 2,
  "is_known_device": 1,
  "ip_risk_score": 0.1,
  "merchant_category": "electronics",
  "transaction_hour": 14
}
```

**Response (200 OK)**:
```json
{
  "false_decline_likelihood": 0.97,
  "recommended_action": "reverify_and_reverse",
  "contributing_features": [
    "low_ip_risk",
    "low_transaction_velocity",
    "known_device",
    "normal_amount",
    "normal_business_hours"
  ]
}
```

---

## Predict Checkout Drop-Off Intervention (Causal Engine)
Runs the dual Causal S-Learner and RTO model to determine whether intervening on an abandoned checkout yields a positive Net Expected Value ($\Delta\Pi$), and selects the optimal channel.

**Endpoint**: `POST /predict/intervention`

**Request Body**:
```json
{
  "session_id": "sess_tech_001",
  "diagnosis": "upi_app_switch_abort",
  "cart_value": 3500.0,
  "merchant_margin": 0.35,
  "duration_sec": 45,
  "attempt_count": 2,
  "events_count": 5,
  "event_sequence": "cart,pay_select,upi_click,abort",
  "payment_method": "upi",
  "device": "mobile_android",
  "is_returning_customer": 1,
  "rto_cost_estimate": 250.0,
  "incentive_amount": 0.0
}
```

**Response (200 OK)**:
```json
{
  "action": "whatsapp",
  "risk_score": 0.124,
  "rto_rate_organic": 0.121,
  "recovery_prob": 0.582,
  "organic_recovery_prob": 0.284,
  "incremental_lift": 0.298,
  "expected_profit": 142.50,
  "recovery_message": "Arre yaar! 😅 Aapka payment thoda ruk gaya. UPI app switch ho gaya tha. Abhi complete karein: https://rzp.io/r/sess_tech",
  "reasoning": "RECOMMEND WHATSAPP (ΔΠ=+₹142.50, r_a=0.124). P0=0.284 r0=0.121 | ΔΠ(WA)=₹142.50 ΔΠ(SMS)=₹98.20 ΔΠ(Email)=₹45.10"
}
```

### Response Fields
* `action`: Recommended intervention channel (`whatsapp`, `sms`, `email`, or `NO_ACTION` if all $\Delta\Pi \le 0$).
* `risk_score`: Action-conditioned return-to-origin probability ($r_a$).
* `rto_rate_organic`: Baseline return-to-origin probability without intervention ($r_0$).
* `recovery_prob`: Conditional recovery probability under chosen action ($P_a$).
* `organic_recovery_prob`: Baseline recovery probability ($P_0$).
* `incremental_lift`: Net causal treatment lift $\tau_a = \max(0, P_a - P_0)$.
* `expected_profit`: Exact net economic value in INR ($\Delta\Pi_a$).
* `recovery_message`: Localized Hinglish message generated for the customer.
* `reasoning`: Mathematical trace showing P0, r0, and $\Delta\Pi$ across all evaluated channels.

---

## Predict Intelligent Retry Routing (Feature B)
Calculates optimal retry probability and determines if an automated re-attempt is viable based on failure cause, time elapsed, and bank operating cycles.

**Endpoint**: `POST /predict/retry`

**Request Body**:
```json
{
  "hour_of_day": 14,
  "day_of_month": 5,
  "failure_cause_encoded": 0,
  "payment_method_encoded": 2,
  "retry_count": 1,
  "time_since_failure_mins": 45
}
```

**Response (200 OK)**:
```json
{
  "retry_success_probability": 0.72,
  "recommended_action": "retry_scheduled"
}
```

---

## Predict Dunning Optimization & Urgency Routing (Feature C)
Selects the optimal re-engagement channel (WhatsApp / SMS / Email) conditioned on customer tenure, time since failure, and NACH consequence severity tiers.

**Endpoint**: `POST /predict/dunning`

**Request Body**:
```json
{
  "channel_encoded": 0,
  "time_since_failure_mins": 30,
  "customer_tenure_months": 18,
  "prior_payment_success_rate": 0.88,
  "product_type": "loan_emi",
  "consequence_severity": "credit_score_risk"
}
```

**Response (200 OK)**:
```json
{
  "payment_probability": 0.63,
  "recommended_channel": "whatsapp",
  "consequence_severity": "credit_score_risk",
  "urgency_tier": "critical"
}
```

### Response Fields
* `payment_probability`: Calibrated probability that the customer settles via the recommended channel.
* `recommended_channel`: Re-engagement channel selected (`whatsapp`, `sms`, `email`, or `push`). Overridden to `whatsapp` on `critical` urgency, or `sms` on `elevated` urgency.
* `consequence_severity`: Preserved consequence severity tag for audit trails (`credit_score_risk`, `investment_lapse_risk`, `policy_lapse_risk`, or empty string).
* `urgency_tier`: Deterministic governor tier (`standard`, `elevated`, or `critical`).


