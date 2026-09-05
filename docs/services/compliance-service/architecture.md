# Mandate Compliance Scanner Architecture

## 1. The Design Philosophy

The original business case called for an autonomous agent capable of "reading" a business's entire mandate flow to find UX compliance violations (dark patterns) based on the Feb 2026 RBI Guidelines.

**Architectural Pivot:** Building an autonomous web crawler that bypasses captchas, navigates React SPAs, and manages authentication state is highly brittle and out-of-scope for a reliable payment infrastructure tool. 

Instead, the `compliance-service` is scoped to operate on a **Declarative UI JSON Schema**.
Merchants (or internal audit teams) provide a JSON representation of the screens, buttons, and checkbox states.

The service processes this JSON via a **2-Layer Pipeline**:
1. **Layer 1 (Deterministic Engine):** Fast regex and state checks (e.g. `state: pre-checked` or "Hurry!"). Zero LLM cost, perfectly accurate for explicit violations.
2. **Layer 2 (LLM Semantic Engine):** For ambiguous violations (e.g. forced bundling, interface pressure). The LLM (`llama3-70b-8192`) analyzes the JSON AST.
3. **Aggregation:** Both layers are merged and deduplicated before returning.

## 2. API Design

### POST `/api/v1/scan-compliance`

**Request Payload:**
```json
{
  "flow": [
    {
      "screen_name": "checkout_step_1",
      "elements": [
        { "id": "btn_pay", "type": "button", "text": "Pay Now (Hurry, 5 mins left!)" },
        { "id": "chk_subscribe", "type": "checkbox", "state": "pre-checked", "text": "Subscribe to premium" }
      ]
    }
  ]
}
```

**Response Payload:**
```json
{
  "is_compliant": false,
  "layer1_violations": 2,
  "layer2_violations": 0,
  "violations": [
    {
      "screen_name": "checkout_step_1",
      "element_id": "btn_pay",
      "rule_broken": "False Urgency",
      "severity": "Medium",
      "fix_suggestion": "Remove the 5-minute countdown language.",
      "detected_by": "layer1_deterministic"
    },
    {
      "screen_name": "checkout_step_1",
      "element_id": "chk_subscribe",
      "rule_broken": "Pre-checked Consent",
      "severity": "High",
      "fix_suggestion": "Consent checkboxes must default to unchecked.",
      "detected_by": "layer1_deterministic"
    }
  ]
}
```

## 3. Technology Stack

- **Framework:** Python + FastAPI (chosen for strict Pydantic parsing of LLM outputs).
- **LLM Provider:** Groq (llama-3.1-8b-instant). Chosen for ultra-low latency.
- **Integration:** Runs on port `3004`. The frontend calls this directly via standard HTTP requests from the `ComplianceScanner.tsx` component.
