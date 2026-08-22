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
│   │   └── stub.go          # Classify(txn) → (*ClassificationResult, error)
│   ├── models/
│   │   └── models.go        # Transaction, ClassificationJob, ClassificationResult, cause constants
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
        
        result = layer1.Classify(txn)           // pure function, always first
        if result == nil {
            result, err = layer2.Classify(txn)  // stub or real LLM
            if err != nil {
                result = fallback(txn)           // soft_decline, confidence=0
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

### 2.4 Layer 2 Interface (stub → real LLM)

```go
// Classify returns a classification or an error.
// Replace stub body with LLM API call + schema validation + retry.
func Classify(txn *models.Transaction) (*models.ClassificationResult, error)
```

**To add the real LLM:** replace only the body of `layer2/stub.go:Classify()`. No other files change.

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
