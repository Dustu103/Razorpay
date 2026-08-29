import requests
import json
import sys
import time
import os

API_URL = os.getenv("API_URL", "http://localhost:3005/api/v1/analyze-dispute")

SCENARIOS = [
    {
        "name": "1. MC 4837 (Fraud) - Strong Evidence, High Value",
        "payload": {
            "reason_code": "mc_4837", "network": "mastercard",
            "has_3ds_auth": 1, "has_ip_device_fingerprint": 0, "has_avs_cvv_match": 1,
            "days_remaining": 10, "days_since_transaction": 20,
            "repeat_dispute_count": 0, "transaction_amount_inr": 90000.0,
            "merchant_category": "ecommerce", "merchant_current_dispute_ratio": 0.001
        }
    },
    {
        "name": "2. MC 4837 (Fraud) - Zero Evidence, Low Value (Should Deflect)",
        "payload": {
            "reason_code": "mc_4837", "network": "mastercard",
            "has_3ds_auth": 0, "has_ip_device_fingerprint": 0, "has_avs_cvv_match": 0,
            "days_remaining": 14, "days_since_transaction": 40,
            "repeat_dispute_count": 0, "transaction_amount_inr": 500.0,
            "merchant_category": "retail", "merchant_current_dispute_ratio": 0.002
        }
    },
    {
        "name": "3. Visa 13.1 (Not Received) - Strong Evidence but 1 Day Left (Should Deflect due to deadline)",
        "payload": {
            "reason_code": "visa_13.1", "network": "visa",
            "has_delivery_proof": 1,
            "days_remaining": 1, "days_since_transaction": 30,
            "repeat_dispute_count": 0, "transaction_amount_inr": 8000.0,
            "merchant_category": "saas", "merchant_current_dispute_ratio": 0.003
        }
    },
    {
        "name": "4. Visa 13.3 (Defective) - Good Evidence, Mid Value",
        "payload": {
            "reason_code": "visa_13.3", "network": "visa",
            "has_prior_comms": 1, "has_usage_logs": 1,
            "days_remaining": 12, "days_since_transaction": 15,
            "repeat_dispute_count": 0, "transaction_amount_inr": 50000.0,
            "merchant_category": "digital_goods", "merchant_current_dispute_ratio": 0.004
        }
    },
    {
        "name": "5. RuPay 1065 (General) - Chronic Friendly Fraud (Repeat=10)",
        "payload": {
            "reason_code": "rupay_1065", "network": "rupay",
            "days_remaining": 8, "days_since_transaction": 10,
            "repeat_dispute_count": 10, "transaction_amount_inr": 2500.0,
            "merchant_category": "ecommerce", "merchant_current_dispute_ratio": 0.005
        }
    },
    {
        "name": "6. RuPay 1085 (Overcharge) - Massive Amount, Zero Evidence",
        "payload": {
            "reason_code": "rupay_1085", "network": "rupay",
            "days_remaining": 14, "days_since_transaction": 5,
            "repeat_dispute_count": 0, "transaction_amount_inr": 200000.0,
            "merchant_category": "travel", "merchant_current_dispute_ratio": 0.002
        }
    },
    {
        "name": "7. RuPay RU03 (Duplicate) - Normal Case",
        "payload": {
            "reason_code": "rupay_ru03", "network": "rupay",
            "days_remaining": 10, "days_since_transaction": 3,
            "repeat_dispute_count": 1, "transaction_amount_inr": 1500.0,
            "merchant_category": "saas", "merchant_current_dispute_ratio": 0.001
        }
    },
    {
        "name": "8. MC 4808 (Auth Failure) - With Delivery Proof (Still Unwinnable)",
        "payload": {
            "reason_code": "mc_4808", "network": "mastercard",
            "has_delivery_proof": 1,
            "days_remaining": 14, "days_since_transaction": 60,
            "repeat_dispute_count": 0, "transaction_amount_inr": 6000.0,
            "merchant_category": "retail", "merchant_current_dispute_ratio": 0.003
        }
    },
    {
        "name": "9. Visa 10.4 (Fraud) - Missing 3DS but has IP & CVV",
        "payload": {
            "reason_code": "visa_10.4", "network": "visa",
            "has_3ds_auth": 0, "has_ip_device_fingerprint": 1, "has_avs_cvv_match": 1,
            "days_remaining": 11, "days_since_transaction": 22,
            "repeat_dispute_count": 0, "transaction_amount_inr": 12000.0,
            "merchant_category": "ecommerce", "merchant_current_dispute_ratio": 0.002
        }
    },
    {
        "name": "10. MC 4853 (Not Provided) - Zero Evidence (Auto Refund)",
        "payload": {
            "reason_code": "mc_4853", "network": "mastercard",
            "has_usage_logs": 0, "has_delivery_proof": 0, "has_prior_comms": 0,
            "days_remaining": 12, "days_since_transaction": 45,
            "repeat_dispute_count": 0, "transaction_amount_inr": 3500.0,
            "merchant_category": "digital_goods", "merchant_current_dispute_ratio": 0.001
        }
    },
    {
        "name": "11. Visa 13.1 (Not Received) - Dangerously High Merchant Ratio (0.02)",
        "payload": {
            "reason_code": "visa_13.1", "network": "visa",
            "has_delivery_proof": 1,
            "days_remaining": 14, "days_since_transaction": 10,
            "repeat_dispute_count": 0, "transaction_amount_inr": 4000.0,
            "merchant_category": "retail", "merchant_current_dispute_ratio": 0.020
        }
    },
    {
        "name": "12. Visa 13.3 (Defective) - Missing Comms, Low Value",
        "payload": {
            "reason_code": "visa_13.3", "network": "visa",
            "has_prior_comms": 0,
            "days_remaining": 13, "days_since_transaction": 8,
            "repeat_dispute_count": 0, "transaction_amount_inr": 4000.0,
            "merchant_category": "ecommerce", "merchant_current_dispute_ratio": 0.002
        }
    },
    {
        "name": "13. MC 4837 (Fraud) - Perfect Evidence but 1 Day Left",
        "payload": {
            "reason_code": "mc_4837", "network": "mastercard",
            "has_3ds_auth": 1, "has_ip_device_fingerprint": 1, "has_avs_cvv_match": 1,
            "days_remaining": 1, "days_since_transaction": 25,
            "repeat_dispute_count": 0, "transaction_amount_inr": 15000.0,
            "merchant_category": "saas", "merchant_current_dispute_ratio": 0.001
        }
    },
    {
        "name": "14. RuPay 1065 (General) - Micro Tx (₹200)",
        "payload": {
            "reason_code": "rupay_1065", "network": "rupay",
            "days_remaining": 14, "days_since_transaction": 2,
            "repeat_dispute_count": 0, "transaction_amount_inr": 200.0,
            "merchant_category": "retail", "merchant_current_dispute_ratio": 0.001
        }
    },
    {
        "name": "15. Visa 10.4 (Fraud) - Perfect Micro Tx",
        "payload": {
            "reason_code": "visa_10.4", "network": "visa",
            "has_3ds_auth": 1, "has_ip_device_fingerprint": 1, "has_avs_cvv_match": 1,
            "days_remaining": 14, "days_since_transaction": 5,
            "repeat_dispute_count": 0, "transaction_amount_inr": 300.0,
            "merchant_category": "saas", "merchant_current_dispute_ratio": 0.001
        }
    }
]

