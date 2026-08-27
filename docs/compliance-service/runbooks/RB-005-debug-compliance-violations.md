# RB-005: Debug Compliance Scanner Violations

**Trigger:** Compliance scan returns unexpected results — false positives (violations on a clean flow) or false negatives (no violations on an obviously dark-pattern flow).  
**Severity:** Medium.

---

## Symptoms

- Scan returns `is_compliant: true` on a flow that visibly has a pre-checked checkbox or hidden cancel button.
- Scan returns violations with generic `rule_broken` text not matching the 5 RBI rules.
- Scan returns `502 Bad Gateway`.

---

## Steps

### 1. Check the service is healthy
```bash
curl http://localhost:3004/health
# Expected: {"status": "ok", "service": "compliance-scanner"}
```

### 2. Run the E2E test suite to isolate the failing scenario
```bash
docker run --rm --network razorpay_default \
  -v "$(pwd)/datasets/scripts:/scripts" \
  python:3.11-slim \
  sh -c "pip install requests -q && python /scripts/test_compliance.py"
```

### 3. Check which LLM provider responded
```bash
docker compose logs --tail=50 compliance-service | grep -E "(Groq|Gemini|Error)"
```
- `Groq API Error... Falling back to Gemini...` → Groq rate-limited. Gemini took over.
- `Both Groq and Gemini failed` → Rotate API keys. See [RB-004](../../operations/runbooks/RB-004-rotate-llm-api-keys.md).

### 4. Inspect raw LLM output for hallucination
Temporarily add `print(content)` before `json.loads()` in `main.py`, rebuild and test:
```bash
docker compose up -d --build compliance-service
docker compose logs -f compliance-service
```
Look for:
- Markdown code fences in output (e.g. ` ```json `) — the strip logic should catch this, but verify.
- LLM inventing rule names not in the 5 RBI rules — tighten the system prompt.

### 5. Fix false negatives — improve payload quality
The LLM needs semantic signals. Ambiguous element IDs degrade accuracy:
```json
// ❌ BAD — no semantic signal
{"id": "btn1", "type": "button", "text": "OK"}

// ✅ GOOD — descriptive id + explicit state
{"id": "btn_cancel_subscription", "type": "button", "state": "hidden", "text": "Cancel My Subscription"}
```

---

## Prevention

- All UX element IDs must be descriptive (not `btn1`, `chk2`).
- Always include the `state` field for checkboxes and action buttons.
- Run `test_compliance.py` in CI on every compliance-service deployment.
