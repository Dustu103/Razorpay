# ADR-005: Concurrent Multi-LLM with Ensemble Tie-breaker

**Status:** Accepted  
**Date:** 2026-08-20  
**Deciders:** Engineering Team  

---

## Context

After stress testing (see `classification-service/testing-and-results.md`), it was discovered that Groq's free-tier token limit causes systematic `429` errors under burst load, dropping live accuracy to ~46% as the system fell back to a hardcoded heuristic. A single-provider LLM architecture has a single point of failure at the most critical layer of the pipeline.

Options to resolve:
1. Retry Groq with exponential backoff (sequential)
2. Add Gemini as a sequential fallback (try Groq, if 429 try Gemini)
3. Query Groq and Gemini **simultaneously** and take the first valid response
4. Upgrade to a paid API key (avoids the problem, doesn't solve the architecture)

---

## Decision

**Query Groq and Gemini concurrently using goroutines. Take the first valid, non-error response. If both fail, fall back to the deterministic heuristic.**

---

## Rationale

**Option 1 (Retry with backoff):** Adds unbounded latency. If Groq is rate-limited, a 3-retry exponential backoff blocks the goroutine slot for 7+ seconds, stalling the semaphore queue.

**Option 2 (Sequential fallback):** Still incurs Groq's full timeout before attempting Gemini. Under burst load, every job takes the full 3-second timeout before failing over, effectively halving throughput.

**Option 3 (Concurrent — Chosen):** Both providers are queried at `t=0`. The effective LLM latency is `min(t_groq, t_gemini)`. The rate-limit failure of one provider is completely hidden by the success of the other. No latency penalty.

**Option 4 (Paid key):** Correct long-term solution but doesn't improve the architecture's resilience. The concurrent design remains superior even with paid keys — it adds redundancy against network partitions and provider outages, not just rate limits.

---

## Implementation Details

```
goroutine A → POST groq/v1/chat/completions ─┐
                                              ├── first result wins → resultCh
goroutine B → POST generativelanguage.googleapis.com ─┘

Timeout: 3 seconds (context.WithTimeout)
Fallback: heuristicFallback() if resultCh is empty after timeout
```

---

## Consequences

- **Positive:** Effective LLM latency = fastest of the two providers. Under normal load: ~400ms.
- **Positive:** Single-provider rate-limit or network error is completely transparent to the pipeline.
- **Positive:** Adding a third LLM provider in the future requires adding one goroutine — no architectural change.
- **Negative:** API cost doubles (two simultaneous calls per job). Acceptable at current volume; revisit at scale.
- **Negative:** The "winning" provider is non-deterministic. Logging must capture which provider responded to enable debugging.
