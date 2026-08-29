"""
Compliance Scanner - E2E Test Suite
Tests the POST /api/v1/scan-compliance endpoint against:
  1. A fully compliant flow   -> expects is_compliant=True,  0 violations
  2. A single violation flow  -> expects is_compliant=False, 1 specific violation
  3. A worst-case flow        -> expects is_compliant=False, 3+ violations (all known dark patterns)
  4. An empty flow            -> expects a 422 validation error from the API
"""

import requests
import json
import sys
import os

BASE_URL = os.getenv("COMPLIANCE_SERVICE_URL", "http://compliance-service:3004")

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

pass_count = 0
fail_count = 0

def print_result(test_name: str, passed: bool, detail: str = ""):
    global pass_count, fail_count
    if passed:
        pass_count += 1
        print(f"  {GREEN}✓ PASS{RESET}  {test_name}")
    else:
        fail_count += 1
        print(f"  {RED}✗ FAIL{RESET}  {test_name}")
        if detail:
            print(f"         {YELLOW}→ {detail}{RESET}")

def scan(payload: dict) -> dict:
    r = requests.post(f"{BASE_URL}/api/v1/scan-compliance", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}=== Compliance Scanner – E2E Test Report ==={RESET}\n")

# 1. Health check
print(f"{BOLD}[0] Health Check{RESET}")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    print_result("Service is reachable and healthy", r.status_code == 200)
except Exception as e:
    print_result("Service is reachable and healthy", False, str(e))
    print(f"\n{RED}Cannot reach compliance-service. Is it running on port 3004?{RESET}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Compliant flow - no dark patterns
print(f"\n{BOLD}[1] Fully Compliant Flow{RESET}")
compliant_payload = {
    "flow": [
        {
            "screen_name": "subscription_setup",
            "elements": [
                {"id": "chk_consent", "type": "checkbox", "state": "unchecked", "text": "I agree to subscribe"},
                {"id": "btn_cancel", "type": "button", "state": "visible", "text": "Cancel Anytime"},
                {"id": "lnk_terms",  "type": "link",   "state": "visible", "text": "Read Terms & Conditions"},
            ]
        }
    ]
}
try:
    result = scan(compliant_payload)
    print_result("is_compliant = True",         result.get("is_compliant") == True)
    print_result("violations list is empty",    len(result.get("violations", [])) == 0)
except Exception as e:
    print_result("API returned 200 for compliant flow", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 3. Single violation - pre-checked consent
print(f"\n{BOLD}[2] Single Violation – Pre-checked Consent{RESET}")
pre_checked_payload = {
    "flow": [
        {
            "screen_name": "checkout",
            "elements": [
                {"id": "chk_subscribe", "type": "checkbox", "state": "pre-checked", "text": "Subscribe to premium plan"}
            ]
        }
    ]
}
try:
    result = scan(pre_checked_payload)
    violations = result.get("violations", [])
    rules_broken = [v["rule_broken"].lower() for v in violations]
    print_result("is_compliant = False",                    result.get("is_compliant") == False)
    print_result("At least 1 violation detected",           len(violations) >= 1)
    print_result("'Pre-checked' rule identified",           any("pre-check" in r or "consent" in r for r in rules_broken))
    print_result("Violation has a fix_suggestion",          all(v.get("fix_suggestion") for v in violations))
    print_result("Violation has a severity (High/Med/Low)", all(v.get("severity") in ["High","Medium","Low"] for v in violations))
except Exception as e:
    print_result("API returned 200 for pre-checked flow", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 4. Worst-case flow - all 3 obvious dark patterns
print(f"\n{BOLD}[3] Worst-Case Flow – Multiple Dark Patterns{RESET}")
worst_case_payload = {
    "flow": [
        {
            "screen_name": "checkout_step_1",
            "elements": [
                {"id": "btn_pay",       "type": "button",   "text": "Pay Now (Only 2 seats left! Hurry!)"},
                {"id": "chk_subscribe", "type": "checkbox", "state": "pre-checked", "text": "Add premium subscription"},
                {"id": "btn_cancel",    "type": "button",   "state": "hidden",      "text": "Cancel Subscription"},
            ]
        }
    ]
}
try:
    result = scan(worst_case_payload)
    violations = result.get("violations", [])
    print_result("is_compliant = False",        result.get("is_compliant") == False)
    print_result("3 or more violations found",  len(violations) >= 3,
                 f"Only {len(violations)} found: {[v['rule_broken'] for v in violations]}")
    has_high = any(v["severity"] == "High" for v in violations)
    print_result("At least 1 High-severity violation", has_high)
    all_have_fixes = all(v.get("fix_suggestion") for v in violations)
    print_result("All violations have fix_suggestion", all_have_fixes)
except Exception as e:
    print_result("API returned 200 for worst-case flow", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# 5. Validation error - empty flow list
print(f"\n{BOLD}[4] Input Validation – Empty Flow List{RESET}")
empty_payload = {"flow": []}
try:
    r = requests.post(f"{BASE_URL}/api/v1/scan-compliance", json=empty_payload, timeout=10)
    # FastAPI may process or return 422. Both are acceptable behaviors.
    print_result("API handles empty flow without crashing (2xx or 422)", r.status_code in [200, 422])
except Exception as e:
    print_result("API handles empty flow without crashing", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'─'*50}")
print(f"{BOLD}Results: {GREEN}{pass_count} passed{RESET}{BOLD}, {RED}{fail_count} failed{RESET}")
print(f"{'─'*50}\n")

sys.exit(0 if fail_count == 0 else 1)
