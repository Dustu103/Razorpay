# NACH Mandate Recovery Service — Low Level Design (LLD)

## Package Structure

```
backend/nach-recovery-service/
├── cmd/
│   └── server/
│       └── main.go                  # Fiber HTTP routes, graceful shutdown & worker wiring
├── internal/
│   ├── governor/
│   │   ├── governor.go              # Pure deterministic evaluation logic
│   │   └── governor_test.go         # Table-driven unit tests
│   ├── worker/
│   │   └── worker.go                # Background batch poller & thread-safe metrics cache
│   ├── models/
│   │   └── models.go                # Request/Response DTOs and domain constants
│   └── db/
│       └── postgres.go              # Database connection pool & transaction queries
├── Dockerfile                       # Multi-stage alpine build
├── go.mod                           # Go dependencies
└── go.sum
```

---

## API Contracts

### 1. `GET /health`
* **Response (200 OK):**
```json
{
  "status": "online",
  "service": "nach-recovery-service",
  "port": "3007"
}
```

### 2. `GET /api/v1/nach-metrics`
* **Response (200 OK):**
```json
{
  "total_mandates_evaluated": 100,
  "governor_pre_emptions": 46,
  "unretryable_hard_stops": 21,
  "bank_retry_fees_saved_inr": 28500.00,
  "revenue_recovered_inr": 367117.00,
  "recent_evaluations": [
    {
      "transaction_id": "ae99080b-6c30-4330-8fa8-1d4d46e931eb",
      "action": "credit_score_risk_escalate",
      "governor_stopped": true,
      "urgency_tier": "critical",
      "recommended_channel": "whatsapp",
      "consequence_severity": "credit_score_risk",
      "confidence": 1.0,
      "reasoning": "[Governor · EMI Credit Risk] 31 days past due date. Immediate WhatsApp intervention forced.",
      "recovery_probability": 0.72
    }
  ]
}
```

### 3. `POST /api/v1/evaluate-mandate`
* **Request Body:**
```json
{
  "transaction_id": "txn-emi-test-01",
  "payment_rail": "nach",
  "product_type": "loan_emi",
  "mandate_value": 15000.0,
  "cause": "insufficient_funds",
  "consecutive_failure_count": 1,
  "days_since_due_date": 28
}
```
* **Response (200 OK):**
```json
{
  "transaction_id": "txn-emi-test-01",
  "action": "credit_score_risk_escalate",
  "governor_stopped": true,
  "urgency_tier": "critical",
  "recommended_channel": "whatsapp",
  "consequence_severity": "credit_score_risk",
  "confidence": 1.0,
  "reasoning": "[Governor · EMI Credit Risk] 28 days past due date. Credit bureau reporting begins at 30 days. Immediate WhatsApp intervention forced to protect borrower credit score.",
  "recovery_probability": 0.72
}
```
