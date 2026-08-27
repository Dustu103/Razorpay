# Mandate Compliance Scanner Architecture

## 1. The Design Philosophy

The original business case called for an autonomous agent capable of "reading" a business's entire mandate flow to find UX compliance violations (dark patterns) based on the Feb 2026 RBI Guidelines.

**Architectural Pivot:** Building an autonomous web crawler that bypasses captchas, navigates React SPAs, and manages authentication state is highly brittle and out-of-scope for a reliable payment infrastructure tool. 

Instead, the `compliance-service` is scoped to operate on a **Declarative UI JSON Schema**.
Merchants (or internal audit teams) provide a JSON representation of the screens, buttons, and checkbox states. The LLM engine evaluates this abstract syntax tree against the regulatory rulebook.

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
  "violations": [
    {
      "screen_name": "checkout_step_1",
      "rule_broken": "False Urgency",
      "severity": "High",
      "fix_suggestion": "Remove the 5-minute countdown language."
    },
    {
      "screen_name": "checkout_step_1",
      "rule_broken": "Pre-checked consent",
      "severity": "High",
      "fix_suggestion": "Consent checkboxes must default to unchecked."
    }
  ]
}
```

## 3. Technology Stack

- **Framework:** Python + FastAPI (chosen for strict Pydantic parsing of LLM outputs).
- **LLM Provider:** Groq (llama-3.1-8b-instant). Chosen for ultra-low latency.
- **Integration:** Runs on port `3004`. The frontend calls this directly via standard HTTP requests from the `ComplianceScanner.tsx` component.
