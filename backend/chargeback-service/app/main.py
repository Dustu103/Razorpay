import os
import re
import json
import requests
import concurrent.futures
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

from .reason_code_map import REASON_CODE_EVIDENCE_MAP
from .context_bridge import build_context_prompt
from .hallucination_guard import clean_hallucinations

INFERENCE_SERVICE_URL = os.getenv("INFERENCE_SERVICE_URL", "http://localhost:8000")

# ── Fatal Reason Code Blocklist ────────────────────────────────────────────────
# These are merchant-error codes where the chargeback outcome is legally
# predetermined. An ML model cannot override procedural law. Fighting these
# codes wastes non-refundable arbitration fees.
FATAL_REASON_CODES = {
    "mc_4808",   # Authorization-related — merchant failed to obtain valid auth
    "mc_4834",   # Duplicate processing — merchant charged the customer twice
    "mc_4831",   # Transaction amount differs — merchant altered the amount
    "visa_12.6", # Duplicate processing
    "visa_12.5", # Incorrect transaction amount
}

# ── VAMP Threshold Tiers (Visa Acquirer Monitoring Program) ───────────────────
# Effective April 1, 2026. Source: Visa VAMP global policy.
VAMP_DANGER_THRESHOLD = 0.015  # 1.5% → Excessive zone: severe fees + possible account termination
VAMP_WARNING_THRESHOLD = 0.012 # 1.2% → Warning zone: proactive deflection recommended

app = FastAPI(title="Chargeback Pre-emption Service API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")



# Pydantic models for request/response validation
class DisputeRequest(BaseModel):
    reason_code: str = Field(..., example="visa_10.4")
    network: str = Field(..., example="visa")
    has_3ds_auth: int = Field(0, ge=0, le=1)
    has_delivery_proof: int = Field(0, ge=0, le=1)
    has_avs_cvv_match: int = Field(0, ge=0, le=1)
    has_ip_device_fingerprint: int = Field(0, ge=0, le=1)
    has_prior_comms: int = Field(0, ge=0, le=1)
    has_signed_receipt: int = Field(0, ge=0, le=1)
    has_usage_logs: int = Field(0, ge=0, le=1)
    days_remaining: int = Field(14, ge=1)
    days_since_transaction: int = Field(30, ge=0)
    repeat_dispute_count: int = Field(0, ge=0)
    transaction_amount_inr: float = Field(1000.0, ge=0.0)
    merchant_category: str = Field("ecommerce", example="saas")
    merchant_current_dispute_ratio: Optional[float] = Field(0.008, ge=0.0)  # VAMP protection trigger

class VampAdvisory(BaseModel):
    status: str
    message: str
    ratio_impact_warning: bool

class DisputeResponse(BaseModel):
    win_probability: float
    variance: float
    disagreement_flag: bool
    recommended_action: str
    individual_predictions: Dict[str, float]
    top_features: List[str]
    evidence_completeness_score: int
    vamp_advisory: VampAdvisory
    narrative: str
    llm_confidence: str
    redacted_artifacts: List[str]
    routing_path: str

# Helper functions to query LLMs
def call_groq_rebuttal(system: str, user: str) -> Optional[str]:
    if not GROQ_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "groq/compound",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                "temperature": 0.15,
                "max_tokens": 1000
            },
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[LLM Routing] Groq failed: {e}")
    return None

def call_gemini_rebuttal(system: str, user: str) -> Optional[str]:
    if not GEMINI_API_KEY:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
        combined_prompt = f"{system}\n\nTransaction Context:\n{user}"
        resp = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": combined_prompt}]}],
                "generationConfig": {"temperature": 0.15}
            },
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[LLM Routing] Gemini failed: {e}")
    return None

def score_narrative(narrative: str, request_data: DisputeRequest) -> float:
    """Evaluates narrative quality by verifying presence of expected evidence keywords."""
    score = 0.0
    if not narrative:
        return score
    
    # Standard format expectations
    if "Subject: Representment Rebuttal" in narrative or "Subject:" in narrative:
        score += 1.0
    
    # Check for evidence inclusion
    if request_data.has_3ds_auth == 1 and any(kw in narrative.lower() for kw in ["3d secure", "3ds", "authentication"]):
        score += 2.0
    if request_data.has_delivery_proof == 1 and any(kw in narrative.lower() for kw in ["delivery", "tracking", "carrier", "delivered"]):
        score += 2.0
    if request_data.has_avs_cvv_match == 1 and any(kw in narrative.lower() for kw in ["avs", "cvv", "verification", "match"]):
        score += 2.0
    if request_data.has_ip_device_fingerprint == 1 and any(kw in narrative.lower() for kw in ["ip", "device fingerprint", "fingerprint", "device id"]):
        score += 2.0
    if request_data.has_prior_comms == 1 and any(kw in narrative.lower() for kw in ["communication", "interaction", "support logs"]):
        score += 1.5

    # Penalize length issues (too short or way too verbose)
    length = len(narrative.split())
    if 80 <= length <= 450:
        score += 1.5
    
    return score

