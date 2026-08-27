"""
Mandate Compliance Scanner — backend/compliance-service/main.py

Two-layer pipeline:
  Layer 1 – Deterministic rule engine  (pattern matching, zero LLM cost)
  Layer 2 – LLM semantic analysis      (ambiguous / contextual violations)
  Aggregation – Merge + deduplicate findings from both layers
"""

import os
import re
import json
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Mandate Compliance Scanner API — v2 Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ── Data Models ───────────────────────────────────────────────────────────────

class ScreenElement(BaseModel):
    id: str
    type: str
    text: Optional[str] = None
    state: Optional[str] = None

class ScreenFlow(BaseModel):
    screen_name: str
    elements: List[ScreenElement]

class ComplianceRequest(BaseModel):
    flow: List[ScreenFlow]

class Violation(BaseModel):
    screen_name: str
    element_id: Optional[str] = None
    rule_broken: str
    severity: str   # "High" | "Medium" | "Low"
    fix_suggestion: str
    detected_by: str  # "layer1_deterministic" | "layer2_llm"

class ComplianceResponse(BaseModel):
    is_compliant: bool
    layer1_violations: int
    layer2_violations: int
    violations: List[Violation]


# ── Layer 1: Deterministic Rule Engine ───────────────────────────────────────
#
# Checks for explicit, unambiguous RBI dark-pattern signals that require
# no LLM inference — just text pattern matching and state inspection.

FALSE_URGENCY_PATTERNS = re.compile(
    r"(hurry|limited time|only \d+ (left|remaining)|offer expires|act now|"
    r"last chance|ends (in|soon)|don.t miss|seats? left|minutes? left|"
    r"seconds? left|time is running out)",
    re.IGNORECASE,
)

CANCEL_KEYWORDS = re.compile(
    r"(cancel|unsubscribe|opt.?out|end subscription|stop auto.?pay)",
    re.IGNORECASE,
)

TERMS_KEYWORDS = re.compile(
    r"(terms|conditions|t&c|privacy policy|tnc)",
    re.IGNORECASE,
)


def layer1_deterministic(flow: List[ScreenFlow]) -> List[Violation]:
    violations: List[Violation] = []

    for screen in flow:
        has_visible_cancel = False
        has_visible_terms  = False

        for el in screen.elements:
            text  = el.text  or ""
            state = (el.state or "").lower()
            eid   = el.id

            # Rule: Pre-checked consent (explicit state field)
            if el.type == "checkbox" and state == "pre-checked":
                violations.append(Violation(
                    screen_name=screen.screen_name,
                    element_id=eid,
                    rule_broken="Pre-checked Consent",
                    severity="High",
                    fix_suggestion=(
                        f"Element '{eid}' defaults to checked. All consent checkboxes "
                        "must be unchecked by default under RBI Guidelines (Feb 2026)."
                    ),
                    detected_by="layer1_deterministic",
                ))

            # Rule: False urgency — keyword in button/label text
            if FALSE_URGENCY_PATTERNS.search(text):
                violations.append(Violation(
                    screen_name=screen.screen_name,
                    element_id=eid,
                    rule_broken="False Urgency",
                    severity="Medium",
                    fix_suggestion=(
                        f"Element '{eid}' uses urgency language: \"{text[:80]}\". "
                        "Remove countdown timers or scarcity language that misrepresents stock/time."
                    ),
                    detected_by="layer1_deterministic",
                ))

            # Rule: Hidden cancellation button
            if CANCEL_KEYWORDS.search(text) and state == "hidden":
                violations.append(Violation(
                    screen_name=screen.screen_name,
                    element_id=eid,
                    rule_broken="Hidden Cancellation Path",
                    severity="High",
                    fix_suggestion=(
                        f"Element '{eid}' (cancel/opt-out) is marked hidden. "
                        "Cancellation must be as easy to find as the sign-up action."
                    ),
                    detected_by="layer1_deterministic",
                ))

            # Track presence for screen-level checks
            if CANCEL_KEYWORDS.search(text) and state != "hidden":
                has_visible_cancel = True
            if TERMS_KEYWORDS.search(text) and state not in ("hidden", "disabled"):
                has_visible_terms = True

        # Screen-level Rule: No cancellation path on any screen with a subscription element
        has_subscription_element = any(
            "subscri" in (el.text or "").lower() or "mandate" in (el.text or "").lower()
            for el in screen.elements
        )
        if has_subscription_element and not has_visible_cancel:
            violations.append(Violation(
                screen_name=screen.screen_name,
                element_id=None,
                rule_broken="Missing Cancellation Path",
                severity="High",
                fix_suggestion=(
                    f"Screen '{screen.screen_name}' presents a subscription/mandate element "
                    "but has no visible cancel option. An easy cancellation path is mandatory."
                ),
                detected_by="layer1_deterministic",
            ))

    return violations


