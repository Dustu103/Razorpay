# ADR-002: Use Groq as Primary LLM Provider

**Status:** Accepted  
**Date:** 2026-08-10  
**Deciders:** Engineering Team  

---

## Context

Layer 3 requires a general-purpose LLM capable of reasoning over payment failure context (status codes, bank names, error descriptions) and returning a structured root-cause classification with justification text. Provider selection is critical because LLM latency directly blocks queue processing.

Candidates evaluated:
1. OpenAI GPT-4o
2. Groq (LLaMA 3 / OpenGPT)
3. Google Gemini 1.5 Flash
4. Anthropic Claude Haiku
5. Self-hosted Ollama (local LLaMA 3)

---

## Decision

**Use Groq as the primary LLM provider, with Google Gemini as concurrent fallback.**

---

## Rationale

| Criterion | OpenAI GPT-4o | Groq | Gemini Flash | Anthropic | Ollama (local) |
|-----------|:-------------:|:----:|:------------:|:---------:|:--------------:|
| Inference speed (p50) | ~2s | **~400ms** | ~800ms | ~1.2s | ~5s (CPU) |
| Free-tier RPM | 3 | 30 | 15 | 5 | Unlimited |
| Cost (per 1M tokens) | $5 | $0.27 | $0.07 | $0.80 | $0 |
| OpenAI-compatible API | ✅ | ✅ | ❌ | ❌ | ✅ |
| JSON-structured output | ✅ | ✅ | ✅ | ✅ | Unreliable |

**Key factors:**
- **Groq's LPU architecture** delivers ~400ms median inference — 5x faster than GPT-4o — which is critical to prevent blocking the Go worker goroutines.
- Groq's API is **OpenAI-compatible**, meaning we can switch to any OpenAI-spec model (including GPT-4o) by changing a single environment variable.
- Ollama was rejected because local CPU inference (~5s) would saturate the semaphore worker slots and stall the queue.

---

## Consequences

- **Positive:** ~400ms p50 LLM latency keeps the classification pipeline well within the 3-second circuit-breaker timeout.
- **Positive:** OpenAI-compatible API enables zero-code provider swapping in future.
- **Negative:** Groq's free tier has a strict daily token cap (TPD), causing `429` errors under burst load. Mitigated by the Multi-LLM concurrent fallback to Gemini (see ADR-005).
- **Negative:** Groq's model roster changes frequently. The `groqModel` constant in `llm.go` must be validated on each deployment.

---

## Superseded Concern

Originally we planned Groq as the sole LLM. After stress testing revealed systematic `429` failures under burst load, ADR-005 was created to add Gemini as a concurrent peer, not just a sequential fallback.