@app.get("/health")
def health():
    return {"status": "healthy", "service": "chargeback-pre-emption", "version": "2.1.0"}

@app.post("/api/v1/analyze-dispute", response_model=DisputeResponse)
def analyze_dispute(req: DisputeRequest):

    # ── Layer 1: Deterministic Engine ─────────────────────────────────────────
    code = req.reason_code
    rules = REASON_CODE_EVIDENCE_MAP.get(code)
    if not rules:
        raise HTTPException(status_code=400, detail=f"Unsupported reason code: {code}")

    # ── Fatal Reason Code Intercept ────────────────────────────────────────────
    # These codes represent merchant procedural errors. No ML model can override
    # legal liability. Intercept before the ML call to avoid wasting inference
    # compute and non-refundable arbitration fees.
    if code in FATAL_REASON_CODES:
        return DisputeResponse(
            win_probability=0.0,
            variance=0.0,
            disagreement_flag=False,
            recommended_action="deflect_via_refund",
            individual_predictions={},
            top_features=[],
            evidence_completeness_score=0,
            vamp_advisory=VampAdvisory(
                status="safe",
                message="Fatal reason code — merchant procedural error. Deflecting immediately.",
                ratio_impact_warning=False
            ),
            narrative=(
                f"This dispute ({code}) represents a merchant-side procedural error. "
                "Representment is legally inadmissible. Issuing an immediate refund is "
                "strongly recommended to avoid non-refundable arbitration fees."
            ),
            llm_confidence="n/a",
            redacted_artifacts=[],
            routing_path="skip_fatal_code_deflect"
        )

    # Evidence completeness score (0 = none, 1 = partial, 2 = complete)
    required = rules.get("required_evidence", [])
    if not required:
        completeness = 2
    else:
        present = sum(1 for r in required if getattr(req, r, 0) == 1)
        if present == 0:
            completeness = 0
        elif present < len(required):
            completeness = 1
        else:
            completeness = 2

    # ── VAMP Adjudication (Tiered) ─────────────────────────────────────────────
    # Visa VAMP effective April 1, 2026: Excessive threshold = 1.5%.
    # Tiered logic: danger zone (>=1.5%) is more aggressive than warning zone (>=1.2%).
    merchant_ratio = req.merchant_current_dispute_ratio or 0.0
    vamp_status = "safe"
    vamp_msg = "Merchant ratio is within safe limits."
    ratio_warning = False

    if merchant_ratio >= VAMP_DANGER_THRESHOLD:
        vamp_status = "danger"  # Excessive zone — severe fees risk
        ratio_warning = True
        vamp_msg = (f"CRITICAL: Dispute ratio ({merchant_ratio:.2%}) exceeds the Visa VAMP "
                    f"Excessive threshold ({VAMP_DANGER_THRESHOLD:.1%}). "
                    "Merchant faces penalty fees and account termination risk. Deflecting all but near-certain wins.")
    elif merchant_ratio >= VAMP_WARNING_THRESHOLD:
        vamp_status = "warning"  # Warning zone — proactive deflection
        ratio_warning = True
        vamp_msg = (f"WARNING: Dispute ratio ({merchant_ratio:.2%}) is approaching VAMP thresholds. "
                    "Deflecting borderline cases to protect merchant standing.")

    # ── ML Layer: Ensemble & Uncertainty Inference ────────────────────────────
    ml_input = req.dict()
    try:
        resp = requests.post(f"{INFERENCE_SERVICE_URL}/predict/chargeback", json=ml_input, timeout=5)
        resp.raise_for_status()
        ml_results = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reach Inference Service: {str(e)}")

    win_prob = ml_results["win_probability"]
    variance = ml_results["variance"]
    disagreement_flag = ml_results["disagreement_flag"]
    recommended_action = ml_results["recommended_action"]
    individual_preds = ml_results["individual_predictions"]
    top_features = ml_results["top_features"]

    # ── VAMP Override (Tiered Thresholds) ─────────────────────────────────────
    # Danger zone (>=1.5%): only fight near-certain wins (>= 95%) to protect
    # merchant account standing above all else.
    # Warning zone (>=1.2%): fight strong cases (>= 80%) but deflect borderline.
    # Near-limit zone (>=1.45%): approaching danger — aggressively deflect below 85%.
    if vamp_status == "danger" and win_prob < 0.95:
        recommended_action = "deflect_via_refund"
    elif merchant_ratio >= 0.0145 and win_prob < 0.85:
        # Near-limit: 1.45%-1.5% — one bad dispute away from Excessive zone
        recommended_action = "deflect_via_refund"
    elif vamp_status == "warning" and win_prob < 0.80:
        recommended_action = "deflect_via_refund"

    # ── Normalize ML action enum to 3 clean outputs ───────────────────────────
    # The inference gateway may return intermediate states that don't map cleanly
    # to business actions. Normalize to: auto_submit | deflect_via_refund | review
    if recommended_action == "one_tap_approval":
        recommended_action = "review"
    elif recommended_action == "await_merchant_approval":
        recommended_action = "review"

    # ── Business Rule Overrides (post-ML) ─────────────────────────────────────
    # These rules encode operational and financial constraints that the ML model
    # cannot learn from training data alone.

    # Rule: Critical deadline (≤2 days) — T+3 UDIR/gateway SLA nearly breached.
    # Even a winnable case cannot be properly represented in 48 hours under
    # Indian TAT rules. Force DEFLECT to avoid automatic loss.
    if req.days_remaining <= 2 and recommended_action == "auto_submit":
        recommended_action = "deflect_via_refund"

    # Rule: Ultra-high value disputes (>₹1,00,000 / $1,200 USD) — Indian issuers
    # apply intensive manual scrutiny above this amount. Always route to human
    # review regardless of ML confidence to protect against irreversible decisions.
    if req.transaction_amount_inr > 100000 and recommended_action == "auto_submit":
        recommended_action = "review"

    # Rule: Critical deadline with high-value — double-flag these for review
    # regardless of action. The stakes are too high for automated handling.
    if req.transaction_amount_inr > 100000 and req.days_remaining <= 3:
        recommended_action = "review"

    # ── Context Bridge & Prompt Optimization ──────────────────────────────────
    system_prompt, user_prompt = build_context_prompt(ml_input, top_features)

    # ── Layer 2: Cost-Aware LLM Routing ───────────────────────────────────────
    # Heuristics:
    # - Low value (< ₹5,000) OR simple reason code WITH complete evidence AND low variance (high confidence):
    #   Route to Single Model (Groq) for cost savings and low latency.
    # - High value (>= ₹5,000) OR high variance (disagreement) OR complex reason code:
    #   Run Multi-LLM Ensemble (Groq + Gemini) concurrently, then score and select the best narrative.
    
    is_simple_code = code in ("visa_13.1", "rupay_ru02", "rupay_ru03", "rupay_1085")
    is_high_confidence = not disagreement_flag and (win_prob >= 0.75 or win_prob <= 0.25)
    is_low_value = req.transaction_amount_inr < 5000.0

    routing_path = "single_llm_groq"
    narrative = ""
    llm_confidence = "high"

    # If evidence completeness is 0 (unwinnable), we don't even need a narrative.
    if completeness == 0 and recommended_action == "deflect_via_refund":
        narrative = "No representment drafted. This dispute lacks the minimum required evidence and has been recommended for deflection (refund) to protect your dispute ratio."
        routing_path = "skip_llm_deflect"
        llm_confidence = "low"
    else:
        if is_low_value and is_simple_code and is_high_confidence:
            # Route to single model (Groq)
            routing_path = "single_llm_groq"
            narrative = call_groq_rebuttal(system_prompt, user_prompt)
            if not narrative:
                # Fallback to Gemini
                routing_path = "single_llm_groq_fallback_gemini"
                narrative = call_gemini_rebuttal(system_prompt, user_prompt)
        else:
            # Multi-LLM Ensemble Parallel Execution
            routing_path = "multi_llm_ensemble"
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_groq = executor.submit(call_groq_rebuttal, system_prompt, user_prompt)
                future_gemini = executor.submit(call_gemini_rebuttal, system_prompt, user_prompt)
                
                groq_res = future_groq.result()
                gemini_res = future_gemini.result()

            # Narrative selection logic based on evidence matching score
            score_g = score_narrative(groq_res, req)
            score_m = score_narrative(gemini_res, req)

            if groq_res and gemini_res:
                if score_g >= score_m:
                    narrative = groq_res
                    routing_path = "multi_llm_ensemble (selected: groq)"
                else:
                    narrative = gemini_res
                    routing_path = "multi_llm_ensemble (selected: gemini)"
            elif groq_res:
                narrative = groq_res
                routing_path = "multi_llm_ensemble (fallback: groq)"
            elif gemini_res:
                narrative = gemini_res
                routing_path = "multi_llm_ensemble (fallback: gemini)"

        # Fallback if both LLMs failed
        if not narrative:
            narrative = f"Subject: Representment Rebuttal - Reason Code {code}\n\nWe hereby dispute this transaction of INR {req.transaction_amount_inr}. The charge was processed in full compliance with network rules."
            llm_confidence = "low"

    # ── Layer 3: Hallucination Guard ──────────────────────────────────────────
    cleaned_narrative, redacted_list = clean_hallucinations(narrative)

    return DisputeResponse(
        win_probability=round(win_prob, 4),
        variance=round(variance, 4),
        disagreement_flag=disagreement_flag,
        recommended_action=recommended_action,
        individual_predictions=individual_preds,
        top_features=top_features,
        evidence_completeness_score=completeness,
        vamp_advisory=VampAdvisory(
            status=vamp_status,
            message=vamp_msg,
            ratio_impact_warning=ratio_warning
        ),
        narrative=cleaned_narrative,
        llm_confidence=llm_confidence,
        redacted_artifacts=redacted_list,
        routing_path=routing_path
    )
