"""
Causal Net-EV Recovery Decision Engine
======================================
1. Feature Preprocessing: Standardizes session telemetry into causal feature space using native scikit-learn OneHotEncoder.
2. Dual Causal Inference:
   - Native LightGBM S-Learner predicts P(Y=1 | X, A) for all A in {none, whatsapp, sms, email}.
   - Native LightGBM RTO Model predicts P(RTO=1 | X, A) — conditioned on action, yielding
     separate r_0 (baseline) and r_a (per-channel) rates.
3. Exact Causal Economic Engine (general formula — no simplifying assumptions):

       ΔΠ_a = P_a[(1-r_a)(CM - D_a) - r_a·K_rto]
              - P_0[(1-r_0)·CM      - r_0·K_rto]
              - K_a

   Incentive D_a is charged on P_a (all treated completions), NOT on τ_a.
   Recommends argmax_a(ΔΠ_a) if max > 0, else SUPPRESS.
4. Generative Hinglish Messaging for the chosen intervention channel.
"""

import os
import math
import joblib
import pandas as pd
import numpy as np
from typing import Optional, Dict
from collections import Counter
from pydantic import BaseModel

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


# ── I/O Schemas ───────────────────────────────────────────────────────────────

class InterventionInput(BaseModel):
    session_id: str
    diagnosis: str
    cart_value: float
    duration_sec: int
    attempt_count: int = 1
    events_count: int = 3
    event_sequence: str = ""
    merchant_name: Optional[str] = None
    item_description: Optional[str] = None
    # Dynamic runtime economic parameters
    merchant_margin: Optional[float] = 0.25
    incentive_amount: Optional[float] = 0.0
    rto_cost_estimate: Optional[float] = 250.0
    channel_cost_wa: Optional[float] = 0.80
    channel_cost_sms: Optional[float] = 0.20
    channel_cost_email: Optional[float] = 0.05
    payment_method: Optional[str] = "upi"
    device: Optional[str] = "mobile_android"
    is_returning_customer: Optional[int] = 0


class InterventionOutput(BaseModel):
    action: str
    risk_score: float            # r_a for the chosen action (RTO rate under treatment)
    rto_rate_organic: float      # r_0 (RTO rate under no-action)
    recovery_prob: float
    organic_recovery_prob: float
    incremental_lift: float
    expected_profit: float       # ΔΠ_a for the chosen action
    recovery_message: str
    reasoning: str


# ── Helper Telemetry Functions ───────────────────────────────────────────────

def _compute_entropy(seq_str: str) -> float:
    if not seq_str:
        return 0.50
    events = [e.strip() for e in seq_str.split(",") if e.strip()]
    if len(events) < 2:
        return 0.50
    counts = Counter(events)
    total = len(events)
    return float(-sum((c / total) * math.log2(c / total) for c in counts.values()))


# ── LLM Hinglish Generation ───────────────────────────────────────────────────

HINGLISH_TEMPLATES = {
    "upi_app_switch_abort": "Arre yaar! 😅 Aapka payment thoda ruk gaya. UPI app switch ho gaya tha. Abhi complete karein: {link}",
    "otp_timeout": "OTP mila nahi? No tension! 🔄 Dobara try karein, is baar ho jaayega. Aapka order wait kar raha hai: {link}",
    "vpa_validation_failure": "UPI ID thodi galat thi shayad? 🤔 Ek baar check karo aur phir se try karo 👉 {link}",
    "price_shock_breakdown": "Kuch zyada laga total? 😮 Hum samajhte hain! Abhi complete karo aur pao instant discount: {link}",
    "genuine_browse_abandon": "Aapka cart abhi bhi aapka intezaar kar raha hai! 🛒 Jaldi karo, stock limited hai: {link}",
    # Aliases for compatibility
    "app_switch_failure": "Arre yaar! 😅 Aapka payment thoda ruk gaya. UPI app switch ho gaya tha. Abhi complete karein: {link}",
    "otp_delivery_delay": "OTP mila nahi? No tension! 🔄 Dobara try karein, is baar ho jaayega. Aapka order wait kar raha hai: {link}",
    "vpa_validation_abort": "UPI ID thodi galat thi shayad? 🤔 Ek baar check karo aur phir se try karo 👉 {link}",
    "price_shock": "Kuch zyada laga total? 😮 Hum samajhte hain! Abhi complete karo aur pao instant discount: {link}",
    "genuine_abandonment": "Aapka cart abhi bhi aapka intezaar kar raha hai! 🛒 Jaldi karo, stock limited hai: {link}",
}

