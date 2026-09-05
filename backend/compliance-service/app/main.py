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
import concurrent.futures
import redis
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Query
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
REDIS_URL      = os.getenv("REDIS_URL", "redis://redis:6379")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


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
   additional product they did not explicitly choose (e.g., auto-added items).
2. Obscured Terms & Conditions — Terms are present but require unusual navigation to
   access or are intentionally hard to read. EXAMPLES: font sizes < 8px, terms hidden
   inside a hover tooltip, or extremely low contrast colors (like light grey on white).
3. Interface Pressure — Layout, button sizing, or label colour/phrasing nudges a user
   toward a more expensive or binding option without explicit coercion. EXAMPLE:
   "Confirmshaming" where the decline button says something insulting like "No thanks,
   I prefer to lose money" or "I hate good deals", or tricking the user by making the 
   cancel button look like unclickable plain text.

CRITICAL RULES:
- Do NOT re-report violations you would catch with:
  - Pre-checked checkboxes (already handled deterministically)
  - Explicit urgency countdown text or "Hurry, only X left" (already handled deterministically)
  - Hidden cancel buttons with cancel-related text (already handled deterministically)
- Do NOT hallucinate violations on perfectly clean UI screens. If a screen has a standard,
  unchecked "I agree to Terms & Conditions" label and a normal "Cancel" button, it is COMPLIANT.

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


def _call_groq(flow_json: str) -> List[dict]:
    if not GROQ_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama3-70b-8192",
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
    except Exception as e:
        print(f"[Layer2] Groq failed: {e}")
        return []


def _call_gemini(flow_json: str) -> List[dict]:
    if not GEMINI_API_KEY:
        return []
    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
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
    except Exception as e:
        print(f"[Layer2] Gemini failed: {e}")
        return []


def layer2_llm(flow: List[ScreenFlow]) -> List[Violation]:
    if not flow:
        return []

    flow_json = json.dumps([s.model_dump() for s in flow])
    
    raw_groq = []
    raw_gemini = []

    # Run both LLMs concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_groq = executor.submit(_call_groq, flow_json)
        future_gemini = executor.submit(_call_gemini, flow_json)
        
        raw_groq = future_groq.result()
        raw_gemini = future_gemini.result()

    violations_map = {}

    def process_raw(raw_list: List[dict], detected_by: str):
        for v in raw_list:
            try:
                screen_name = v["screen_name"]
                rule_broken = v["rule_broken"]
                key = (screen_name, rule_broken.lower())
                
                # If both find the exact same rule on the same screen, mark it as consensus
                if key in violations_map:
                    violations_map[key].detected_by = "layer2_llm_ensemble_consensus"
                else:
                    violations_map[key] = Violation(
                        screen_name=screen_name,
                        element_id=v.get("element_id"),
                        rule_broken=rule_broken,
                        severity=v.get("severity", "Medium"),
                        fix_suggestion=v["fix_suggestion"],
                        detected_by=detected_by,
                    )
            except Exception:
                continue

    process_raw(raw_groq, "layer2_llm_groq")
    process_raw(raw_gemini, "layer2_llm_gemini")

    return list(violations_map.values())


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

class RBIDunningResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    ist_time: str
    attempts_today: int

@app.get("/api/v1/compliance/rbi-dunning-window", response_model=RBIDunningResponse)
async def rbi_dunning_window(borrower_id: str = Query(...)):
    # 1. Check strict IST (UTC+5:30) time window (8 AM to 7 PM)
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist_tz)
    
    hour = now_ist.hour
    date_str = now_ist.strftime("%Y-%m-%d")
    time_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    
    # 2. Redis Anti-Harassment Rate Limiting (max 3 calls per day)
    redis_key = f"dunning_attempts:{borrower_id}:{date_str}"
    
    try:
        attempts = int(redis_client.get(redis_key) or 0)
    except Exception as e:
        print(f"Redis error: {e}")
        attempts = 0 # Fail open on redis error for the sake of this prototype

    if hour < 8 or hour >= 19:
        return RBIDunningResponse(
            allowed=False,
            reason="outside_legal_hours",
            ist_time=time_str,
            attempts_today=attempts
        )
        
    if attempts >= 3:
        return RBIDunningResponse(
            allowed=False,
            reason="anti_harassment_limit_exceeded",
            ist_time=time_str,
            attempts_today=attempts
        )
        
    # Increment attempt counter
    try:
        redis_client.incr(redis_key)
        # expire at the end of the day (roughly 24 hours is fine here)
        redis_client.expire(redis_key, 86400)
    except Exception as e:
        print(f"Redis error: {e}")
        
    return RBIDunningResponse(
        allowed=True,
        reason=None,
        ist_time=time_str,
        attempts_today=attempts + 1
    )
