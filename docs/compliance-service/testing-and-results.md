# Compliance Scanner – Testing & Results

**Version:** 1.0  
**Status:** Validated

---

## 1. Test Harness Overview

The compliance-service is validated using a dedicated Python E2E test script located at `datasets/scripts/test_compliance.py`. The scanner is validated through **scenario-driven assertions** — each test case verifies a specific RBI rule, pipeline layer, or edge case.

To run the tests:
```bash
docker run --rm --network razorpay_default \
  -v "$(pwd)/datasets/scripts:/scripts" \
  python:3.11-slim \
  sh -c "pip install requests -q && python /scripts/test_compliance.py"
```

For local development (outside Docker):
```bash
COMPLIANCE_SERVICE_URL=http://localhost:3004 python datasets/scripts/test_compliance.py
```

---

## 2. Test Scenarios

| # | Scenario | Input | Expected Outcome |
|---|----------|-------|-----------------|
| 0 | Health Check | `GET /health` | `200 OK` |
| 1 | Fully Compliant Flow | Unchecked checkbox, visible cancel btn, visible terms link | `is_compliant: true`, 0 violations |
| 2 | Single Violation — Pre-checked Consent | `chk_subscribe` with `state: pre-checked` | `is_compliant: false`, ≥1 violation, "Pre-checked" rule named |
| 3 | Worst-Case — All 3 Dark Patterns | False urgency text, pre-checked checkbox, hidden cancel btn | `is_compliant: false`, ≥3 violations, ≥1 High severity |
| 4 | Input Validation — Empty Flow | `{ "flow": [] }` | `200` or `422` — no crash |

---

## 3. Live Test Results

```
=== Compliance Scanner – E2E Test Report ===

[0] Health Check
  ✓ PASS  Service is reachable and healthy

[1] Fully Compliant Flow
  ✓ PASS  is_compliant = True
  ✓ PASS  violations list is empty

[2] Single Violation – Pre-checked Consent
  ✓ PASS  is_compliant = False
  ✓ PASS  At least 1 violation detected
  ✓ PASS  'Pre-checked' rule identified
  ✓ PASS  Violation has a fix_suggestion
  ✓ PASS  Violation has a severity (High/Med/Low)

[3] Worst-Case Flow – Multiple Dark Patterns
  ✓ PASS  is_compliant = False
  ✓ PASS  3 or more violations found
  ✓ PASS  At least 1 High-severity violation
  ✓ PASS  All violations have fix_suggestion

[4] Input Validation – Empty Flow List
  ✓ PASS  API handles empty flow without crashing (2xx or 422)

──────────────────────────────────────────────────
Results: 13 passed, 0 failed
──────────────────────────────────────────────────
```

**Date:** 2026-08-27 (v2.0 — Multi-LLM Ensemble)  
**Environment:** Docker network `razorpay_default` | LLM: `groq/compound` + `gemini-3.6-flash` (concurrent)

---

## 4. Observed LLM Output Quality — Ensemble Behaviour

On the worst-case test, Layer 2 runs `groq/compound` and `gemini-3.6-flash` concurrently via `ThreadPoolExecutor`. Violations are merged and tagged:

| `detected_by` value | Meaning |
|---------------------|---------|
| `layer1_deterministic` | Caught by regex/state engine — no LLM cost |
| `layer2_llm_groq` | Only Groq identified this pattern |
| `layer2_llm_gemini` | Only Gemini identified this pattern |
| `layer2_llm_ensemble_consensus` | **Both** models independently flagged the same rule on the same screen |

Consensus violations are highest-confidence findings — two independent LLMs with different training data both agree.

---

## 5. Known Limitations & Revisit Triggers

| Limitation | Impact | Plan |
|------------|--------|------|
| Groq `groq/compound` model is used (not GPT-4 class) | May miss subtle implied dark patterns (e.g. UI contrast manipulation) | Upgrade to higher reasoning model for prod |
| Input is JSON schema, not live UI | Cannot detect visual dark patterns (e.g. grey-on-white "decline" buttons) | Future: add screenshot + Gemini Vision support |
| No deduplication of repeated violations | Same rule can appear twice if two elements both violate it | Deduplicate by `rule_broken` before returning response |
