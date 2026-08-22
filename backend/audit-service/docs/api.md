# Audit Service — API Documentation
# Feature 1 — Root-Cause Classifier

**Base URL:** `http://localhost:3003`

---

## `GET /api/v1/classifications`

Returns a paginated list of classifications joined with their transaction data.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `cause` | string | `""` | Filter by cause (e.g. `soft_decline`, `notification_compliance_block`) |
| `layer` | int | `0` | Filter by layer: `1` or `2`. `0` = all |
| `limit` | int | `50` | Max results (capped at 100) |
| `offset` | int | `0` | Pagination offset |

**Example:**
```
GET /api/v1/classifications?cause=soft_decline&layer=2&limit=20
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "clf_abc",
      "transaction_id": "txn_xyz",
      "gateway_transaction_id": "pay_xyz123",
      "layer": 2,
      "cause": "soft_decline",
      "confidence": 0.75,
      "reasoning": "The failure with status 'FAILED' appears to be a transient soft decline...",
      "recommended_action": "retry_scheduled",
      "model_version": "stub-v1.0-heuristic",
      "status_code": "FAILED",
      "npci_response_code": "NPCI001",
      "bank_response_code": "05",
      "amount": 99900,
      "customer_bank": "HDFC",
      "retry_count_so_far": 1,
      "created_at": "2026-08-21T10:00:00Z"
    }
  ],
  "count": 1
}
```

---

## `GET /api/v1/classifications/:id`

Returns a single classification by its UUID.

**Path Param:** `id` — UUID of the classification row

**Response `200 OK`:** Same shape as a single item in the list above.

**Response `404 Not Found`:**
```json
{"error":"classification <id> not found","code":"NOT_FOUND"}
```

---

## `GET /health`

```json
{"status":"online","service":"audit-service"}
```

---

## Allowed Cause Values

| Value | Description |
|-------|-------------|
| `notification_compliance_block` | RBI pre-debit notification missing or late |
| `soft_decline` | Transient issuer issue — retriable |
| `hard_decline` | Permanent issuer rejection |
| `gateway_fault` | Timeout / technical failure at gateway |
| `fraud_filter_block` | Bank risk/fraud filter triggered |

## Allowed Recommended Actions

| Value | Description |
|-------|-------------|
| `silent_reschedule` | Reschedule without alerting customer |
| `retry_now` | Retry immediately |
| `retry_scheduled` | Retry after delay |
| `do_not_retry` | Permanent failure — notify customer |
| `reverify_and_reverse` | Reverify mandate, reverse if needed |
