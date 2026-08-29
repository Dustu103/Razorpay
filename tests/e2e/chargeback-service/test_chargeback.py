"""
E2E Test Suite for Chargeback & Friendly-Fraud Pre-emption Service
===================================================================
Tests 15 predefined scenarios against the local FastAPI chargeback-service API (port 3005).
"""

import requests
import json
import sys
import time

import os
API_URL = os.getenv("API_URL", "http://localhost:3005/api/v1/analyze-dispute")

SCENARIOS = [
    # 1. Visa 10.4: Ideal fraud dispute with CE 3.0 (3DS, IP, AVS/CVV all present)
    {
        "name": "Visa 10.4 (Fraud) - CE 3.0 Qualified (Win expected)",
        "payload": {
            "reason_code": "visa_10.4", "network": "visa",
            "has_3ds_auth": 1, "has_ip_device_fingerprint": 1, "has_avs_cvv_match": 1,
            "days_remaining": 12, "days_since_transaction": 15,
            "repeat_dispute_count": 0, "transaction_amount_inr": 4500.0,
            "merchant_category": "saas", "merchant_current_dispute_ratio": 0.005
        },
        "expect_action": ["auto_submit", "one_tap_approval"]
    },
    # 2. Visa 10.4: Fraud dispute missing 3DS and CVV
    {
        "name": "Visa 10.4 (Fraud) - Weak evidence (Refund expected)",
        "payload": {
            "reason_code": "visa_10.4", "network": "visa",
            "has_3ds_auth": 0, "has_ip_device_fingerprint": 0, "has_avs_cvv_match": 0,
            "days_remaining": 10, "days_since_transaction": 45,
            "repeat_dispute_count": 0, "transaction_amount_inr": 3500.0,
            "merchant_category": "ecommerce", "merchant_current_dispute_ratio": 0.005
        },
        "expect_action": ["deflect_via_refund"]
    },
    # 3. MC 4808: Authorization failure (Unwinnable)
    {
        "name": "MC 4808 (Auth failure) - Unwinnable (Refund expected)",
        "payload": {
            "reason_code": "mc_4808", "network": "mastercard",
            "has_3ds_auth": 1, "has_delivery_proof": 1,
            "days_remaining": 8, "days_since_transaction": 60,
            "repeat_dispute_count": 0, "transaction_amount_inr": 9000.0,
            "merchant_category": "saas", "merchant_current_dispute_ratio": 0.004
        },
        "expect_action": ["auto_submit", "deflect_via_refund"]
    },
    # 4. Visa 13.1: Goods not received (Has tracking logs)
    {
        "name": "Visa 13.1 (Not Received) - Has delivery proof (Win expected)",
        "payload": {
            "reason_code": "visa_13.1", "network": "visa",
            "has_delivery_proof": 1,
            "days_remaining": 14, "days_since_transaction": 10,
            "repeat_dispute_count": 0, "transaction_amount_inr": 12000.0,
            "merchant_category": "retail", "merchant_current_dispute_ratio": 0.005
        },
        "expect_action": ["auto_submit", "one_tap_approval"]
    },
    # 5. Visa 13.1: Goods not received (No delivery proof)
    {
        "name": "Visa 13.1 (Not Received) - No delivery proof (Refund expected)",
        "payload": {
            "reason_code": "visa_13.1", "network": "visa",
            "has_delivery_proof": 0,
            "days_remaining": 11, "days_since_transaction": 10,
            "repeat_dispute_count": 0, "transaction_amount_inr": 1500.0,
            "merchant_category": "retail", "merchant_current_dispute_ratio": 0.005
        },
        "expect_action": ["deflect_via_refund"]
    },
    # 6. VAMP protection override: Borderline dispute + High merchant dispute ratio
    {
        "name": "Visa 13.1 - Borderline + High Merchant Ratio (Deflect override)",
        "payload": {
            "reason_code": "visa_13.1", "network": "visa",
            "has_delivery_proof": 1,
            "days_remaining": 10, "days_since_transaction": 20,
            "repeat_dispute_count": 0, "transaction_amount_inr": 5000.0,
            "merchant_category": "ecommerce", "merchant_current_dispute_ratio": 0.014  # High (VAMP threat)
        },
        "expect_action": ["deflect_via_refund"]
    },
    # 7. Repeat offender check (Friendly fraud indicator)
    {
        "name": "Visa 10.4 - Repeat Offender (Flagged / Reduced Probability)",
        "payload": {
            "reason_code": "visa_10.4", "network": "visa",
            "has_3ds_auth": 1, "has_ip_device_fingerprint": 1, "has_avs_cvv_match": 1,
            "days_remaining": 12, "days_since_transaction": 15,
            "repeat_dispute_count": 5, "transaction_amount_inr": 4500.0,
            "merchant_category": "saas", "merchant_current_dispute_ratio": 0.005
        },
        "expect_action": ["deflect_via_refund", "one_tap_approval", "await_merchant_approval", "review"]
    },
    # 8. T+5 days critical RuPay 1065 (Near deadline)
    {
        "name": "RuPay 1065 - Under 2 days remaining (Negative impact)",
        "payload": {
            "reason_code": "rupay_1065", "network": "rupay",
            "days_remaining": 2, "days_since_transaction": 4,
            "repeat_dispute_count": 0, "transaction_amount_inr": 2000.0,
            "merchant_category": "ecommerce", "merchant_current_dispute_ratio": 0.003
        },
        "expect_action": ["deflect_via_refund"]
    },
    # 9. RuPay 1085: Charged more than transaction amount (ledger proof needed)
    {
        "name": "RuPay 1085 - Overcharge (Ledger/Invoice implicit win)",
        "payload": {
            "reason_code": "rupay_1085", "network": "rupay",
            "days_remaining": 7, "days_since_transaction": 5,
            "repeat_dispute_count": 0, "transaction_amount_inr": 1500.0,
            "merchant_category": "ecommerce", "merchant_current_dispute_ratio": 0.003
        },
        "expect_action": ["auto_submit", "one_tap_approval"]
    },
    # 10. MC 4853: Cardholder dispute with tracking and communication
    {
        "name": "MC 4853 - Goods not provided (Strong evidence)",
        "payload": {
            "reason_code": "mc_4853", "network": "mastercard",
            "has_delivery_proof": 1, "has_usage_logs": 1, "has_prior_comms": 1,
            "days_remaining": 14, "days_since_transaction": 30,
            "repeat_dispute_count": 0, "transaction_amount_inr": 15000.0,
            "merchant_category": "travel", "merchant_current_dispute_ratio": 0.002
        },
        "expect_action": ["auto_submit", "one_tap_approval", "await_merchant_approval"]
    },
    # 11. Cost-aware routing: Low value simple case -> Single LLM (Groq) routing
    {
        "name": "RuPay RU03 - Duplicate Tx, Low value, Simple (Single LLM Routing)",
        "payload": {
            "reason_code": "rupay_ru03", "network": "rupay",
            "days_remaining": 7, "days_since_transaction": 3,
            "repeat_dispute_count": 0, "transaction_amount_inr": 1200.0,
            "merchant_category": "ecommerce", "merchant_current_dispute_ratio": 0.002
        },
        "expect_action": ["auto_submit", "one_tap_approval"]
    },
    # 12. Model disagreement simulation (High variance)
    {
        "name": "Visa 10.4 - Complex case with partial evidence (Disagreement expected)",
        "payload": {
            "reason_code": "visa_10.4", "network": "visa",
            "has_3ds_auth": 1, "has_ip_device_fingerprint": 0, "has_avs_cvv_match": 0,
            "days_remaining": 10, "days_since_transaction": 40,
            "repeat_dispute_count": 1, "transaction_amount_inr": 8000.0,
            "merchant_category": "ecommerce", "merchant_current_dispute_ratio": 0.005
        },
        "expect_action": ["await_merchant_approval", "review", "one_tap_approval"]
    },
    # 13. Visa 13.3: Defective goods (CS communication present)
    {
        "name": "Visa 13.3 - Defective (CS comms present)",
        "payload": {
            "reason_code": "visa_13.3", "network": "visa",
            "has_prior_comms": 1,
            "days_remaining": 14, "days_since_transaction": 12,
            "repeat_dispute_count": 0, "transaction_amount_inr": 20000.0,
            "merchant_category": "saas", "merchant_current_dispute_ratio": 0.002
        },
        "expect_action": ["auto_submit", "one_tap_approval"]
    },
    # 14. Visa 13.3: Defective goods (Missing CS communication)
    {
        "name": "Visa 13.3 - Defective (No CS comms, refund expected)",
        "payload": {
            "reason_code": "visa_13.3", "network": "visa",
            "has_prior_comms": 0,
            "days_remaining": 14, "days_since_transaction": 12,
            "repeat_dispute_count": 0, "transaction_amount_inr": 5000.0,
            "merchant_category": "saas", "merchant_current_dispute_ratio": 0.002
        },
        "expect_action": ["deflect_via_refund"]
    },
    # 15. Extreme high-value dispute (Scrutiny expected)
    {
        "name": "Visa 10.4 - Extreme High Value (₹1,50,000)",
        "payload": {
            "reason_code": "visa_10.4", "network": "visa",
            "has_3ds_auth": 1, "has_ip_device_fingerprint": 1, "has_avs_cvv_match": 1,
            "days_remaining": 14, "days_since_transaction": 2,
            "repeat_dispute_count": 0, "transaction_amount_inr": 150000.0,
            "merchant_category": "saas", "merchant_current_dispute_ratio": 0.001
        },
        "expect_action": ["auto_submit", "one_tap_approval", "await_merchant_approval"]
    }
]

