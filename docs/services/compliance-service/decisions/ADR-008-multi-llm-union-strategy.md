# ADR-008: Use Union Strategy for Multi-LLM Compliance Ensemble

**Status:** Accepted  
**Date:** 2026-08-27  
**Service:** `compliance-service`

---

## Context

The compliance scanner's Layer 2 runs two LLMs concurrently — `groq/compound` and `gemini-3.6-flash`. When their outputs are merged, there are two possible strategies for handling disagreements:

**Intersection (AND):** Only flag a violation if *both* models found it.  
- Pros: Fewer false positives. Every result has two-model confidence.  
- Cons: If one model misses a real dark pattern, it gets dropped entirely.

**Union (OR):** Flag a violation if *either* model found it.  
- Pros: Maximum recall. No real violation gets silently dropped.  
- Cons: Risk of false positives if one model hallucinates.

---

## Decision

**Use the Union strategy.**

Violations found by only one model are included. Violations found by both models are promoted to `layer2_llm_ensemble_consensus`.

---

## Rationale

### 1. Asymmetric Cost of Errors in Compliance

In a payment mandate context, the cost of a **false negative** (missing a real RBI dark pattern that makes it to production) is:
- Regulatory fine from RBI
- Potential enforcement action
- Reputational damage to the merchant

The cost of a **false positive** (flagging something safe):
- One extra review item for the engineering team
- Minor friction, easily dismissed

This asymmetry strongly favours maximizing recall — which Union achieves.

### 2. Two Independent Training Data Sources

`groq/compound` and `gemini-3.6-flash` were trained on different data by different organizations. When one model detects a pattern the other misses, that is valuable signal — it reflects genuine model diversity, not noise. Discarding it via Intersection wastes this diversity.

### 3. Hallucination Mitigation

Layer 2 is explicitly instructed via its system prompt to **not re-report** violations already caught by Layer 1 (pre-checked boxes, explicit urgency text, hidden cancel buttons). This significantly constrains the output space and reduces hallucination risk, making the Union strategy safe to use.

If a model hallucinates a novel rule name not in the 5 RBI categories, the deduplication key `(screen_name, rule_broken.lower())` will still capture it — but it will be easily identifiable in the report as a single-model finding (not consensus) and can be reviewed.

### 4. Consensus as a Trust Signal

Rather than discarding single-model findings, we *label* them:
- `layer2_llm_groq` or `layer2_llm_gemini` — one model saw it
- `layer2_llm_ensemble_consensus` — both models independently agreed

This gives downstream teams a built-in confidence tier without losing any signal.

---

## Consequences

- **Positive:** Maximum dark pattern recall. No real violation silently dropped.
- **Positive:** Consensus label provides natural prioritisation — fix consensus violations first.
- **Negative:** Engineers must review single-model findings more carefully for potential hallucinations.
- **Mitigation:** The constrained system prompt and Layer 1 pre-filtering substantially reduce hallucination surface area.

---

## Revisit Trigger

If false positive rate exceeds ~15% in production review (i.e., more than 1 in 6 Layer 2 findings requires dismissal), switch to a **Weighted Intersection** — require consensus for novel rules, but keep Union for rules where one model has a proven track record.
