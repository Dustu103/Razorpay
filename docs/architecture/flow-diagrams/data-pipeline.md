# Data Pipeline — End-to-End Flow

**Scope:** Full journey from Razorpay webhook to Frontend Inspector

---

## Pipeline Diagram

```mermaid
flowchart TD
    A([Razorpay payment.failed]) --> B[Ingestion Service\n:3001]
    B --> C{Payload valid?}
    C -- No --> D([400 Bad Request])
    C -- Yes --> E[Clean Fields\nSection 5 - TDD]
    E --> F[(PostgreSQL\nAtomic Upsert)]
    F --> G{New row?}
    G -- No / Duplicate --> H([200 Duplicate - drop])
    G -- Yes --> I[Redis Queue\nclassification_jobs]
    I --> J[Classification Worker\nBLPOP]
    J --> K[(PostgreSQL\nFetch Transaction)]
    K --> L{Layer 1\nRBI Rule}
    L -- compliance block --> M[(PostgreSQL\nWrite classification\nlayer=1)]
    L -- fall through --> N{Layer 2\nStub / LLM}
    N -- success --> O[(PostgreSQL\nWrite classification\nlayer=2)]
    N -- error/timeout --> P[Fallback\nsoft_decline\nconfidence=0]
    P --> O
    M --> Q([Done])
    O --> Q

    R([Frontend Inspector]) --> S[Audit Service\n:3003]
    S --> T[(PostgreSQL\nJOIN query)]
    T --> S
    S --> R
```

---

## Feature Enrichment (Before Layer 2)

The classification worker enriches the raw transaction before it reaches Layer 2:

| Derived Field | How Computed |
|---------------|-------------|
| `time_since_last_failure` | `SELECT MAX(created_at) FROM transactions WHERE gateway_transaction_id != $current AND customer_bank = $bank` |
| `retry_count_so_far` | Read directly from `transactions.retry_count_so_far` (set at ingestion) |
| `bank_response_code` (normalised) | Normalised by ingestion cleaning; Layer 2 sees canonical form |

> **Note:** `time_since_last_failure` enrichment is planned for the real LLM integration. The current stub uses only the fields present in the transaction row.

---

## Deduplication Strategy

```
Razorpay at-least-once delivery
         │
         ▼
INSERT ... ON CONFLICT (gateway_transaction_id) DO NOTHING
         │
    ┌────┴────┐
    │         │
  New row   No row returned
    │         │
  Enqueue   DROP (already processed)
```

**Why atomic?** Two copies of the same webhook can arrive concurrently. A read-then-write check (SELECT then INSERT) would let both pass the SELECT before either writes, creating double classifications.

---

## PII / Compliance Boundary

```
What goes to Layer 2 (LLM):
  ✅ status_code
  ✅ npci_response_code
  ✅ bank_response_code
  ✅ amount
  ✅ customer_bank
  ✅ retry_count_so_far
  ✅ time_since_last_failure

What NEVER goes to Layer 2:
  ❌ Customer name
  ❌ Account number
  ❌ Card PAN
  ❌ Any direct customer identifier
```
