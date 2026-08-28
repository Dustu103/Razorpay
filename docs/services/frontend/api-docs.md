# Frontend — API Documentation
# Feature 1 — Classifier Inspector (BFF Routes)

**Base URL:** `http://localhost:3000`

These are the Next.js BFF (Backend-for-Frontend) routes. They proxy to the Audit Service internally.

---

## `GET /api/classifications`

Returns paginated list of classifications for the transaction list view.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `cause` | string | `""` | Filter: `soft_decline`, `hard_decline`, `gateway_fault`, `fraud_filter_block`, `notification_compliance_block` |
| `layer` | `1` or `2` | — | Filter by classification layer |
| `limit` | int | `50` | Page size |
| `offset` | int | `0` | Pagination |

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "abc123",
      "gateway_transaction_id": "pay_xyz",
      "layer": 1,
      "cause": "notification_compliance_block",
      "confidence": 1.0,
      "reasoning": "The pre-debit notification was not sent...",
      "recommended_action": "silent_reschedule",
      "model_version": null,
      "status_code": "FAILED",
      "amount": 99900,
      "customer_bank": "HDFC",
      "retry_count_so_far": 0,
      "created_at": "2026-08-22T10:00:00Z"
    }
  ],
  "count": 1
}
```

---

## `GET /api/classifications/[id]`

Returns a single classification for the detail view.

**Path Param:** `id` — classification UUID

**Response `200 OK`:** Same shape as single item above, plus all fields.

**Response `404`:**
```json
{ "error": "Not found" }
```

---

## Screen ↔ API Mapping

| Screen | API Called | Query Params Used |
|--------|-----------|-------------------|
| Transaction List (`/`) | `GET /api/classifications` | `cause`, `layer`, `limit`, `offset` |
| Transaction Detail (`/classifications/[id]`) | `GET /api/classifications/[id]` | none |
