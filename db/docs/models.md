# Backend — Data Models Reference
# Feature 1 — Root-Cause Classifier

---

## Ingestion Service Models

### `WebhookPayload`
Root envelope from Razorpay webhook.
```go
type WebhookPayload struct {
    Event   string         // "payment.failed"
    Payload PaymentPayload
}
```

### `Transaction`
Normalised DB row. Written once at ingestion, read by classification worker.
```go
type Transaction struct {
    ID                         string
    GatewayTransactionID       string     // Razorpay pay_* ID — dedup key
    StatusCode                 string     // normalised, uppercase
    NPCIResponseCode           *string    // nullable
    BankResponseCode           *string    // nullable
    Amount                     float64
    CustomerBank               *string    // nullable — canonical bank name
    RetryCountSoFar            int        // clamped 0–10
    MandateNotificationSentAt  *time.Time // nullable — preserve null, never fabricate
    DebitScheduledAt           *time.Time // nullable
    CreatedAt                  time.Time
}
```

### `ClassificationJob`
Redis queue envelope. Minimal — only the UUID needed to fetch the full row.
```go
type ClassificationJob struct {
    TransactionID string `json:"transaction_id"`
}
```

---

## Classification Service Models

### `ClassificationResult`
Output of Layer 1 or Layer 2. Written to the `classifications` table.
```go
type ClassificationResult struct {
    TransactionID     string
    Layer             int      // 1 or 2
    Cause             string   // see Cause Constants
    Confidence        float64  // 0.0–1.0; Layer 1 is always 1.0
    Reasoning         string   // 1–2 human-readable sentences
    RecommendedAction string   // see Action Constants
    ModelVersion      *string  // nil for Layer 1
}
```

### Cause Constants
```go
const (
    CauseNotificationComplianceBlock = "notification_compliance_block"
    CauseSoftDecline                 = "soft_decline"
    CauseHardDecline                 = "hard_decline"
    CauseGatewayFault                = "gateway_fault"
    CauseFraudFilterBlock            = "fraud_filter_block"
)
```

### Action Constants
```go
const (
    ActionSilentReschedule = "silent_reschedule"  // Layer 1 only
    ActionRetryNow         = "retry_now"
    ActionRetryScheduled   = "retry_scheduled"
    ActionDoNotRetry       = "do_not_retry"
    ActionReverifyReverse  = "reverify_and_reverse"
)
```

---

## Audit Service Models

### `ClassificationView`
Joined read model — combines `classifications` + `transactions` into one object for the frontend.
```go
type ClassificationView struct {
    // Classification fields
    ID                string
    TransactionID     string
    Layer             int
    Cause             string
    Confidence        float64
    Reasoning         string
    RecommendedAction string
    ModelVersion      *string
    CreatedAt         time.Time

    // Transaction fields (joined)
    GatewayTransactionID string
    StatusCode           string
    NPCIResponseCode     *string
    BankResponseCode     *string
    Amount               float64
    CustomerBank         *string
    RetryCountSoFar      int
}
```

### `ListFilter`
Parsed from query params for the list endpoint.
```go
type ListFilter struct {
    Cause  string  // "" = all causes
    Layer  *int    // nil = all layers; 1 or 2 to filter
    Limit  int     // default 50, max 100
    Offset int     // default 0
}
```

---

## Confidence Scale

| Value | Meaning |
|-------|---------|
| `1.000` | Deterministic (Layer 1 — RBI rule match) |
| `0.750` | Stub classifier estimate (replace with real LLM value) |
| `0.000` | Fallback — Layer 2 errored; manual review required |

---

## Cause ↔ Action Mapping (Default)

| Cause | Default Action | Can Retry? |
|-------|---------------|-----------|
| `notification_compliance_block` | `silent_reschedule` | Yes — after notification |
| `soft_decline` | `retry_scheduled` | Yes |
| `hard_decline` | `do_not_retry` | No |
| `gateway_fault` | `retry_scheduled` | Yes |
| `fraud_filter_block` | `do_not_retry` | No |
