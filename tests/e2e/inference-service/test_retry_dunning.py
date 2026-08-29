import requests
import time

def test_features():
    print("="*60)
    print("Testing Feature B (Retry Routing)")
    print("="*60)
    
    retry_url = "http://localhost:8000/predict/retry"
    retry_payload = {
        "hour_of_day": 14,
        "day_of_month": 1,
        "failure_cause_encoded": 0,
        "payment_method_encoded": 2,
        "retry_count": 1,
        "time_since_failure_mins": 30
    }
    
    start = time.time()
    try:
        response = requests.post(retry_url, json=retry_payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        latency = (time.time() - start) * 1000
        
        print(f"  ✅ PASS")
        print(f"     Probability: {data.get('retry_success_probability'):.2f}")
        print(f"     Action: {data.get('recommended_action')}")
        print(f"     Latency: {latency:.2f} ms\n")
    except Exception as e:
        print(f"  ❌ FAIL (Error: {e})\n")
        
    print("="*60)
    print("Testing Feature C (Dunning Optimization)")
    print("="*60)
    
    dunning_url = "http://localhost:8000/predict/dunning"
    dunning_payload = {
        "channel_encoded": 0,
        "time_since_failure_mins": 10,
        "customer_tenure_months": 24,
        "prior_payment_success_rate": 0.95
    }
    
    start = time.time()
    try:
        response = requests.post(dunning_url, json=dunning_payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        latency = (time.time() - start) * 1000
        
        print(f"  ✅ PASS")
        print(f"     Probability: {data.get('payment_probability'):.2f}")
        print(f"     Channel: {data.get('recommended_channel')}")
        print(f"     Latency: {latency:.2f} ms\n")
    except Exception as e:
        print(f"  ❌ FAIL (Error: {e})\n")

if __name__ == "__main__":
    test_features()