def _generate_hinglish_message(diagnosis: str, link: str, cart_value: float, discount: float = 0.0) -> str:
    template = HINGLISH_TEMPLATES.get(diagnosis, HINGLISH_TEMPLATES["genuine_browse_abandon"])
    fallback = template.format(link=link)
    if discount > 0:
        fallback = f"Special Offer! Save ₹{int(discount)} on your ₹{cart_value} cart: {link}"
        
    api_key = os.getenv("GROQ_API_KEY")
    if not (GROQ_AVAILABLE and api_key):
        return fallback

    prompt = (
        f"Write a 1-sentence friendly Hinglish (Hindi+English in Roman script) message for a dropped checkout of ₹{cart_value}. "
        f"Reason: {diagnosis}. Discount: ₹{discount}. End with this link: {link}. Keep it very short and conversational."
    )
    try:
        client = Groq(api_key=api_key)
        res = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=60
        )
        msg = res.choices[0].message.content.strip()
        if any('\u0900' <= c <= '\u097F' for c in msg):
            return fallback
        return msg
    except Exception:
        return fallback


# ── Main Causal Intervention System ───────────────────────────────────────────

class InterventionModel:
    def __init__(self, model_dir="/app/models/ml"):
        if not os.path.exists(model_dir):
            model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "models", "ml")
        
        self.encoder = None
        self.s_model = None
        self.rto_model = None
        self.model_dir = model_dir
        
        self.actions = ["none", "whatsapp", "sms", "email"]
        self.action_to_idx = {a: i for i, a in enumerate(self.actions)}
        self.numerical_cols = [
            "cart_value", "duration_sec", "attempt_count", "events_count",
            "sequence_entropy", "mean_inter_event_time", "is_returning_customer"
        ]
        self.categorical_cols = ["payment_method", "device", "diagnosis"]
        
        self._load_artifacts()

    def _load_artifacts(self):
        enc_path = os.path.join(self.model_dir, "causal_preprocessor_encoder.pkl")
        s_path = os.path.join(self.model_dir, "causal_s_model.pkl")
        rto_path = os.path.join(self.model_dir, "causal_rto_model.pkl")
        
        if os.path.exists(enc_path) and os.path.exists(s_path) and os.path.exists(rto_path):
            try:
                self.encoder = joblib.load(enc_path)
                self.s_model = joblib.load(s_path)
                self.rto_model = joblib.load(rto_path)
                print("[InterventionModel] Successfully loaded native Causal Models & Encoder.")
            except Exception as e:
                print(f"[InterventionModel] Failed to load causal models: {e}. Falling back.")
        else:
            print(f"[InterventionModel] Causal models not found at {self.model_dir}. Running in fallback mode.")

    def _action_feature_vector(self, X_base: np.ndarray, action: str) -> np.ndarray:
        """Build the full feature vector [X_base | action_onehot | X×A interactions]."""
        n = 1
        action_onehot = np.zeros((n, len(self.actions)))
        if action in self.action_to_idx:
            action_onehot[0, self.action_to_idx[action]] = 1.0

        interactions = np.hstack([
            X_base * action_onehot[:, a_idx:a_idx+1]
            for a_idx in range(len(self.actions))
        ])
        return np.hstack([X_base, action_onehot, interactions])

    def _predict_action_prob(self, X_base: np.ndarray, action: str) -> float:
        """P(Y=1 | X, A=action) from S-Learner."""
        X_all = self._action_feature_vector(X_base, action)
        return float(self.s_model.predict_proba(X_all)[0, 1])

    def _predict_rto_prob(self, X_base: np.ndarray, action: str) -> float:
        """P(RTO=1 | X, A=action) — action-conditioned RTO rate.

        Uses the same action-feature construction as the outcome model so
        the RTO model can learn that e.g. WhatsApp attracts slightly more
        impulsive (higher-RTO) buyers than email.
        """
        X_all = self._action_feature_vector(X_base, action)
        return float(self.rto_model.predict_proba(X_all)[0, 1])

    def predict(self, data: InterventionInput) -> InterventionOutput:
        recovery_link = f"https://rzp.io/r/{data.session_id[:8]}"
        
        # Standardize diagnosis aliases
        diag = data.diagnosis
        if diag == "app_switch_failure": diag = "upi_app_switch_abort"
        elif diag == "otp_delivery_delay": diag = "otp_timeout"
        elif diag == "vpa_validation_abort": diag = "vpa_validation_failure"
        elif diag == "price_shock": diag = "price_shock_breakdown"
        elif diag == "genuine_abandonment": diag = "genuine_browse_abandon"
        
        entropy = _compute_entropy(data.event_sequence)
        mean_iet = float(data.duration_sec) / max(1, data.events_count)
        
        # DataFrame for encoder
        df_row = pd.DataFrame([{
            "cart_value": float(data.cart_value),
            "duration_sec": int(data.duration_sec),
            "attempt_count": int(data.attempt_count),
            "events_count": int(data.events_count),
            "sequence_entropy": entropy,
            "mean_inter_event_time": mean_iet,
            "is_returning_customer": int(data.is_returning_customer or 0),
            "payment_method": str(data.payment_method or "upi"),
            "device": str(data.device or "mobile_android"),
            "diagnosis": diag
        }])
        
        # Model Inference
        if self.encoder is not None and self.s_model is not None and self.rto_model is not None:
            try:
                num_vals = df_row[self.numerical_cols].values
                cat_vals = self.encoder.transform(df_row[self.categorical_cols])
                X_base = np.hstack([num_vals, cat_vals])

                # Outcome probabilities P(Y=1 | X, A)
                p0      = self._predict_action_prob(X_base, "none")
                p_wa    = self._predict_action_prob(X_base, "whatsapp")
                p_sms   = self._predict_action_prob(X_base, "sms")
                p_email = self._predict_action_prob(X_base, "email")

                # Action-conditioned RTO rates r(A) — SEPARATE for baseline and each action
                r0      = self._predict_rto_prob(X_base, "none")
                r_wa    = self._predict_rto_prob(X_base, "whatsapp")
                r_sms   = self._predict_rto_prob(X_base, "sms")
                r_email = self._predict_rto_prob(X_base, "email")
            except Exception as e:
                print(f"[InterventionModel] Inference exception: {e}, using heuristic fallback.")
                p0, p_wa, p_sms, p_email, r0, r_wa, r_sms, r_email = self._heuristic_probs(diag, data.cart_value)
        else:
            p0, p_wa, p_sms, p_email, r0, r_wa, r_sms, r_email = self._heuristic_probs(diag, data.cart_value)
            
        # ── Causal Economic Decision Engine ───────────────────────────────────
        # General formula (no simplifying assumptions on r_a = r_0):
        #   ΔΠ_a = P_a[(1-r_a)(CM - D_a) - r_a·K_rto]
        #          - P_0[(1-r_0)·CM       - r_0·K_rto]
        #          - K_a
        # D_a (discount) is charged on P_a — all treated completions, not τ_a.
        margin   = float(data.merchant_margin      if data.merchant_margin      is not None else 0.25)
        cart     = float(data.cart_value)
        rto_cost = float(data.rto_cost_estimate    if data.rto_cost_estimate    is not None else 250.0)
        cm       = cart * margin

        costs = {
            "whatsapp": float(data.channel_cost_wa    or 0.80),
            "sms":      float(data.channel_cost_sms   or 0.20),
            "email":    float(data.channel_cost_email or 0.05),
        }
        # Incentive D_a: applied to ALL treated completions (P_a), not just incremental ones.
        incentives = {
            "whatsapp": float(data.incentive_amount or 0.0),
            "sms":      float(data.incentive_amount or 0.0),
            "email":    float(data.incentive_amount or 0.0),
        }

        p_candidates = {"whatsapp": p_wa,   "sms": p_sms,   "email": p_email}
        r_candidates = {"whatsapp": r_wa,   "sms": r_sms,   "email": r_email}

        # Baseline organic expected profit: P_0 * [(1-r_0)*CM - r_0*K_rto]
        base_profit = p0 * ((1.0 - r0) * cm - r0 * rto_cost)

        best_action   = "none"
        best_delta_pi = 0.0
        best_p        = p0
        best_r_a      = r0
        deltas        = {}

        for a in ["whatsapp", "sms", "email"]:
            pa  = p_candidates[a]
            ra  = r_candidates[a]
            d_a = incentives[a]
            k_a = costs[a]

            # ΔΠ_a  — exact general formula
            action_profit = pa * ((1.0 - ra) * (cm - d_a) - ra * rto_cost) - k_a
            delta         = action_profit - base_profit
            deltas[a]     = delta

            if delta > best_delta_pi:
                best_delta_pi = delta
                best_action   = a
                best_p        = pa
                best_r_a      = ra

        lift = max(0.0, best_p - p0) if best_action != "none" else 0.0

        reasoning = (
            f"P0={p0:.3f} r0={r0:.3f} | "
            f"ΔΠ(WA)=₹{deltas['whatsapp']:.2f} "
            f"ΔΠ(SMS)=₹{deltas['sms']:.2f} "
            f"ΔΠ(Email)=₹{deltas['email']:.2f}"
        )

        if best_action == "none":
            action_label = "NO_ACTION"
            reasoning    = "SUPPRESSED. " + reasoning
            msg          = ""
        else:
            action_label = best_action
            reasoning    = (
                f"RECOMMEND {best_action.upper()} "
                f"(ΔΠ=+₹{best_delta_pi:.2f}, r_a={best_r_a:.3f}). "
                + reasoning
            )
            msg = _generate_hinglish_message(diag, recovery_link, cart, incentives[best_action])

        return InterventionOutput(
            action                = action_label,
            risk_score            = round(best_r_a, 3),   # r_a for chosen action
            rto_rate_organic      = round(r0,        3),   # r_0 baseline
            recovery_prob         = round(best_p,    3),
            organic_recovery_prob = round(p0,        3),
            incremental_lift      = round(lift,      3),
            expected_profit       = round(best_delta_pi, 2),
            recovery_message      = msg,
            reasoning             = reasoning,
        )

    def _heuristic_probs(self, diag: str, cart: float):
        """Principled fallback based on empirical causal baseline.

        Returns:
            (p0, p_wa, p_sms, p_email, r0, r_wa, r_sms, r_email)

        r values are action-conditioned RTO rates matching the simulator's
        logit shifts: WA/SMS +0.05 vs baseline, Email -0.05 vs baseline.
        """
        if diag in ["upi_app_switch_abort", "app_switch_failure"]:
            p0, p_wa, p_sms, p_email = 0.35, 0.68, 0.50, 0.38
            r0 = 0.08
        elif diag in ["otp_timeout", "otp_delivery_delay"]:
            p0, p_wa, p_sms, p_email = 0.25, 0.55, 0.60, 0.30
            r0 = 0.10
        elif diag in ["price_shock_breakdown", "price_shock"]:
            p0, p_wa, p_sms, p_email = 0.08, 0.35, 0.25, 0.15
            r0 = 0.12
        elif diag in ["vpa_validation_failure", "vpa_validation_abort"]:
            p0, p_wa, p_sms, p_email = 0.15, 0.52, 0.40, 0.20
            r0 = 0.08
        else:  # genuine_browse_abandon
            p0, p_wa, p_sms, p_email = 0.05, 0.12, 0.08, 0.06
            r0 = 0.18

        # WA/SMS elevate RTO slightly; Email reduces it slightly
        def _sigmoid_shift(r: float, shift: float) -> float:
            import math
            lo = math.log(r / (1 - r)) if 0 < r < 1 else 0.0
            return 1.0 / (1.0 + math.exp(-(lo + shift)))

        r_wa    = _sigmoid_shift(r0,  0.05)
        r_sms   = _sigmoid_shift(r0,  0.05)
        r_email = _sigmoid_shift(r0, -0.05)
        return p0, p_wa, p_sms, p_email, r0, r_wa, r_sms, r_email
