"""
Unit & Behavioral Tests: NACH Dunning Urgency Tiers & Channel Routing
======================================================================
Validates the product-aware dunning optimization logic implemented in
backend/inference-service/app/models/dunning.py.

Invariants tested:
1. Urgency Tier Mapping:
   - 'credit_score_risk'     -> 'critical'
   - 'investment_lapse_risk' -> 'elevated'
   - 'policy_lapse_risk'     -> 'elevated'
   - '' / unspecified        -> 'standard'

2. Channel Override Guarantees:
   - Critical urgency MUST override to 'whatsapp' regardless of ML/encoded channel.
   - Elevated urgency MUST override to 'sms' regardless of ML/encoded channel.
   - Standard urgency MUST preserve ML channel recommendation without override.

3. Mathematical & Audit Invariants:
   - 0.0 <= payment_probability <= 1.0
   - consequence_severity and urgency_tier are preserved in DunningOutput for compliance audit.
"""

import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "backend", "inference-service"))

from app.models.dunning import (
    DunningModel,
    DunningInput,
    DunningOutput,
    _CONSEQUENCE_URGENCY,
    _URGENCY_CHANNEL_OVERRIDE,
    _CHANNEL_MAP,
)


def test_dunning_static_mappings():
    """Verify static mapping dictionaries conform to NACH policy requirements."""
    assert _CONSEQUENCE_URGENCY["credit_score_risk"] == "critical"
    assert _CONSEQUENCE_URGENCY["investment_lapse_risk"] == "elevated"
    assert _CONSEQUENCE_URGENCY["policy_lapse_risk"] == "elevated"
    assert _CONSEQUENCE_URGENCY[""] == "standard"

    assert _URGENCY_CHANNEL_OVERRIDE["critical"] == "whatsapp"
    assert _URGENCY_CHANNEL_OVERRIDE["elevated"] == "sms"
    assert _URGENCY_CHANNEL_OVERRIDE["standard"] is None

    assert _CHANNEL_MAP[0] == "email"
    assert _CHANNEL_MAP[1] == "sms"
    assert _CHANNEL_MAP[2] == "push"
    print("  PASS: Static mappings and policy tables verified.")


def test_dunning_model_loaded():
    """Verify model can be loaded from models/ml."""
    model_dir = "models/ml" if os.path.exists("models/ml") else "/app/models/ml"
    model = DunningModel(model_dir)
    assert model.model is not None, f"Feature C model not loaded from {model_dir}"
    print(f"  PASS: Feature C model loaded successfully from {model_dir}.")
    return model


def test_standard_urgency_uses_ml_channel(model: DunningModel):
    """When consequence_severity is empty (standard), ML channel is preserved."""
    for ch_code, expected_ch in _CHANNEL_MAP.items():
        inp = DunningInput(
            channel_encoded=ch_code,
            time_since_failure_mins=15,
            customer_tenure_months=12,
            prior_payment_success_rate=0.90,
            product_type="",
            consequence_severity="",
        )
        out = model.predict(inp)

        assert out.urgency_tier == "standard", f"Expected standard tier, got {out.urgency_tier}"
        assert out.recommended_channel == expected_ch, (
            f"Expected ML channel {expected_ch}, got {out.recommended_channel}"
        )
        assert out.consequence_severity == ""
        assert 0.0 <= out.payment_probability <= 1.0
    print("  PASS: Standard urgency correctly preserves ML channel across channels {0, 1, 2}.")


def test_critical_urgency_forces_whatsapp(model: DunningModel):
    """Credit bureau risk (EMI) MUST override channel to WhatsApp unconditionally."""
    for ch_code in [0, 1, 2]: # Email, SMS, Push
        inp = DunningInput(
            channel_encoded=ch_code,
            time_since_failure_mins=60,
            customer_tenure_months=24,
            prior_payment_success_rate=0.75,
            product_type="loan_emi",
            consequence_severity="credit_score_risk",
        )
        out = model.predict(inp)

        assert out.urgency_tier == "critical", f"Expected critical tier, got {out.urgency_tier}"
        assert out.recommended_channel == "whatsapp", (
            f"Critical urgency MUST force whatsapp, but got {out.recommended_channel} for input channel {ch_code}"
        )
        assert out.consequence_severity == "credit_score_risk"
        assert 0.0 <= out.payment_probability <= 1.0
    print("  PASS: Critical urgency (credit_score_risk) strictly forces WhatsApp across all initial channels.")


def test_elevated_urgency_forces_sms(model: DunningModel):
    """Investment/Policy lapse risk MUST override channel to SMS minimum."""
    elevated_causes = ["investment_lapse_risk", "policy_lapse_risk"]

    for cause in elevated_causes:
        for ch_code in [0, 1, 2]:
            inp = DunningInput(
                channel_encoded=ch_code,
                time_since_failure_mins=30,
                customer_tenure_months=6,
                prior_payment_success_rate=0.85,
                product_type="sip" if "investment" in cause else "insurance_premium",
                consequence_severity=cause,
            )
            out = model.predict(inp)

            assert out.urgency_tier == "elevated", f"Expected elevated tier, got {out.urgency_tier}"
            assert out.recommended_channel == "sms", (
                f"Elevated urgency MUST force sms, but got {out.recommended_channel}"
            )
            assert out.consequence_severity == cause
            assert 0.0 <= out.payment_probability <= 1.0
    print("  PASS: Elevated urgency (investment & policy lapse) strictly forces SMS across all initial channels.")


def test_dunning_model_missing_error():
    """Verify error raised when model not loaded."""
    model = DunningModel("/nonexistent/path")
    inp = DunningInput(
        channel_encoded=0,
        time_since_failure_mins=10,
        customer_tenure_months=12,
        prior_payment_success_rate=0.8,
    )
    try:
        model.predict(inp)
        assert False, "Expected ValueError when model is not loaded"
    except ValueError as e:
        assert "not loaded" in str(e)
    print("  PASS: Model raises ValueError when uninitialized.")


def run_all_tests():
    print("=" * 70)
    print("TEST SUITE: NACH DUNNING URGENCY TIERS & CHANNEL ROUTING")
    print("=" * 70)

    test_dunning_static_mappings()
    model = test_dunning_model_loaded()
    test_standard_urgency_uses_ml_channel(model)
    test_critical_urgency_forces_whatsapp(model)
    test_elevated_urgency_forces_sms(model)
    test_dunning_model_missing_error()

    print("=" * 70)
    print("ALL DUNNING NACH UNIT TESTS PASSED (6/6)")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
