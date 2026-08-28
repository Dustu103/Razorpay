# ADR-003: Use Redis Queue for Async Classification

**Status:** Accepted  
**Date:** 2026-08-05  
**Deciders:** Engineering Team  

---

## Context

When a `payment.failed` webhook arrives at the Ingestion Service, classification must happen asynchronously. The Ingestion Service cannot block the HTTP response waiting for LLM inference (~400ms–3s). We need a durable, low-latency decoupling layer between ingestion and classification.

Candidates evaluated:
1. Synchronous HTTP (Ingestion calls Classification directly)
2. Redis List (BLPOP/LPUSH)
3. Kafka / Redpanda
4. RabbitMQ
5. PostgreSQL as a job queue (polling)

---

## Decision

**Use Redis List with BLPOP/LPUSH as the async job queue.**

---

## Rationale

| Criterion | Sync HTTP | Redis List | Kafka | RabbitMQ | PG Queue |
|-----------|:---------:|:----------:|:-----:|:--------:|:--------:|
| Ingestion latency impact | Blocks (~3s) | **None** | None | None | None |
| Setup complexity | None | **Trivial** | High | Medium | Trivial |
| Durability | None | In-memory* | Full | Full | Full |
| Throughput (ops/sec) | N/A | **>100k** | >1M | ~50k | ~5k |
| Already in stack | — | **Yes (cache)** | No | No | Yes |
| Ops burden | None | **Low** | Very High | Medium | Low |

**Key factors:**
- Redis was **already required** for distributed deduplication of webhooks in the Ingestion Service. Using it as a queue adds zero new infrastructure.
- Kafka is operationally heavyweight (Zookeeper, partition management, consumer groups) — significant over-engineering for the current throughput requirements.
- Synchronous HTTP was ruled out immediately: a 3-second LLM call blocks the Ingestion HTTP handler, making the webhook endpoint flaky under burst load.

---

## Consequences

- **Positive:** Zero additional infrastructure. Redis serves dual purpose: dedup store + job queue.
- **Positive:** BLPOP gives the Go worker a blocking long-poll with a configurable timeout — no busy-wait polling.
- **Negative:** Redis is an in-memory store. A process crash without persistence (`AOF`/`RDB`) will lose queued jobs. Acceptable for MVP; requires `appendonly yes` in Redis config for production.
- **Negative:** No native dead-letter queue. Failed jobs are currently dropped. A future `DLQ` pattern must be implemented before production launch.

---

## Revisit Trigger

If throughput exceeds 10,000 classification jobs/minute sustained, or if dead-letter queue requirements become critical, evaluate migration to Redpanda (Kafka-compatible, simpler ops).
