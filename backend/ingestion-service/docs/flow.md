# Ingestion Flow — Webhook to Queue

**Service:** Ingestion Service (`:3001`)  
**Trigger:** Razorpay `payment.failed` webhook

---

## Flow Diagram

```mermaid
sequenceDiagram
    participant RZ as Razorpay
    participant IS as Ingestion Service
    participant PG as PostgreSQL
    participant RQ as Redis Queue

    RZ->>IS: POST /api/v1/webhook<br/>{event: "payment.failed", payload: {...}}
    
    IS->>IS: 1. Parse & validate JSON body
    IS->>IS: 2. Clean fields<br/>(uppercase status_code, normalise codes,<br/>clamp retry_count 0–10,<br/>parse timestamps / preserve null)

    IS->>PG: 3. INSERT ... ON CONFLICT (gateway_transaction_id) DO NOTHING<br/>RETURNING id
    
    alt New transaction (row returned)
        PG-->>IS: transaction UUID
        IS->>RQ: 4. RPUSH classification_jobs<br/>{"transaction_id": "<uuid>"}
        IS-->>RZ: 202 Accepted<br/>{"status":"accepted","transaction_id":"<uuid>"}
    else Duplicate (no row returned)
        PG-->>IS: (empty)
        IS-->>RZ: 200 OK<br/>{"status":"duplicate","message":"already ingested"}
    end
```

---

## Field Cleaning Rules Applied

| Field | Rule |
|-------|------|
| `status_code` | Uppercase + trim; map synonyms (`TIMED_OUT`→`TIMEOUT`) |
| `bank_response_code` | Pass through as-is; normalisation done in classification |
| `retry_count_so_far` | Clamp to `[0, 10]`; log if out of range |
| `mandate_notification_sent_at` | Parse RFC3339; **null stays null** (never fabricated) |
| `debit_scheduled_at` | Parse RFC3339; **null stays null** |
| `amount` | Passed as float; reject on parse failure |

---

## Error Paths

| Scenario | Response |
|----------|---------|
| Malformed JSON | `400 INVALID_BODY` |
| DB upsert error | `500 DB_ERROR` |
| Redis enqueue error | `500 QUEUE_ERROR` (transaction already persisted) |
| Duplicate webhook | `200` (acknowledged, not re-processed) |
