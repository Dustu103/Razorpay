import requests
import json
import time

URL = "http://razorpay-chargeback:3005/api/v1/analyze-dispute"

test_cases = [
    {"id": "1.1", "payload": {"reason_code": "visa_10.4", "network": "visa", "has_3ds_auth": 1, "has_delivery_proof": 1, "days_remaining": 14, "transaction_amount_inr": 4500, "merchant_current_dispute_ratio": 0.0162}, "expected": "deflect_via_refund"},
    {"id": "1.2", "payload": {"reason_code": "visa_10.4", "network": "visa", "has_3ds_auth": 1, "has_delivery_proof": 0, "days_remaining": 10, "transaction_amount_inr": 2500, "merchant_current_dispute_ratio": 0.0080}, "expected": "auto_submit"},
    {"id": "1.3", "payload": {"reason_code": "visa_10.4", "network": "visa", "has_3ds_auth": 0, "has_delivery_proof": 1, "has_avs_cvv_match": 0, "has_ip_device_fingerprint": 0, "days_remaining": 10, "transaction_amount_inr": 15000, "merchant_current_dispute_ratio": 0.0110}, "expected": "deflect_via_refund"},
    {"id": "1.4", "payload": {"reason_code": "mc_4853", "network": "mastercard", "has_3ds_auth": 1, "has_delivery_proof": 0, "days_remaining": 9, "transaction_amount_inr": 3000, "merchant_current_dispute_ratio": 0.0050}, "expected": "deflect_via_refund"},
    {"id": "1.5", "payload": {"reason_code": "mc_4853", "network": "mastercard", "has_3ds_auth": 0, "has_delivery_proof": 1, "days_remaining": 12, "transaction_amount_inr": 8000, "merchant_current_dispute_ratio": 0.0040}, "expected": "auto_submit"},
    {"id": "1.6", "payload": {"reason_code": "rupay_1065", "network": "rupay", "has_3ds_auth": 1, "has_delivery_proof": 1, "days_remaining": 1, "transaction_amount_inr": 1200, "merchant_current_dispute_ratio": 0.0090}, "expected": "deflect_via_refund"},
    {"id": "1.7", "payload": {"reason_code": "visa_13.1", "network": "visa", "has_3ds_auth": 1, "has_delivery_proof": 1, "days_remaining": 14, "transaction_amount_inr": 450000, "merchant_current_dispute_ratio": 0.0060}, "expected": "review"},
    {"id": "1.8", "payload": {"reason_code": "mc_4837", "network": "mastercard", "has_3ds_auth": 0, "has_delivery_proof": 0, "days_remaining": 5, "transaction_amount_inr": 500, "merchant_current_dispute_ratio": 0.0148}, "expected": "deflect_via_refund"},
    {"id": "1.9", "payload": {"reason_code": "visa_10.4", "network": "visa", "has_3ds_auth": 1, "has_delivery_proof": 1, "days_remaining": 21, "transaction_amount_inr": 500, "merchant_current_dispute_ratio": 0.0020}, "expected": "auto_submit"},
    {"id": "1.10", "payload": {"reason_code": "rupay_1062", "network": "rupay", "has_3ds_auth": 0, "has_delivery_proof": 1, "has_prior_comms": 1, "days_remaining": 10, "transaction_amount_inr": 6000, "merchant_current_dispute_ratio": 0.0030}, "expected": "review"},
    {"id": "1.11", "payload": {"reason_code": "visa_13.3", "network": "visa", "has_3ds_auth": 1, "has_delivery_proof": 1, "days_remaining": 12, "transaction_amount_inr": 8000, "merchant_current_dispute_ratio": 0.0145}, "expected": "deflect_via_refund"},
    {"id": "1.12", "payload": {"reason_code": "mc_4808", "network": "mastercard", "has_3ds_auth": 1, "has_delivery_proof": 1, "days_remaining": 10, "transaction_amount_inr": 4000, "merchant_current_dispute_ratio": 0.0010}, "expected": "deflect_via_refund"},
    {"id": "1.13", "payload": {"reason_code": "visa_10.4", "network": "visa", "has_3ds_auth": 0, "has_delivery_proof": 0, "days_remaining": 14, "transaction_amount_inr": 9000, "merchant_current_dispute_ratio": 0.0120}, "expected": "deflect_via_refund"},
    {"id": "1.14", "payload": {"reason_code": "mc_4853", "network": "mastercard", "has_3ds_auth": 0, "has_delivery_proof": 1, "days_remaining": 2, "transaction_amount_inr": 22000, "merchant_current_dispute_ratio": 0.0070}, "expected": "deflect_via_refund"},
    {"id": "1.15", "payload": {"reason_code": "visa_10.4", "network": "visa", "has_3ds_auth": 1, "has_delivery_proof": 1, "days_remaining": 12, "transaction_amount_inr": 2000, "merchant_current_dispute_ratio": 0.0095}, "expected": "auto_submit"}
]

passed = 0
failed = 0

print("="*60)
print("CHARGEBACK PRE-EMPTION ACCURACY TEST")
print("="*60)

for tc in test_cases:
    # Set default values for omitted fields
    payload = tc["payload"]
    payload.setdefault("has_avs_cvv_match", 1)
    payload.setdefault("has_ip_device_fingerprint", 1)
    payload.setdefault("has_prior_comms", 0)
    payload.setdefault("days_since_transaction", 5)
    payload.setdefault("repeat_dispute_count", 0)
    payload.setdefault("merchant_category", "ecommerce")

    try:
        response = requests.post(URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            actual = data.get("recommended_action")
            expected = tc["expected"]
            
            # Map auto_submit to FIGHT, deflect_via_refund to DEFLECT, review to FLAG FOR REVIEW
            display_actual = "FIGHT" if actual == "auto_submit" else "DEFLECT" if actual == "deflect_via_refund" else "FLAG FOR REVIEW"
            display_expected = "FIGHT" if expected == "auto_submit" else "DEFLECT" if expected == "deflect_via_refund" else "FLAG FOR REVIEW"
            
            if actual == expected:
                print(f"✅ Case {tc['id']}: Expected {display_expected} -> Got {display_actual} (Win Prob: {data.get('win_probability', 'N/A')})")
                passed += 1
            else:
                print(f"❌ Case {tc['id']}: Expected {display_expected} -> Got {display_actual} (Win Prob: {data.get('win_probability', 'N/A')})")
                failed += 1
        else:
            print(f"❌ Case {tc['id']}: HTTP {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"❌ Case {tc['id']}: Failed with exception {str(e)}")
        failed += 1

print("="*60)
print(f"Total: {len(test_cases)} | Passed: {passed} | Failed: {failed}")
print(f"Accuracy: {(passed/len(test_cases))*100:.2f}%")
print("="*60)
