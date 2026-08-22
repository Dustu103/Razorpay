# Ingestion Service — API Documentation
# Feature 1 — Root-Cause Classifier

**Base URL:** `http://localhost:3001`

---

## `POST /api/v1/webhook`

Receives a Razorpay `payment.failed` webhook, deduplicates, persists, and enqueues for classification.

**Request Body:**
```json
{
  "event": "payment.failed",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_xyz123",
        "status_code": "FAILED",
        "npci_txn_id": "NPCI001",
        "acquirer_data": "05",
        "amount": 99900,
        "bank": "HDFC",
        "retry_count": 1,
        "mandate_notification_sent_at": "2026-08-20T10:00:00Z",
        "debit_scheduled_at": "2026-08-21T09:00:00Z"
      }
    }
  }
}
```

**Responses:**

| Status | Body | When |
|--------|------|------|
| `202 Accepted` | `{"status":"accepted","transaction_id":"<uuid>"}` | New event ingested & queued |
| `200 OK` | `{"status":"duplicate","message":"already ingested"}` | Duplicate webhook |
| `400 Bad Request` | `{"error":"invalid JSON body","code":"INVALID_BODY"}` | Malformed payload |
| `500 Internal Server Error` | `{"error":"...","code":"DB_ERROR"\|"QUEUE_ERROR"}` | Infrastructure failure |

---

## `GET /health`

```json
{"status":"online","service":"ingestion-service"}
```
