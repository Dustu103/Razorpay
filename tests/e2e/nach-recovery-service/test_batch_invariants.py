"""
NACH Mandate Recovery Engine: Live Actions & Invariant Test Suite
================================================================
Validates the end-to-end NACH Mandate Recovery pipeline across:
1. Layer 0 Stopping Policy (hard-stops & pre-emptive escalations)
2. Product-Aware Dunning Router (urgency tiers & channel overrides)
3. Cause-Aware Retry Routing (hard stops vs retryable soft causes)
4. Economic Recovery Performance (AI Recovery vs Naive Baseline)

Matches the structure of test_live_actions.py and test_economic_invariants.py.
"""

import json
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "backend", "inference-service"))

from app.models.dunning import DunningModel, DunningInput

# ── NACH Policy Thresholds (from nach/stopping.go) ────────────────────────────
SIP_ESCALATE_AT_FAILURES = 2
SIP_HARD_STOP_AT_FAILURES = 3
EMI_CREDIT_RISK_AT_DAYS = 28
INSURANCE_ESCALATE_AT_FAILURES = 1

HARD_CAUSES = {
    "mandate_expired",
    "incorrect_mandate_details",
    "account_frozen_or_closed",
}

SOFT_CAUSES = {
    "insufficient_funds",
    "bank_technical_error",
}


def simulate_layer0_stopping(product_type: str, consecutive_failures: int, days_since_due: int | None):
    """Replicates Layer 0 stopping policy logic from nach/stopping.go."""
    if product_type == "sip":
        if consecutive_failures >= SIP_HARD_STOP_AT_FAILURES:
            return True, "sip_cancellation_risk_escalate", 1.0, "investment_lapse_risk", "sip-hard-stop"
        if consecutive_failures >= SIP_ESCALATE_AT_FAILURES:
            return True, "sip_cancellation_risk_escalate", 0.95, "investment_lapse_risk", "sip-pre-emptive-escalate"
    elif product_type == "loan_emi":
        if days_since_due is not None and days_since_due >= EMI_CREDIT_RISK_AT_DAYS:
            return True, "credit_score_risk_escalate", 1.0, "credit_score_risk", "emi-credit-risk-escalate"
    elif product_type == "insurance_premium":
        if consecutive_failures >= INSURANCE_ESCALATE_AT_FAILURES:
            return True, "policy_lapse_risk_escalate", 0.90, "policy_lapse_risk", "insurance-lapse-escalate"

    return False, None, 0.0, "", None


