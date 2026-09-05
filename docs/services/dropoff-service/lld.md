# Drop-Off Recovery Service - Low Level Design (LLD)

## Service Architecture & Packages

```
backend/dropoff-service/
├── cmd/
│   └── server/
│       └── main.go          # Entrypoint, Fiber HTTP routes, graceful shutdown
├── internal/
│   ├── worker/
│   │   └── detector.go      # ZSET poller, event analyzer, inference client
│   ├── guardrails/
│   │   └── execution.go     # Frequency capping, opt-outs, TRAI quiet hours
│   └── models/
│       └── session.go       # Structs for checkout telemetry and ML request/response
├── Dockerfile
├── go.mod
└── go.sum
```

## Redis Data Model

### 1. Active Sessions Tracker
* **Key:** `active_checkout_sessions`
* **Type:** Sorted Set (`ZSET`)
* **Score:** UTC Unix timestamp when session expiration check should trigger (`now + expiry_sec`).
* **Member:** `session_id` (string)

### 2. Session Metadata Hash
* **Key:** `session:{session_id}`
* **Type:** Hash (`HSET`)
* **Fields:**
  * `cart_value`: float (e.g. `3500.00`)
  * `payment_method`: string (`upi`, `card`, `netbanking`, `cod`)
  * `device`: string (`mobile_android`, `mobile_ios`, `desktop`)
  * `payment_status`: string (`pending`, `success`, `failed`)
  * `customer_id`: string (phone or unique ID)
  * `merchant_id`: string
  * `merchant_margin`: float (e.g. `0.30`)
  * `created_at`: Unix timestamp

### 3. Session Event Stream
* **Key:** `session:{session_id}:events`
* **Type:** List (`RPUSH`)
* **Elements:** Ordered telemetry event strings:
  * `cart_loaded`
  * `payment_selected`
  * `upi_app_switch_init`
  * `upi_app_switch_return`
  * `otp_requested`
  * `otp_entered`
  * `vpa_validation_failed`
  * `price_breakdown_viewed`

## Rule-Based Diagnostic Classifier (`detector.go`)

When a session expires, `detector.go` scans the event sequence to extract the primary diagnosis before invoking the ML engine:

| Behavioral Pattern | Extracted Diagnosis | Description |
| :--- | :--- | :--- |
| `upi_app_switch_init` with no return | `upi_app_switch_abort` | Customer redirected to UPI app (GPay/PhonePe) but never returned |
| `otp_requested` with no `otp_entered` | `otp_timeout` | Delayed SMS OTP from issuer bank causing drop-off |
| `vpa_validation_failed` | `vpa_validation_failure` | Typos in UPI ID / VPA handle |
| Rapid cart view + immediate price review | `price_shock_breakdown` | Unexpected convenience fees or shipping costs |
| Prolonged inactivity after cart load | `genuine_browse_abandon` | Intentional window shopping abandonment |

## Telemetry Feature Extraction for Inference Gateway

`detector.go` computes runtime statistics passed to `inference-service`:
* `duration_sec`: Time elapsed from `created_at` to expiration.
* `attempt_count`: Number of distinct payment initiation events.
* `events_count`: Total event count in Redis list.
* `sequence_entropy`: Information entropy of the event sequence string.
* `mean_inter_event_time`: `duration_sec / max(1, events_count)`.

## API Endpoints

### `GET /api/v1/dropoff-metrics`
Returns real-time dashboard telemetry:
```json
{
  "active_sessions": 42,
  "interventions_sent": 156,
  "revenue_recovered": "117000.00",
  "recent_interventions": [
    {
      "session_id": "sess_98a71b2",
      "diagnosis": "price_shock_breakdown",
      "action": "whatsapp",
      "expected_profit": 34.50,
      "timestamp": "2 mins ago"
    }
  ]
}
```