def run_tests():
    passed = 0
    failed = 0

    print("=" * 70)
    print("RUNNING CHARGEBACK SERVICE E2E TEST SUITE (15 SCENARIOS)")
    print("=" * 70)

    for i, sc in enumerate(SCENARIOS, 1):
        print(f"\n[{i}/15] Scenario: {sc['name']}")
        print(f"Payload: {json.dumps(sc['payload'])}")
        
        try:
            resp = requests.post(API_URL, json=sc['payload'], timeout=20)
            if resp.status_code != 200:
                print(f"❌ FAILED: Status code {resp.status_code}")
                print(f"Response: {resp.text}")
                failed += 1
                continue
                
            res = resp.json()
            win_prob = res["win_probability"]
            action = res["recommended_action"]
            routing = res["routing_path"]
            redacted = res["redacted_artifacts"]
            
            print(f"Ensemble Win Prob: {win_prob:.2%}")
            print(f"Ensemble Std Dev:  {res['variance']:.4f}")
            print(f"Routing Path:      {routing}")
            print(f"Recommended Action: {action}")
            print(f"Redactions Count:   {len(redacted)}")
            
            # Check expected action
            if action in sc["expect_action"]:
                print("✅ PASSED")
                passed += 1
            else:
                print(f"❌ FAILED: Got action '{action}', expected one of {sc['expect_action']}")
                failed += 1
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} PASSED | {failed} FAILED")
    print("=" * 70)
    
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    # Wait a few seconds for server startup if executed sequentially
    time.sleep(2)
    run_tests()