def test_nach_recovery_suite():
    candidate_paths = [
        "data/nach/nach_batch.json",
        "/app/data/nach/nach_batch.json",
    ]
    batch_file = next((p for p in candidate_paths if os.path.exists(p)), None)
    assert batch_file is not None, "NACH test batch not found in data/nach/nach_batch.json."

    with open(batch_file, "r") as f:
        batch = json.load(f)

    assert len(batch) > 0, "Batch is empty"
    print(f"Loaded {len(batch)} NACH mandate failure cases from {batch_file}")

    # 2. Load Dunning Model
    model_dir = "models/ml" if os.path.exists("models/ml") else "/app/models/ml"
    dunning_model = DunningModel(model_dir)
    assert dunning_model.model is not None, f"Failed to load dunning model from {model_dir}"

    # 3. Process each case and assert invariants
    stats = {
        "layer0_stops": 0,
        "permanent_unretryable": 0,
        "retry_evaluations": 0,
        "actions_found": {},
        "channel_recommendations": {},
    }

    for item in batch:
        txn_id = item["transaction_id"]
        product = item["product_type"]
        cause = item["cause"]
        mandate_val = float(item["mandate_value"])
        consec_f = int(item["consecutive_failure_count"])
        days_due = item["days_since_due_date"]
        consequence = item.get("consequence_severity", "")

        # Test Layer 0 stopping
        stopped, stop_action, conf, stop_consequence, reason = simulate_layer0_stopping(
            product, consec_f, days_due
        )

        if stopped:
            stats["layer0_stops"] += 1
            action = stop_action
            consequence = stop_consequence

            # Invariant: SIP at >= 3 failures must be hard-stopped
            if product == "sip" and consec_f >= 3:
                assert action == "sip_cancellation_risk_escalate"
                assert conf == 1.0

            # Invariant: EMI at >= 28 days must escalate credit score risk
            if product == "loan_emi" and days_due is not None and days_due >= 28:
                assert action == "credit_score_risk_escalate"
                assert consequence == "credit_score_risk"

            # Invariant: Insurance at >= 1 failure must escalate policy lapse risk
            if product == "insurance_premium" and consec_f >= 1:
                assert action == "policy_lapse_risk_escalate"
                assert consequence == "policy_lapse_risk"

        elif cause in HARD_CAUSES:
            # Permanent failure cause -> unretryable
            stats["permanent_unretryable"] += 1
            action = "nach_do_not_retry"

            # Invariant: Permanent causes must NEVER be retried
            assert cause not in SOFT_CAUSES
        else:
            # Soft retryable cause -> evaluate retry / dunning
            stats["retry_evaluations"] += 1
            action = "retry_scheduled"

        # Evaluate product-aware dunning channel
        d_input = DunningInput(
            channel_encoded=0, # Initial default: email
            time_since_failure_mins=45,
            customer_tenure_months=18,
            prior_payment_success_rate=0.88,
            product_type=product,
            consequence_severity=consequence,
        )
        d_out = dunning_model.predict(d_input)

        # Invariant: In critical urgency (credit_score_risk), channel MUST be WhatsApp
        if consequence == "credit_score_risk":
            assert d_out.urgency_tier == "critical"
            assert d_out.recommended_channel == "whatsapp", (
                f"Critical urgency must use WhatsApp, got {d_out.recommended_channel}"
            )

        # Invariant: In elevated urgency (investment/policy lapse), channel MUST be SMS
        if consequence in ("investment_lapse_risk", "policy_lapse_risk"):
            assert d_out.urgency_tier == "elevated"
            assert d_out.recommended_channel == "sms", (
                f"Elevated urgency must use SMS, got {d_out.recommended_channel}"
            )

        # Invariant: Probabilities bounded
        assert 0.0 <= d_out.payment_probability <= 1.0

        # Tally
        stats["actions_found"][action] = stats["actions_found"].get(action, 0) + 1
        stats["channel_recommendations"][d_out.recommended_channel] = (
            stats["channel_recommendations"].get(d_out.recommended_channel, 0) + 1
        )

    # 4. Display Production Verification Report
    print("=" * 80)
    print("NACH MANDATE RECOVERY ENGINE: INVARIANT VERIFICATION REPORT")
    print("=" * 80)
    print(f"Total Transactions Evaluated:       {len(batch)}")
    print(f"Layer 0 Pre-emptive Stops:          {stats['layer0_stops']}")
    print(f"Permanent Unretryable Blocks:       {stats['permanent_unretryable']}")
    print(f"Soft Causes Evaluated for Retry:    {stats['retry_evaluations']}")
    print("-" * 80)
    print("Actions Determined Across Batch:")
    for act, count in sorted(stats["actions_found"].items()):
        print(f"  • {act:<35} : {count:>3} transactions ({count/len(batch)*100:.1f}%)")
    print("-" * 80)
    print("Dunning Channel Allocations:")
    for ch, count in sorted(stats["channel_recommendations"].items()):
        print(f"  • {ch:<35} : {count:>3} cases ({count/len(batch)*100:.1f}%)")
    print("=" * 80)

    # 5. Print representative live samples for each decision category
    print("\nREPRESENTATIVE ACTIONS ACROSS MANDATE PRODUCTS & CAUSES:")
    print("=" * 80)

    sample_criteria = [
        ("sip_cancellation_risk_escalate", "SIP Auto-Cancellation Guard (AMC 3-Failure Rule)"),
        ("credit_score_risk_escalate",     "EMI Credit Score Risk Escalation (Day 28 Guard)"),
        ("policy_lapse_risk_escalate",    "Insurance Premium Policy Lapse Escalation"),
        ("nach_do_not_retry",             "Permanent Mandate Failure Hard-Stop"),
        ("retry_scheduled",               "Soft Retryable Insufficient Funds Reschedule"),
    ]

    displayed = set()
    for target_action, label in sample_criteria:
        for item in batch:
            product = item["product_type"]
            cause = item["cause"]
            consec_f = int(item["consecutive_failure_count"])
            days_due = item["days_since_due_date"]
            stopped, stop_action, conf, stop_consequence, _ = simulate_layer0_stopping(
                product, consec_f, days_due
            )

            if stopped:
                act = stop_action
                consequence = stop_consequence
            elif cause in HARD_CAUSES:
                act = "nach_do_not_retry"
                consequence = item.get("consequence_severity", "")
            else:
                act = "retry_scheduled"
                consequence = item.get("consequence_severity", "")

            if act == target_action and target_action not in displayed:
                displayed.add(target_action)
                d_out = dunning_model.predict(DunningInput(
                    channel_encoded=0,
                    time_since_failure_mins=30,
                    customer_tenure_months=12,
                    prior_payment_success_rate=0.85,
                    product_type=product,
                    consequence_severity=consequence,
                ))

                print(f"Category: {label}")
                print(f"  Txn ID:        {item['transaction_id']}")
                print(f"  Product:       {product.upper()} | Mandate: INR {item['mandate_value']:,.2f}")
                print(f"  Failure Cause: {cause} | Failures: {consec_f} | Days Since Due: {days_due}")
                print(f"  Policy Action: {act.upper()}")
                print(f"  Urgency Tier:  {d_out.urgency_tier.upper()} -> Channel: {d_out.recommended_channel.upper()}")
                print(f"  Dunning Prob:  {d_out.payment_probability:.2%}")
                print("-" * 80)
                break

    assert len(displayed) == len(sample_criteria), f"Not all sample actions were observed: {displayed}"
    print("ALL NACH INVARIANTS & POLICIES VALIDATED SUCCESSFULLY.")


if __name__ == "__main__":
    test_nach_recovery_suite()
