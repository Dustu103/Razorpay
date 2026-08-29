import requests
import json
import time

URL = "http://razorpay-compliance:3004/api/v1/scan-compliance"

test_cases = [
    # ── Layer 1 Deterministic Tests ──────────────────────────────────────────
    {
        "id": "2.1", "expected_violations": 1, "expected_severity": "High", "rule": "Pre-checked Consent",
        "payload": {"flow": [{"screen_name": "Checkout", "elements": [{"id": "chk_1", "type": "checkbox", "state": "pre-checked", "text": "I agree to Terms"}]}]}
    },
    {
        "id": "2.2", "expected_violations": 1, "expected_severity": "Medium", "rule": "False Urgency",
        "payload": {"flow": [{"screen_name": "Payment", "elements": [{"id": "btn_1", "type": "button", "state": "active", "text": "Hurry, only 2 left! Pay Now"}]}]}
    },
    {
        "id": "2.3", "expected_violations": 2, "expected_severity": "High", "rule": "Hidden Cancellation Path",
        "payload": {"flow": [{"screen_name": "Settings", "elements": [{"id": "btn_cancel", "type": "button", "state": "hidden", "text": "Cancel Subscription"}]}]}
    },
    {
        "id": "2.4", "expected_violations": 1, "expected_severity": "High", "rule": "Missing Cancellation Path",
        "payload": {"flow": [{"screen_name": "Mandate Confirmation", "elements": [{"id": "lbl_1", "type": "label", "text": "Subscribe to monthly plan"}, {"id": "btn_pay", "type": "button", "text": "Proceed"}]}]}
    },
    {
        "id": "2.5", "expected_violations": 0, "expected_severity": None, "rule": "Clean Subscription",
        "payload": {"flow": [{"screen_name": "Mandate Confirmation", "elements": [{"id": "lbl_1", "type": "label", "text": "Subscribe to monthly plan"}, {"id": "chk_terms", "type": "checkbox", "state": "unchecked", "text": "I agree to Terms & Conditions"}, {"id": "btn_cancel", "type": "button", "text": "Cancel"}]}]}
    },
    {
        "id": "2.6", "expected_violations": 1, "expected_severity": "Medium", "rule": "False Urgency",
        "payload": {"flow": [{"screen_name": "Offer Page", "elements": [{"id": "lbl_timer", "type": "label", "text": "Offer expires in 05:00 minutes!"}]}]}
    },

    # ── Layer 2 LLM Semantic Tests ──────────────────────────────────────────
    {
        "id": "2.7", "expected_violations": 1, "expected_severity": "Medium", "rule": "Forced Product Bundling",
        "payload": {"flow": [{"screen_name": "Cart", "elements": [{"id": "cart_item_1", "type": "row", "text": "Flight Ticket - ₹4000"}, {"id": "cart_item_2", "type": "row", "text": "Travel Insurance - ₹399 (Auto-added, non-removable)"}]}]}
    },
    {
        "id": "2.8", "expected_violations": 1, "expected_severity": "Medium", "rule": "Obscured Terms & Conditions",
        "payload": {"flow": [{"screen_name": "Signup", "elements": [{"id": "lbl_terms", "type": "label", "text": "By continuing you agree to the T&C. (Note: The font is 6px and color is light grey on white background)"}]}]}
    },
    {
        "id": "2.9", "expected_violations": 1, "expected_severity": "Low", "rule": "Interface Pressure",
        "payload": {"flow": [{"screen_name": "Upsell", "elements": [{"id": "btn_yes", "type": "button", "text": "Yes, I want to save money!"}, {"id": "btn_no", "type": "button", "text": "No thanks, I prefer to lose money"}]}]}
    },
    {
        "id": "2.10", "expected_violations": 1, "expected_severity": "Low", "rule": "Interface Pressure",
        "payload": {"flow": [{"screen_name": "Plan Selection", "elements": [{"id": "btn_premium", "type": "button", "text": "Go Premium (Giant green button with pulsing animation)"}, {"id": "btn_free", "type": "label", "text": "continue with free tier (tiny grey text, doesn't look clickable)"}]}]}
    },
    {
        "id": "2.11", "expected_violations": 1, "expected_severity": "Medium", "rule": "Obscured Terms & Conditions",
        "payload": {"flow": [{"screen_name": "Checkout", "elements": [{"id": "btn_pay", "type": "button", "text": "Pay Now"}, {"id": "icon_q", "type": "icon", "text": "Hover over this tiny question mark to read the mandatory terms"}]}]}
    },

    # ── Edge Cases & False Positives ────────────────────────────────────────
    {
        "id": "2.12", "expected_violations": 2, "expected_severity": "Mixed", "rule": "Double Violation (L1 + L2)",
        "payload": {"flow": [{"screen_name": "Combo", "elements": [{"id": "chk", "type": "checkbox", "state": "pre-checked", "text": "Accept Terms"}, {"id": "btn_no", "type": "button", "text": "No, I hate good deals"}]}]}
    },
    {
        "id": "2.13", "expected_violations": 0, "expected_severity": None, "rule": "Valid Urgency (False Positive)",
        "payload": {"flow": [{"screen_name": "Billing Info", "elements": [{"id": "lbl_billing", "type": "label", "text": "Your next billing date is tomorrow."}]}]}
    },
    {
        "id": "2.14", "expected_violations": 0, "expected_severity": None, "rule": "Valid Cross-sell (False Positive)",
        "payload": {"flow": [{"screen_name": "Upsell", "elements": [{"id": "lbl_offer", "type": "label", "text": "Want to add premium features?"}, {"id": "btn_yes", "type": "button", "text": "Yes, upgrade me"}, {"id": "btn_no", "type": "button", "text": "No thanks, keep current plan"}]}]}
    },
    {
        "id": "2.15", "expected_violations": 1, "expected_severity": "High", "rule": "Missing Cancellation Path (Multi-screen)",
        "payload": {"flow": [
            {"screen_name": "Screen 1", "elements": [{"id": "btn", "type": "button", "text": "Next"}]},
            {"screen_name": "Screen 2", "elements": [{"id": "lbl", "type": "label", "text": "Terms"}, {"id": "btn_cancel", "type": "button", "text": "Cancel"}]},
            {"screen_name": "Screen 3", "elements": [{"id": "lbl", "type": "label", "text": "Final Confirmation for Subscription"}, {"id": "btn_pay", "type": "button", "text": "Pay"}]}
        ]}
    },
]

