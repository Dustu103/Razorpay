# RB-005: Debug Compliance Scanner Violations

**Trigger:** Compliance scan returns unexpected results — false positives (violations on a clean flow) or false negatives (no violations on an obviously dark-pattern flow).  
**Severity:** Medium.

---

## Pipeline Architecture (v2 — Multi-LLM Ensemble)

```
Input JSON
    │
    ▼
Layer 1: Deterministic Engine (regex + state inspection) — zero LLM cost
    │
    ▼
Layer 2: Multi-LLM Ensemble — Groq + Gemini run CONCURRENTLY via ThreadPoolExecutor
    │          ├── llama3-70b-8192
    │          └── gemini-1.5-flash
    ▼
Aggregation: Union merge + deduplication by (screen_name, rule_broken)
    │          ├── detected_by: layer1_deterministic
    │          ├── detected_by: layer2_llm_groq
    │          ├── detected_by: layer2_llm_gemini
    │          └── detected_by: layer2_llm_ensemble_consensus (both agreed)
    ▼
ComplianceResponse
```

---

## Symptoms

- Scan returns `is_compliant: true` on a flow with a pre-checked checkbox or hidden cancel button.
- `layer1_violations` is 0 even though the JSON has `state: pre-checked` → Layer 1 regex bug.
- `layer2_violations` is 0 even with ambiguous elements → both LLMs failed or timed out.
- Scan returns `502 Bad Gateway`.
- `layer2_llm_ensemble_consensus` never appears → one LLM is silently failing.

---

## Steps

### 1. Check service health and pipeline version
```bash
curl http://localhost:3004/health
# Expected: {"status": "ok", "service": "compliance-scanner", "version": "2.0-pipeline"}
```

### 2. Run E2E test suite to isolate which layer is failing
```bash
docker run --rm --network razorpay_default \
  -v "$(pwd)/datasets/scripts:/scripts" \
  python:3.11-slim \
  sh -c "pip install requests -q && python /scripts/test_compliance.py"
```
All 13 assertions should pass. If any fail, compare the scenario to the pipeline layer above.

### 3. Diagnose Layer 1 failures (false negatives from deterministic engine)
Layer 1 failures mean the regex or state check missed an explicit violation.

```bash
docker compose logs --tail=50 compliance-service | grep "\[Layer1\]"
```

Check `main.py`'s `layer1_deterministic()` function:
- **Pre-checked box missed?** Verify `el.state == "pre-checked"` (exact string match, lowercase).
- **Urgency text not caught?** Check `FALSE_URGENCY_PATTERNS` regex covers the exact phrase used.
- **Missing cancellation path not flagged?** Verify the element text contains "subscri" or "mandate".

### 4. Diagnose Layer 2 failures (LLM ensemble not returning results)
```bash
docker compose logs --tail=100 compliance-service | grep -E "\[Layer2\]"
```

Log patterns and what they mean:

| Log message | Cause | Fix |
|------------|-------|-----|
| `[Layer2] Groq failed: 400` | Model name decommissioned | Update model in `_call_groq()` |
| `[Layer2] Groq failed: 401` | Invalid API key | Rotate key → [RB-004](../../operations/runbooks/RB-004-rotate-llm-api-keys.md) |
| `[Layer2] Gemini failed: 404` | Model not found | Update model in `_call_gemini()` |
| `[Layer2] Groq failed: timed out` | Groq overloaded | Increase timeout in `_call_groq()` |
| Both Groq and Gemini failed | Both keys invalid | Check `.env` for `GROQ_API_KEY` and `GEMINI_API_KEY` |

### 5. Check if the ensemble is running concurrently
If you see Groq logs then Gemini logs appearing sequentially with a full gap between them, the `ThreadPoolExecutor` may have fallen back to sequential execution. Verify:
```bash
docker compose logs --timestamps compliance-service | grep "\[Layer2\]"
```
Groq and Gemini timestamps should be within 1–2 seconds of each other.

### 6. Inspect raw LLM output for hallucination
Add `print(content)` before each `json.loads()` in `_call_groq()` and `_call_gemini()`, rebuild, and check logs:
```bash
docker compose up -d --build compliance-service
docker compose logs -f compliance-service
```
Look for:
- Markdown code fences (` ```json `) — strip logic handles this but verify.
- LLM inventing rule names outside the 3 defined semantic categories — tighten `LLM_SYSTEM_PROMPT`.

### 7. Fix false negatives — improve payload quality
Layer 2 requires semantic signals. Ambiguous element IDs degrade accuracy significantly:
```json
// ❌ BAD — no semantic signal for the LLM
{"id": "btn1", "type": "button", "text": "OK"}

// ✅ GOOD — descriptive id + explicit state
{"id": "btn_cancel_subscription", "type": "button", "state": "hidden", "text": "Cancel My Subscription"}
```

---

## Prevention

- All UX element IDs must be descriptive (never `btn1`, `chk2`, etc.).
- Always pass the `state` field for checkboxes and action buttons.
- Run `test_compliance.py` in CI on every `compliance-service` deployment.
- Monitor `layer1_violations` vs `layer2_violations` counts — a sudden drop to zero in Layer 2 is an LLM health signal.