# ── Layer 2: LLM Semantic Analysis ───────────────────────────────────────────
#
# Sends the FULL flow to the LLM only for violations that deterministic
# rules cannot catch: implied forced bundling, obscured terms, subtle
# interface pressure patterns. Uses Groq with Gemini fallback.

LLM_SYSTEM_PROMPT = """
You are a strict RBI compliance auditor specialising in digital dark patterns.

The user will send you a JSON representation of a payment mandate/subscription UX flow.
You must check ONLY for the following hard-to-detect, semantically ambiguous violations
that CANNOT be caught by simple keyword or state matching:

1. Forced Product Bundling — A user cannot proceed without purchasing/accepting an
   additional product they did not explicitly choose.
2. Obscured Terms & Conditions — Terms are present but require unusual navigation to
   access (e.g., hidden behind a tooltip, displayed in <8px font hint, or absent entirely).
3. Interface Pressure — Layout, button sizing, or label colour/phrasing nudges a user
   toward a more expensive or binding option without explicit coercion (subtle patterns only).

Do NOT re-report violations you would catch with:
- Pre-checked checkboxes (already handled deterministically)
- Explicit urgency countdown text (already handled deterministically)
- Hidden cancel buttons with cancel-related text (already handled deterministically)

Return a valid JSON object with this exact schema:
{
  "llm_violations": [
    {
      "screen_name": string,
      "element_id": string | null,
      "rule_broken": string,
      "severity": "High" | "Medium" | "Low",
      "fix_suggestion": string
    }
  ]
}
Return an empty llm_violations list if no semantic violations are found.
Do NOT return any text outside the JSON object.
"""


def _call_llm(flow_json: str) -> List[dict]:
    """Calls Groq, with Gemini fallback. Returns list of raw violation dicts."""

    # --- Groq ---
    if GROQ_API_KEY:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "groq/compound",
                    "messages": [
                        {"role": "system", "content": LLM_SYSTEM_PROMPT},
                        {"role": "user",   "content": flow_json},
                    ],
                    "temperature": 0.1,
                },
                timeout=10,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            content = re.sub(r"^```json|^```|```$", "", content.strip(), flags=re.MULTILINE).strip()
            return json.loads(content).get("llm_violations", [])
        except Exception as groq_err:
            print(f"[Layer2] Groq failed: {groq_err}. Trying Gemini...")

    # --- Gemini fallback ---
    if GEMINI_API_KEY:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
            )
            resp = requests.post(
                url,
                json={
                    "contents": [{"parts": [{"text": LLM_SYSTEM_PROMPT + "\n\n" + flow_json}]}],
                    "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
                },
                timeout=15,
            )
            resp.raise_for_status()
            content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(content.strip()).get("llm_violations", [])
        except Exception as gemini_err:
            print(f"[Layer2] Gemini failed: {gemini_err}. Skipping LLM layer.")

    return []


def layer2_llm(flow: List[ScreenFlow]) -> List[Violation]:
    flow_json = json.dumps([s.model_dump() for s in flow])
    raw = _call_llm(flow_json)
    violations = []
    for v in raw:
        try:
            violations.append(Violation(
                screen_name=v["screen_name"],
                element_id=v.get("element_id"),
                rule_broken=v["rule_broken"],
                severity=v.get("severity", "Medium"),
                fix_suggestion=v["fix_suggestion"],
                detected_by="layer2_llm",
            ))
        except Exception:
            continue
    return violations


# ── Aggregation ───────────────────────────────────────────────────────────────

def deduplicate(violations: List[Violation]) -> List[Violation]:
    """Remove duplicate violations by (screen_name, rule_broken) key.
    Layer 1 results always win over Layer 2 for the same rule on the same screen."""
    seen: dict[tuple, Violation] = {}
    for v in violations:
        key = (v.screen_name, v.rule_broken.lower())
        if key not in seen or v.detected_by == "layer1_deterministic":
            seen[key] = v
    return list(seen.values())


# ── API Endpoint ──────────────────────────────────────────────────────────────

@app.post("/api/v1/scan-compliance", response_model=ComplianceResponse)
async def scan_compliance(request: ComplianceRequest):
    # Layer 1 — always runs, zero latency
    l1_violations = layer1_deterministic(request.flow)

    # Layer 2 — LLM semantic analysis
    l2_violations = layer2_llm(request.flow)

    all_violations = deduplicate(l1_violations + l2_violations)

    return ComplianceResponse(
        is_compliant=len(all_violations) == 0,
        layer1_violations=len(l1_violations),
        layer2_violations=len(l2_violations),
        violations=all_violations,
    )


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "compliance-scanner", "version": "2.0-pipeline"}
