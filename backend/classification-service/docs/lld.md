# Classification Service — Low-Level Design (LLD)
# Feature 1 — Root-Cause Classifier

**Framework:** Go 1.22 (no HTTP server — worker only)

### 2.1 Package Structure

```
classification-service/
├── cmd/
│   └── main.go              # Wires: DB → Redis → Worker.Run()
├── internal/
│   ├── worker/
│   │   └── worker.go        # BLPOP loop → processJob()
│   ├── layer1/
│   │   └── rule.go          # Classify(txn) → *ClassificationResult | nil
│   ├── layer2/
│   │   └── stub.go          # Classify(txn) → (*ClassificationResult, error) [Fine-tuned small model]
│   ├── layer3/
│   │   └── llm.go           # Classify(txn) → (*ClassificationResult, error) [General LLM fallback]
│   ├── models/
│   │   └── models.go        # Transaction, ClassificationJob, ClassificationResult, constants (incl. thresholds)
│   └── db/
│       └── postgres.go      # Connect(), GetTransaction(), SaveClassification()
├── go.mod
└── Dockerfile
```

### 2.2 Worker Loop

```go
// Pseudocode
func (w *Worker) Run(ctx) {
    for {
        job = redis.BLPOP(ctx, 5s, queueName)
        txn = db.GetTransaction(job.TransactionID)
        
        result = layer1.Classify(txn)           // Layer 1: pure function, deterministic rule
        if result == nil {
            result, err = layer2.Classify(txn)  // Layer 2: fast fine-tuned classifier
            
            // Check confidence against action-specific thresholds
            if result.Confidence < getThresholdForAction(result.RecommendedAction) {
                l3Result, err := layer3.Classify(txn) // Layer 3: general LLM fallback
                if err == nil {
                    result = l3Result
                }
            }
        }
        db.SaveClassification(result)
    }
}
```

### 2.3 Layer 1 Interface

```go
// Classify is a pure function. Returns nil = fall through to Layer 2.
func Classify(txn *models.Transaction) *models.ClassificationResult
```

### 2.4 Layer 2 Interface (Fine-tuned model)

```go
// Classify simulates a fine-tuned model (e.g. Qwen 2.5 7B).
// Returns a categorical reasoning and a confidence score.
func Classify(txn *models.Transaction) (*ClassificationResult, error)
```

### 2.5 Layer 3 Interface (General LLM Fallback)

```go
// Classify simulates a general LLM (e.g. GPT-4o).
// Invoked only when Layer 2's confidence is below the threshold for its proposed action.
// Generates verbose reasoning.
func Classify(txn *models.Transaction) (*ClassificationResult, error)
```

---

## 4. Error Handling Strategy

| Scenario | Classification |
|----------|---------------|
| DB error | log + skip (job lost*) |
| Redis error | log + retry loop |
| Layer 2 error | fallback classification |

> *Future: dead-letter queue for classification failures

---

## 5. Configuration (Environment Variables)

| Variable | Service | Default |
|----------|---------|---------|
| `DATABASE_URL` | all | required |
| `REDIS_URL` | classification | required |
| `QUEUE_NAME` | classification | `classification_jobs` |
| `APP_ENV` | all | `development` |
