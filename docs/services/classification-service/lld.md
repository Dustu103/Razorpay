# Classification Service — Low-Level Design (LLD)
# Feature 1 — Root-Cause Classifier

**Framework:** Go 1.22 (event-driven queue worker)

---

## 1. Package Structure

```
classification-service/
├── cmd/
│   └── main.go              # Wires: DB → Redis → Worker.Run()
├── internal/
│   ├── nach/
│   │   ├── stopping.go      # Layer 0: NACH Mandate Stopping Policy (pure function)
│   │   └── stopping_test.go # Unit tests for AMC SIP, EMI 28-day & insurance guards
│   ├── layer1/
│   │   └── rule.go          # Layer 1: RBI 24h notification compliance rule
│   ├── layer2/
│   │   └── client.go        # Layer 2: HTTP client for inference-service ML endpoints
│   ├── layer3/
│   │   └── llm.go           # Layer 3: Rail-aware multi-LLM (Groq/Gemini/Fallback)
│   ├── layer4/
│   │   └── ensemble.go      # Layer 4: Dynamic confidence calibration & arbitration
│   ├── worker/
│   │   ├── worker.go        # Queue polling, orchestration & post-ensemble routing
│   │   └── worker_test.go   # Unit tests for fallback and consequence mapping
│   ├── models/
│   │   └── models.go        # Transaction, ClassificationResult, NACH & Action constants
│   └── db/
│       └── postgres.go      # GetTransaction(), SaveClassification()
├── tests/
│   └── unit/                # Integration unit tests (layer1, layer2, nach, worker)
├── go.mod
└── Dockerfile
```

---

## 2. Worker Loop & Pipeline Orchestration

```go
func (w *Worker) processJob(ctx context.Context, job models.ClassificationJob) error {
    txn := w.db.GetTransaction(ctx, job.TransactionID)

    // ── Layer 0: NACH Stopping Policy ──
    if stopping := nach.Check(txn); stopping.ShouldStop {
        return w.db.SaveClassification(ctx, stopping.Result)
    }

    // ── Layer 1: RBI Notification Compliance ──
    if l1Result := layer1.Classify(txn); l1Result != nil {
        return w.db.SaveClassification(ctx, l1Result)
    }

    // ── Layers 2 & 3: Concurrent ML + LLM ──
    var l2Result *models.ClassificationResult
    var l3Result *models.ClassificationResult

    var wg sync.WaitGroup
    wg.Add(2)
    go func() { defer wg.Done(); l2Result, _ = layer2.Classify(txn) }()
    go func() { defer wg.Done(); l3Result, _ = layer3.Classify(txn) }()
    wg.Wait()

    // ── Layer 4: Dynamic Confidence Ensemble ──
    result := layer4.Ensemble(l2Result, l3Result)

    // ── Post-Ensemble Orchestration ──
    // 1. Feature D: False Decline Recovery
    if result.Cause == models.CauseFraudFilterBlock {
        if likelihood, action, _ := layer2.CheckFalseDecline(txn); likelihood > 0.85 {
            result.RecommendedAction = action
        }
    }

    // 2. Features B & C: Retry & Product-Aware Dunning
    if isSoftCause(result.Cause) {
        prob, action, _ := layer2.EvaluateRetry(txn)
        if action == "retry_scheduled" {
            result.RecommendedAction = models.ActionRetryScheduled
        } else {
            _, channel, _ := layer2.EvaluateDunning(txn)
            // NACH Overrides
            if txn.PaymentRail == "nach" && txn.ProductType == "loan_emi" && consequenceSeverity(txn) == "credit_score_risk" {
                channel = "whatsapp"
            }
            result.RecommendedAction = "trigger_dunning_" + channel
        }
    }

    // 3. NACH Hard Stops (Unretryable)
    if isNACHHardCause(result.Cause) {
        result.RecommendedAction = models.ActionNACHDoNotRetry
    }

    return w.db.SaveClassification(ctx, result)
}
```

---

## 3. Core Component Interfaces

### 3.1 Layer 0: NACH Stopping Policy (`internal/nach/stopping.go`)
```go
type StoppingResult struct {
    ShouldStop bool
    Result     *models.ClassificationResult
}

// Check evaluates mandate cancellation rules and factual credit risk.
// Pure function: deterministic, zero network dependencies.
func Check(txn *models.Transaction) StoppingResult
```

### 3.2 Layer 1: RBI Compliance Rule (`internal/layer1/rule.go`)
```go
// Classify verifies notification was dispatched at least 24 hours prior to scheduled debit.
func Classify(txn *models.Transaction) *models.ClassificationResult
```

### 3.3 Layer 3: Rail-Aware LLM Client (`internal/layer3/llm.go`)
```go
// Classify constructs rail-specific prompts (NACH vs UPI/Card) and routes through Groq/Gemini/Fallback.
func Classify(txn *models.Transaction) (*models.ClassificationResult, error)
```

---

## 4. Extended Transaction Data Model

```go
type Transaction struct {
    ID                        string     `json:"id"`
    PaymentMethod             string     `json:"payment_method"`
    ErrorCode                 *string    `json:"error_code"`
    ErrorDescription          *string    `json:"error_description"`
    MandateNotificationSentAt *time.Time `json:"mandate_notification_sent_at"`
    DebitScheduledAt          *time.Time `json:"debit_scheduled_at"`

    // NACH Mandate Extensions
    PaymentRail              string     `json:"payment_rail"`               // "nach" | "upi" | "card"
    ProductType              string     `json:"product_type"`              // "sip" | "loan_emi" | "insurance_premium"
    ConsecutiveFailureCount  int        `json:"consecutive_failure_count"` // 0..N
    DaysSinceDueDate         *int       `json:"days_since_due_date"`       // Days past loan due date
}
```

---

## 5. Configuration (Environment Variables)

| Variable | Service | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | all | required | PostgreSQL connection string |
| `REDIS_URL` | classification | required | Redis connection string |
| `QUEUE_NAME` | classification | `classification_jobs` | Redis BLPOP queue name |
| `ML_SERVICE_URL` | classification | `http://inference-service:8000` | Local ML inference gateway |
| `GROQ_API_KEY` | classification | optional | Groq Llama-3 API Key |
| `GEMINI_API_KEY` | classification | optional | Google Gemini API Key |