def run_tests():
    passed = 0
    failed = 0
    
    print("="*70)
    print("🚀 RUNNING E2E TESTS (V2) AGAINST CHARGEBACK SERVICE 🚀")
    print("="*70)

    for idx, test in enumerate(SCENARIOS):
        print(f"\n[{idx+1}/15] Scenario: {test['name']}")
        print(f"Payload: {json.dumps(test['payload'])}")

        try:
            resp = requests.post(API_URL, json=test['payload'], timeout=45)
            
            if resp.status_code != 200:
                print(f"❌ FAILED: Status code {resp.status_code}")
                print(f"Response: {resp.text}")
                failed += 1
                continue
                
            data = resp.json()
            rebuttal = data.get("rebuttal", {})
            
            # Print core routing outputs
            print(f"Ensemble Win Prob: {data.get('win_probability', 0)*100:.2f}%")
            print(f"Ensemble Std Dev:  {data.get('variance', 0):.4f}")
            print(f"Routing Path:      {data.get('routing_path')}")
            print(f"Recommended Action: {data.get('recommended_action')}")
            print(f"Redactions Count:   {rebuttal.get('hallucination_stats', {}).get('redacted_claims_count', 0)}")
            
            print("✅ PASSED")
            passed += 1

        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"RESULTS: {passed} PASSED | {failed} FAILED")
    print("="*70)
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
