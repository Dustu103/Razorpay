# High-Level Design (HLD)
# Feature 1 — Root-Cause Classifier

**Version:** 1.0  
**Last Updated:** 2026-08-22  
**Author:** Engineering Team  
**Status:** Approved for Implementation

---

## 1. Problem Statement

Razorpay processes millions of recurring mandate payments daily. When a payment fails, the current system cannot programmatically determine *why* it failed — teams rely on manual inspection of bank response codes that are inconsistent across issuers. This causes delayed recovery actions and poor customer experience.

**Feature 1** builds a two-layer automated classifier that:
1. Detects RBI notification-compliance violations deterministically (Layer 1)
2. Classifies all other failures into one of four causes using an LLM (Layer 2 — stubbed for now)

---

## 2. System Architecture

```mermaid
graph TD
    RZ[Razorpay Webhooks] -->|POST /api/v1/webhook| IS[Ingestion Service<br/>:3001]
    IS -->|Atomic upsert| PG[(PostgreSQL)]
    IS -->|RPUSH| RQ[Redis Queue<br/>classification_jobs]
    RQ -->|BLPOP| CS[Classification Service<br/>worker]
    CS -->|SELECT transaction| PG
    CS -->|Layer 1 rule| L1{RBI compliance<br/>check}
    L1 -->|compliance block| PG
    L1 -->|fall through| L2[Layer 2<br/>stub / LLM]
    L2 --> PG
    FE[Frontend Inspector<br/>:3000] -->|GET /api/v1/classifications| AS[Audit Service<br/>:3003]
    AS -->|SELECT JOIN| PG
```

---

## 3. Services

| Service | Port | Role | Scales |
|---------|------|------|--------|
| **Ingestion Service** | 3001 | Webhook receiver; payload validation, dedup, enqueue | Horizontally (stateless) |
| **Classification Service** | — | Queue worker; Layer 1 + Layer 2; persists results | Horizontally (multiple workers) |
| **Audit Service** | 3003 | Read-only API for the Frontend Inspector | Horizontally (stateless) |
| **Frontend** | 3000 | Next.js Classifier Inspector UI | Horizontally |

---

## 4. Data Flow (End-to-End)

```
Razorpay
  │  payment.failed webhook (POST)
  ▼
Ingestion Service
  ├─ Validate payload structure
  ├─ Clean fields (uppercase, normalise codes, clamp retries)
  ├─ Atomic upsert → PostgreSQL (ON CONFLICT DO NOTHING)
  │   └─ Duplicate? → return 200 "duplicate", stop.
  └─ Enqueue ClassificationJob (transaction_id) → Redis
  
Classification Worker
  ├─ BLPOP from Redis queue
  ├─ Fetch full transaction from PostgreSQL
  ├─ Layer 1: RBI 24h notification rule
  │   └─ Match? → write classification (layer=1, confidence=1.0), done.
  └─ Layer 2: stub heuristic (replace with LLM later)
      └─ Write classification (layer=2, confidence=0.75)

Audit Service
  └─ Frontend reads GET /api/v1/classifications?cause=&layer=
      └─ Joined view: classifications ⋈ transactions → JSON
```

---

## 5. Classification Taxonomy

| Cause | Layer | Trigger |
|-------|-------|---------|
| `notification_compliance_block` | 1 | RBI: notification missing or < 24h before debit |
| `soft_decline` | 2 | Transient issuer issue — retriable |
| `hard_decline` | 2 | Permanent issuer rejection — do not retry |
| `gateway_fault` | 2 | Timeout / technical failure at gateway |
| `fraud_filter_block` | 2 | Bank risk/fraud filter triggered |

---

## 6. Recommended Actions

| Action | Meaning |
|--------|---------|
| `silent_reschedule` | Reschedule debit without alerting customer |
| `retry_now` | Retry immediately |
| `retry_scheduled` | Retry after a delay |
| `do_not_retry` | Permanent failure — notify customer |
| `reverify_and_reverse` | Reverify mandate and reverse if needed |

---

## 7. Infrastructure

```mermaid
graph LR
    subgraph Docker Compose
        IS[ingestion-service]
        CS[classification-service]
        AS[audit-service]
        FE[frontend]
        PG[(postgres:15)]
        RD[(redis:7)]
    end
    IS --> PG
    IS --> RD
    CS --> PG
    CS --> RD
    AS --> PG
    FE --> AS
```

---

## 8. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Queue decouples ingestion from classification | Webhook must return fast; LLM calls can be slow/retried |
| Atomic DB upsert for dedup | Razorpay guarantees at-least-once delivery; concurrent duplicates would pass a non-atomic check |
| Layer 1 is a pure function | Zero dependencies, zero latency, deterministic — runs before any I/O |
| `recommended_action` stored at classification time | Audit trail must reflect the decision made *then*, not derived from current routing logic |
| Layer 2 is stubbed | Full pipeline is functional/testable without an LLM key; drop-in replacement later |

---

## 9. Open Issues (Pre-Build)

| # | Issue | Owner |
|---|-------|-------|
| 1 | Dedup must be atomic upsert, not read-then-write | Backend |
| 2 | `mandate_notification_sent_at` field coverage per bank needs auditing | Data/Backend |
| 3 | `least_aggressive_action` needs per-cause lookup table | Backend |
| 4 | LLM call needs timeout + retry + failure path | AI/Backend |
| 5 | Data residency / third-party API sign-off for RBI-governed fields | Legal/Infra |
| 6 | Synthetic validation set is directional only | AI |
