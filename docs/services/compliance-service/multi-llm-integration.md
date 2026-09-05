# Compliance Scanner — Multi-LLM Integration

**Service:** `compliance-service`  
**Version:** 2.0 (Pipeline)

---

## 1. Overview

Layer 2 of the compliance pipeline runs **two LLMs concurrently** to detect semantically ambiguous dark patterns that cannot be caught by the deterministic Layer 1 engine. Running them in parallel provides:

- **Higher recall** — patterns one model misses, the other may catch (Union strategy)
- **Confidence scoring** — violations found by both models are marked as `consensus`, signalling highest-confidence findings
- **No latency penalty** — because both calls are concurrent, total Layer 2 latency equals `max(groq_latency, gemini_latency)`, not their sum

---

## 2. Models

| Model | Provider | Role | Context Window |
|-------|----------|------|---------------|
| `llama3-70b-8192` | Groq | Primary LLM — fast inference on Groq's LPU hardware | 131,072 tokens |
| `gemini-1.5-flash` | Google Gemini | Secondary LLM — different training data for independent perspective | Large |

Both models receive the **same system prompt** and the **same serialized JSON flow** as user content.

---

## 3. Execution — Concurrent via `ThreadPoolExecutor`

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    future_groq   = executor.submit(_call_groq, flow_json)
    future_gemini = executor.submit(_call_gemini, flow_json)

    raw_groq   = future_groq.result()
    raw_gemini = future_gemini.result()
```

Both `_call_groq()` and `_call_gemini()` are independently fault-tolerant — if either raises an exception, it logs the error and returns an empty list, so the other model's results are still used.

**Timeout values:**
- Groq: 10s (LPU inference is fast)
- Gemini: 15s (REST API can be slower)

---

## 4. Merge Strategy — Union with Consensus Tracking

```
Groq violations   Gemini violations
      │                  │
      └────────┬─────────┘
               ▼
    Union by (screen_name, rule_broken)
               │
    ┌──────────┴──────────────────────┐
    │                                  │
  Both found it?              Only one found it?
    │                                  │
    ▼                                  ▼
detected_by:                  detected_by:
layer2_llm_ensemble_consensus layer2_llm_groq | layer2_llm_gemini
```

**Why Union, not Intersection?**  
In compliance, a false negative (missing a real dark pattern) is worse than a false positive (flagging something safe). Union maximises recall. See [ADR-008](./decisions/ADR-008-multi-llm-union-strategy.md) for full rationale.

---

## 5. System Prompt Design

Layer 2 is deliberately scoped to **only** catch violations that Layer 1 cannot:

```
You must check ONLY for:
  1. Forced Product Bundling
  2. Obscured Terms & Conditions
  3. Interface Pressure (subtle layout/wording nudges)

Do NOT re-report violations already caught by:
  - Pre-checked checkboxes
  - Explicit urgency countdown text
  - Hidden cancel buttons
```

This reduces LLM hallucination and prevents double-reporting what Layer 1 already caught deterministically.

---

## 6. Failure Modes & Fallback Behaviour

| Scenario | Behaviour |
|----------|-----------|
| Groq fails (timeout/API error) | Logs `[Layer2] Groq failed`. Returns empty list. Gemini results still used. |
| Gemini fails (timeout/API error) | Logs `[Layer2] Gemini failed`. Returns empty list. Groq results still used. |
| Both fail | Layer 2 returns empty list. Layer 1 results still returned. Service never returns 502. |
| Both succeed, same violation | Marked `layer2_llm_ensemble_consensus` — highest confidence. |
| `GROQ_API_KEY` not set | `_call_groq()` short-circuits immediately, returns empty. |
| `GEMINI_API_KEY` not set | `_call_gemini()` short-circuits immediately, returns empty. |
| Empty flow `[]` passed | `layer2_llm()` short-circuits before spawning threads. |
