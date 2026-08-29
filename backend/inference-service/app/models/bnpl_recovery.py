import os
import math
import joblib
from pydantic import BaseModel
from typing import Optional

# λ = 0.023 → external debt signal half-life of ~30 days
# In production, calibrate against empirical borrower cohort data
DEBT_SIGNAL_DECAY_LAMBDA = 0.023

class BNPLRecoveryInput(BaseModel):
    internal_debt: float
    external_ecosystem_debt: float
    days_since_login: int
    demographic_age: int
    # Preprocessing gate fields — never passed directly to the ML model
    # consent_revoked: DPDP Act compliance gate. If True + data stale > 30 days,
    #   external_ecosystem_debt is zeroed out BEFORE the model sees it.
    #   It is deliberately excluded as a tree feature to prevent a chilling effect
    #   on the Right to Erasure.
    consent_revoked: bool = False
    external_debt_data_age_days: int = 0

class BNPLRecoveryOutput(BaseModel):
    recommended_channel: str
    channel_id: int
    effective_external_debt_used: float  # Expose for audit/explainability


def compute_effective_external_debt(
    raw_debt: float,
    data_age_days: int,
    consent_revoked: bool
) -> float:
    """
    Preprocessing gate — runs BEFORE the model.
    
    1. Hard DPDP consent gate: revoked + stale > 30 days → zero out signal.
    2. Exponential decay: 30-day half-life applied to all other cases.
    """
    if consent_revoked and data_age_days > 30:
        return 0.0
    decay_factor = math.exp(-DEBT_SIGNAL_DECAY_LAMBDA * data_age_days)
    return raw_debt * decay_factor


class BNPLRecoveryModel:
    def __init__(self, model_dir: str):
        self.model_path = os.path.join(model_dir, "feature_f_recovery.joblib")
        self.model = None
        self.channel_map = {0: "email", 1: "sms", 2: "voice"}

        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"Loaded BNPL Recovery model from {self.model_path}")
        else:
            print(f"WARNING: BNPL Recovery model not found at {self.model_path}")

    def predict(self, input_data: BNPLRecoveryInput) -> BNPLRecoveryOutput:
        if self.model is None:
            raise ValueError("BNPL Recovery model is not loaded")

        # ── PREPROCESSING GATE ────────────────────────────────────────────
        # Apply consent gate + exponential decay BEFORE the model.
        # The model NEVER receives consent_revoked as a feature.
        effective_external_debt = compute_effective_external_debt(
            raw_debt=input_data.external_ecosystem_debt,
            data_age_days=input_data.external_debt_data_age_days,
            consent_revoked=input_data.consent_revoked,
        )

        # ── MODEL INFERENCE ───────────────────────────────────────────────
        # Features must match the exact columns trained in train_bnpl_recovery.py
        features = [[
            input_data.internal_debt,
            effective_external_debt,
            input_data.days_since_login,
            input_data.demographic_age
        ]]

        channel_id = int(self.model.predict(features)[0])
        channel_name = self.channel_map.get(channel_id, "email")

        return BNPLRecoveryOutput(
            recommended_channel=channel_name,
            channel_id=channel_id,
            effective_external_debt_used=effective_external_debt
        )
