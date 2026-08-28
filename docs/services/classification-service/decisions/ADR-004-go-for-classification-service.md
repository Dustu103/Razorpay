# ADR-004: Use Go for the Classification Service

**Status:** Accepted  
**Date:** 2026-08-05  
**Deciders:** Engineering Team  

---

## Context

The classification-service runs a hot loop: it continuously polls Redis, deserializes job payloads, fans out to ML and LLM APIs concurrently, merges results, and writes to PostgreSQL. The language choice directly determines concurrency model, memory overhead, and deployment size.

Candidates evaluated:
1. Python (FastAPI / asyncio)
2. Go (net/http)
3. Node.js (Express)
4. Rust (Axum)

---

## Decision

**Use Go for the classification-service.**

---

## Rationale

| Criterion | Python | Go | Node.js | Rust |
|-----------|:------:|:--:|:-------:|:----:|
| Native goroutine concurrency | ❌ (GIL) | ✅ | Partial | ✅ |
| Memory per idle goroutine | N/A | **~4KB** | ~1MB/thread | ~4KB |
| Docker image size | ~500MB | **~15MB** | ~200MB | ~10MB |
| Redis + Postgres client ecosystem | ✅ | ✅ | ✅ | Immature |
| Team familiarity | High | High | Medium | Low |
| Compile-time safety | ❌ | ✅ | ❌ | ✅ |

**Key factors:**
- The semaphore-based worker spawns up to **50 concurrent goroutines** simultaneously. Go's goroutines are ~4KB each (vs ~1MB for OS threads), making 50-way concurrency nearly zero-cost.
- Python's **GIL** would serialize concurrent LLM HTTP calls, eliminating the performance benefit of the multi-LLM architecture.
- Rust offers similar performance but has a steep learning curve and a less mature ecosystem for this use case (Redis, Postgres, HTTP clients).
- The `ml-service` (Python/FastAPI) correctly handles the ML inference where Python excels (scikit-learn, numpy). Go handles the orchestration layer where concurrency is paramount.

---

## Consequences

- **Positive:** 50 concurrent classification jobs run with <200MB total RAM.
- **Positive:** Single statically-linked binary. Docker image is ~15MB.
- **Positive:** The `context` package gives us clean, propagating timeout cancellation across all goroutines.
- **Negative:** Go's error handling is verbose compared to Python. More boilerplate for HTTP clients.
- **Negative:** No dynamic typing — adding new JSON fields from LLM responses requires struct updates.