print("="*80)
print("COMPLIANCE SCANNER ACCURACY TEST")
print("="*80)

passed = 0
failed = 0

for tc in test_cases:
    # Add delay to prevent LLM API rate limits on free tiers
    time.sleep(3)
    try:
        start_time = time.time()
        resp = requests.post(URL, json=tc["payload"], timeout=20)
        resp.raise_for_status()
        data = resp.json()
        latency = time.time() - start_time
        
        violations = data.get("violations", [])
        num_violations = len(violations)
        
        is_pass = False
        if num_violations == tc["expected_violations"]:
            if num_violations == 0:
                is_pass = True
            else:
                # Check if the expected rule was flagged
                # For L2, LLM might phrase it slightly differently, so we check broadly
                # We expect at least one violation to match the expected severity or rule domain
                found_match = False
                for v in violations:
                    if tc["expected_severity"] == "Mixed" or v.get("severity") == tc["expected_severity"] or tc["rule"].split()[0] in v.get("rule_broken", ""):
                        found_match = True
                        break
                is_pass = found_match

        if is_pass:
            print(f"✅ Case {tc['id']} | Pass ({latency:.2f}s) | Found {num_violations} violations")
            passed += 1
        else:
            print(f"❌ Case {tc['id']} | Fail ({latency:.2f}s) | Expected {tc['expected_violations']} '{tc['rule']}', got {num_violations}")
            if num_violations > 0:
                for v in violations:
                    print(f"   -> Detected: {v.get('rule_broken')} ({v.get('severity')}) via {v.get('detected_by')}")
            failed += 1

    except Exception as e:
        print(f"❌ Case {tc['id']} | Error: {str(e)}")
        failed += 1

print("="*80)
print(f"Total: {len(test_cases)} | Passed: {passed} | Failed: {failed}")
print(f"Accuracy: {(passed/len(test_cases))*100:.2f}%")
print("="*80)
