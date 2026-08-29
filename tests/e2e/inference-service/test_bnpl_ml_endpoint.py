import requests
import json
import math
import time

BASE_URL = "http://localhost:8000"
DECAY_LAMBDA = 0.023

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check(condition, pass_msg, fail_msg):
    if condition:
        print(f"  ✅ {pass_msg}")
    else:
        print(f"  ❌ {fail_msg}")
    return condition

def test_edge_checkout():
    section("Engine 1: Real-Time Checkout Edge Model")

    # Test 1a: High amount + insufficient funds → should offer BNPL
    payload = {"amount": 6000.0, "decline_reason_encoded": 0, "tenure_months": 36}
    resp = requests.post(f"{BASE_URL}/predict/checkout-offer", json=payload).json()
    print(f"\n  Test 1a — High value Insufficient Funds:")
    print(f"  Payload: {payload}")
    print(f"  Result:  {resp}")
    check(resp["show_bnpl_offer"] == True,
          "Correctly offered BNPL (conversion prob: {:.2%})".format(resp["conversion_probability"]),
          "Failed to offer BNPL on high-value Insufficient Funds")

    # Test 1b: Technical decline on small amount → should NOT offer BNPL
    payload = {"amount": 150.0, "decline_reason_encoded": 3, "tenure_months": 2}
    resp = requests.post(f"{BASE_URL}/predict/checkout-offer", json=payload).json()
    print(f"\n  Test 1b — Low value Technical decline:")
    print(f"  Payload: {payload}")
    print(f"  Result:  {resp}")
    check(resp["show_bnpl_offer"] == False,
          "Correctly suppressed BNPL offer for technical decline",
          "Incorrectly offered BNPL on small technical decline")

def test_recovery_phantom_debt():
    section("Engine 2: Phantom Debt Signal (Fresh Consent)")

    # Gen Z, massive phantom debt, fresh data → should SMS
    payload = {
        "internal_debt": 500.0,
        "external_ecosystem_debt": 12000.0,
        "days_since_login": 5,
        "demographic_age": 22,
        "consent_revoked": False,
        "external_debt_data_age_days": 2
    }
    resp = requests.post(f"{BASE_URL}/predict/bnpl-recovery", json=payload).json()

    expected_eff = round(12000.0 * math.exp(-DECAY_LAMBDA * 2), 2)
    print(f"\n  Payload: {payload}")
    print(f"  Result:  {resp}")
    print(f"  Expected effective_external_debt ≈ {expected_eff:.2f}")
    check(resp["recommended_channel"] == "sms",
          f"Correctly routed Gen Z phantom-debt borrower to SMS",
          f"Incorrect channel: {resp['recommended_channel']}")
    check(abs(resp["effective_external_debt_used"] - expected_eff) < 50,
          f"Decay math correct (got {resp['effective_external_debt_used']:.2f})",
          f"Decay math wrong (got {resp['effective_external_debt_used']:.2f}, expected ≈ {expected_eff:.2f})")

def test_recovery_consent_revoked_stale():
    section("Engine 2: DPDP Consent Gate (Revoked + Stale Data)")

    # Consent revoked + 60-day stale data → external debt should be zeroed
    # With no phantom debt signal, model should fall back to Email
    payload = {
        "internal_debt": 800.0,
        "external_ecosystem_debt": 15000.0,  # Large but STALE + REVOKED
        "days_since_login": 10,
        "demographic_age": 35,
        "consent_revoked": True,
        "external_debt_data_age_days": 60   # Stale > 30 day threshold
    }
    resp = requests.post(f"{BASE_URL}/predict/bnpl-recovery", json=payload).json()
    print(f"\n  Payload: {payload}")
    print(f"  Result:  {resp}")
    check(resp["effective_external_debt_used"] == 0.0,
          "Consent gate correctly zeroed out stale phantom debt signal",
          f"DPDP VIOLATION: Stale debt signal not zeroed (got {resp['effective_external_debt_used']})")

def test_recovery_consent_revoked_fresh():
    section("Engine 2: Consent Revoked But Data Fresh (<= 30 days)")

    # Consent revoked but data is only 15 days old → decay applies, NOT zeroed
    payload = {
        "internal_debt": 500.0,
        "external_ecosystem_debt": 10000.0,
        "days_since_login": 5,
        "demographic_age": 25,
        "consent_revoked": True,
        "external_debt_data_age_days": 15  # Fresh enough → use with decay
    }
    resp = requests.post(f"{BASE_URL}/predict/bnpl-recovery", json=payload).json()
    expected_eff = round(10000.0 * math.exp(-DECAY_LAMBDA * 15), 2)
    print(f"\n  Payload: {payload}")
    print(f"  Result:  {resp}")
    print(f"  Expected effective_external_debt ≈ {expected_eff:.2f}")
    check(resp["effective_external_debt_used"] > 0.0,
          f"Correctly used decayed signal for fresh revoked data ({resp['effective_external_debt_used']:.2f})",
          "Incorrectly zeroed fresh data")

if __name__ == "__main__":
    print("BNPL Dual-Engine E2E Validation Suite")
    print(f"Target: {BASE_URL}\n")

    time.sleep(2)  # Allow service to be ready
    test_edge_checkout()
    test_recovery_phantom_debt()
    test_recovery_consent_revoked_stale()
    test_recovery_consent_revoked_fresh()
    print(f"\n{'='*60}")
    print("  Suite Complete")
    print(f"{'='*60}\n")
