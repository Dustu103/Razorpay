# Ingestion Service — Low-Level Design (LLD)
# Feature 1 — Root-Cause Classifier

**Port:** 3001 · **Framework:** Go + Fiber v2 · **Language:** Go 1.22

### 1.1 Package Structure

```
ingestion-service/
├── cmd/
│   └── main.go              # Wires: DB → Queue → Fiber → Routes
├── internal/
│   ├── handlers/
│   │   └── webhook.go       # POST /api/v1/webhook
│   ├── models/
│   │   └── transaction.go   # WebhookPayload, Transaction, ClassificationJob, ErrorResponse
│   ├── db/
│   │   └── postgres.go      # Connect(), UpsertTransaction()
│   ├── queue/
│   │   └── redis.go         # New(), Enqueue()
│   └── routes/
│       └── routes.go        # Register(app, handler)
├── go.mod
└── Dockerfile
```

### 1.2 Handler: `WebhookHandler.Handle`

```
POST /api/v1/webhook

1. BodyParser → WebhookPayload
2. Clean: uppercase status_code, normalise synonyms, clamp retry_count
3. Parse timestamps (preserve null)
4. db.UpsertTransaction() — atomic ON CONFLICT DO NOTHING
   ├── isNew=false → return 200 "duplicate"
   └── isNew=true  → queue.Enqueue(ClassificationJob{TransactionID})
5. Return 202 Accepted
```

### 1.3 DB Interface

```go
// UpsertTransaction performs atomic dedup upsert.
// Returns ("", false, nil) if duplicate.
func (d *DB) UpsertTransaction(ctx, *Transaction) (id string, isNew bool, err error)
```

### 1.4 Queue Interface

```go
// Enqueue pushes a ClassificationJob to Redis via RPUSH (tail).
func (q *Queue) Enqueue(ctx, ClassificationJob) error
```

---

## 4. Error Handling Strategy

| Scenario | Ingestion |
|----------|-----------|
| Malformed request | 400 |
| DB error | 500 |
| Redis error | 500 |
| Duplicate webhook | 200 (silent) |

---

## 5. Configuration (Environment Variables)

| Variable | Service | Default |
|----------|---------|---------|
| `DATABASE_URL` | all | required |
| `REDIS_URL` | ingestion | required |
| `QUEUE_NAME` | ingestion | `classification_jobs` |
| `INGESTION_PORT` | ingestion | `3001` |
| `APP_ENV` | all | `development` |
