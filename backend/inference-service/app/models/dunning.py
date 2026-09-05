import os
import joblib
import pandas as pd
from pydantic import BaseModel
from typing import Optional


class DunningInput(BaseModel):
    channel_encoded: int          # 0: Email, 1: SMS, 2: Push
    time_since_failure_mins: int
    customer_tenure_months: int
    prior_payment_success_rate: float
    # NACH-aware fields — optional, zero-valued for UPI/card transactions.
    product_type: Optional[str] = ""         # "sip" | "loan_emi" | "insurance_premium" | ""
    consequence_severity: Optional[str] = "" # "credit_score_risk" | "investment_lapse_risk" | "policy_lapse_risk" | ""


class DunningOutput(BaseModel):
    payment_probability: float
    recommended_channel: str
    consequence_severity: str   # Passed through for the audit trail
    urgency_tier: str           # "standard" | "elevated" | "critical"


# Urgency tiers govern which channels are available and override weak model recommendations.
# - standard:  any channel (ML model decides)
# - elevated:  SMS or WhatsApp only (no email)
# - critical:  WhatsApp only (immediate human contact required)
_CONSEQUENCE_URGENCY = {
    "credit_score_risk":     "critical",   # EMI: credit bureau window is a hard deadline
    "investment_lapse_risk": "elevated",   # SIP: AMC cancellation if unresolved
    "policy_lapse_risk":     "elevated",   # Insurance: lapse is immediate but not as irreversible
    "":                      "standard",
}

# Minimum channel for each urgency tier.
# The dunning ML model's recommendation is only used when urgency == "standard".
# Otherwise, the urgency tier overrides the model to guarantee delivery quality.
_URGENCY_CHANNEL_OVERRIDE = {
    "critical":  "whatsapp",  # WhatsApp has the highest open rate for urgent payment comms
    "elevated":  "sms",       # SMS reaches even users who have WhatsApp disabled
    "standard":  None,        # No override — ML model picks the optimal channel
}

_CHANNEL_MAP = {0: "email", 1: "sms", 2: "push"}


class DunningModel:
    def __init__(self, model_dir: str):
        self.model_path = os.path.join(model_dir, "feature_c.joblib")
        self.model = None

        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"Loaded Dunning Optimization model from {self.model_path}")
        else:
            print(f"WARNING: Dunning Optimization model not found at {self.model_path}")

    def predict(self, input_data: DunningInput) -> DunningOutput:
        if self.model is None:
            raise ValueError("Dunning Optimization model is not loaded")

        features = pd.DataFrame([[
            input_data.channel_encoded,
            input_data.time_since_failure_mins,
            input_data.customer_tenure_months,
            input_data.prior_payment_success_rate,
        ]], columns=[
            "channel_encoded",
            "time_since_failure_mins",
            "customer_tenure_months",
            "prior_payment_success_rate",
        ])

        prob = self.model.predict_proba(features)[0][1]
        ml_channel = _CHANNEL_MAP.get(input_data.channel_encoded, "email")

        # Resolve consequence severity and urgency tier.
        severity = input_data.consequence_severity or ""
        urgency = _CONSEQUENCE_URGENCY.get(severity, "standard")

        # Apply urgency override if applicable.
        # This is deterministic, not ML — the urgency of credit bureau reporting
        # or AMC cancellation is a known fact, not a probabilistic estimate.
        override = _URGENCY_CHANNEL_OVERRIDE.get(urgency)
        recommended = override if override is not None else ml_channel

        return DunningOutput(
            payment_probability=float(prob),
            recommended_channel=recommended,
            consequence_severity=severity,
            urgency_tier=urgency,
        )
