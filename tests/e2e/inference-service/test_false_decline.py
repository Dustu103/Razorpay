import requests
import time

def test_false_decline_endpoint():
    url = "http://localhost:8000/predict/false-decline"
    
    print("="*60)
    print("Testing False Decline Endpoint (Feature D)")
    print("="*60)
    
    scenarios = [
        {
            "name": "Scenario 1: Highly Likely False Decline (Safe Customer)",
            "payload": {
                "amount": 150.0,
                "transaction_velocity": 1,
                "is_known_device": 1,
                "ip_risk_score": 0.05,
                "merchant_category": "retail",
                "transaction_hour": 14
            },
            "expected_action": "reverify_and_reverse"
        },
        {
            "name": "Scenario 2: Highly Likely Genuine Fraud (Risky Customer)",
            "payload": {
                "amount": 25000.0,
                "transaction_velocity": 8,
                "is_known_device": 0,
                "ip_risk_score": 0.95,
                "merchant_category": "gaming",
                "transaction_hour": 3
            },
            "expected_action": "uphold_block"
        },
        {
            "name": "Scenario 3: Borderline Case (High Amount, Known Device)",
            "payload": {
                "amount": 8000.0,
                "transaction_velocity": 2,
                "is_known_device": 1,
                "ip_risk_score": 0.2,
                "merchant_category": "electronics",
                "transaction_hour": 18
            },
            "expected_action": "reverify_and_reverse"
        }
    ]
    
    passed = 0
    total_time = 0
    
    for idx, scenario in enumerate(scenarios, 1):
        print(f"[{idx}] {scenario['name']}")
        start = time.time()
        
        try:
            response = requests.post(url, json=scenario["payload"], timeout=5)
            response.raise_for_status()
            data = response.json()
            latency = (time.time() - start) * 1000
            total_time += latency
            
            likelihood = data.get("false_decline_likelihood", 0)
            action = data.get("recommended_action", "")
            features = data.get("contributing_features", [])
            
            expected = scenario["expected_action"]
            
            if action == expected:
                print(f"  ✅ PASS")
                passed += 1
            else:
                print(f"  ❌ FAIL (Expected: {expected}, Got: {action})")
                
            print(f"     Likelihood: {likelihood:.2f}")
            print(f"     Action: {action}")
            print(f"     Features: {features}")
            print(f"     Latency: {latency:.2f} ms\n")
            
        except Exception as e:
            print(f"  ❌ FAIL (Error: {e})\n")
            
    print("="*60)
    print(f"Results: {passed}/{len(scenarios)} passed")
    print(f"Average Latency: {total_time/len(scenarios):.2f} ms")
    print("="*60)

if __name__ == "__main__":
    test_false_decline_endpoint()
