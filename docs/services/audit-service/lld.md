# Audit Service — Low-Level Design (LLD)
# Feature 1 — Root-Cause Classifier

**Port:** 3003 · **Framework:** Go + Fiber v2 · **Read-only**

### 3.1 Package Structure

```
audit-service/
├── cmd/
│   └── main.go
├── internal/
│   ├── handlers/
│   │   └── classifications.go  # List(), GetByID()
│   ├── models/
│   │   └── models.go           # ClassificationView, ListFilter, ErrorResponse
│   ├── db/
│   │   └── postgres.go         # ListClassifications(), GetClassification()
│   └── routes/
│       └── routes.go
├── go.mod
└── Dockerfile
```

### 3.2 DB Interface

```go
// ListClassifications returns paginated joined results.
// filter.Cause = "" → all causes; filter.Layer = nil → all layers.
func (d *DB) ListClassifications(ctx, ListFilter) ([]ClassificationView, error)

// GetClassification returns a single joined row by classification UUID.
func (d *DB) GetClassification(ctx, id string) (*ClassificationView, error)
```

### 3.3 ClassificationView (joined model)

Joins `classifications` and `transactions` so the frontend gets everything in one call:

```go
type ClassificationView struct {
    // From classifications
    ID, TransactionID, Layer, Cause, Confidence, Reasoning, RecommendedAction, ModelVersion

    // From transactions (joined)
    GatewayTransactionID, StatusCode, NPCIResponseCode, BankResponseCode,
    Amount, CustomerBank, RetryCountSoFar, CreatedAt
}
```

---

## 4. Error Handling Strategy

| Scenario | Audit |
|----------|-------|
| Malformed request | 400 |
| DB error | 500 |

---

## 5. Configuration (Environment Variables)

| Variable | Service | Default |
|----------|---------|---------|
| `DATABASE_URL` | all | required |
| `AUDIT_PORT` | audit | `3003` |
| `APP_ENV` | all | `development` |
