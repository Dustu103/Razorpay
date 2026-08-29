import requests
import random
import time
import math
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8000"
DECAY_LAMBDA = 0.023

def expected_edge_offer(amount, decline_reason_encoded, tenure_months):
    # Rule used in training:
    # High conversion if insufficient funds (0) and large amount (>1000)
    # Loyal customers (tenure > 12) also have a boost.
    if decline_reason_encoded == 0 and amount > 1000:
        return True
    if decline_reason_encoded == 0 and tenure_months > 12:
        return True
    if decline_reason_encoded == 1 and amount > 5000 and tenure_months > 24:
        return True
    return False

def expected_recovery_channel(internal_debt, raw_external_debt, days_since_login, age, consent_revoked, data_age):
    # Apply preprocessing rules
    if consent_revoked and data_age > 30:
        eff_debt = 0.0
    else:
        eff_debt = raw_external_debt * math.exp(-DECAY_LAMBDA * data_age)

    # Apply training rules
    if eff_debt > 8000 and age < 30:
        return "sms"
    elif (internal_debt + eff_debt) > 10000 and age > 50:
        return "voice"
    elif days_since_login > 30 and age > 40:
        return "email"
    elif eff_debt > 5000 and age < 40:
        return "sms"
    else:
        return "email"

def test_random_edge(n_samples=500):
    correct = 0
    total = 0
    
    for _ in range(n_samples):
        payload = {
            "amount": random.uniform(50.0, 15000.0),
            "decline_reason_encoded": random.choice([0, 1, 2, 3]),
            "tenure_months": random.randint(0, 48)
        }
        
        try:
            resp = requests.post(f"{BASE_URL}/predict/checkout-offer", json=payload).json()
            predicted = resp.get("show_bnpl_offer", False)
            expected = expected_edge_offer(payload["amount"], payload["decline_reason_encoded"], payload["tenure_months"])
            
            if predicted == expected:
                correct += 1
            total += 1
        except Exception:
            pass

    return correct, total

def test_random_recovery(n_samples=500):
    correct = 0
    total = 0
    
    for _ in range(n_samples):
        payload = {
            "internal_debt": random.uniform(0, 3000.0),
            "external_ecosystem_debt": random.uniform(0, 20000.0),
            "days_since_login": random.randint(0, 90),
            "demographic_age": random.randint(18, 70),
            "consent_revoked": random.choice([True, False]),
            "external_debt_data_age_days": random.randint(0, 120)
        }
        
        try:
            resp = requests.post(f"{BASE_URL}/predict/bnpl-recovery", json=payload).json()
            predicted = resp.get("recommended_channel", "email")
            
            expected = expected_recovery_channel(
                payload["internal_debt"], 
                payload["external_ecosystem_debt"], 
                payload["days_since_login"], 
                payload["demographic_age"], 
                payload["consent_revoked"], 
                payload["external_debt_data_age_days"]
            )
            
            if predicted == expected:
                correct += 1
            total += 1
        except Exception as e:
            pass

    return correct, total

if __name__ == "__main__":
    print(f"Running 1000 randomized predictions against live inference service at {BASE_URL}...\n")
    
    # Let's parallelize the requests to make it fast
    with ThreadPoolExecutor(max_workers=10) as executor:
        edge_future = executor.submit(test_random_edge, 500)
        recovery_future = executor.submit(test_random_recovery, 500)
        
        edge_correct, edge_total = edge_future.result()
        rec_correct, rec_total = recovery_future.result()

    print("=== LIVE ACCURACY RESULTS ===")
    if edge_total > 0:
        print(f"Engine 1 (Edge Checkout):   {edge_correct}/{edge_total} correct -> {(edge_correct/edge_total)*100:.2f}% Accuracy")
    else:
        print("Engine 1 failed to respond.")
        
    if rec_total > 0:
        print(f"Engine 2 (Recovery Routing): {rec_correct}/{rec_total} correct -> {(rec_correct/rec_total)*100:.2f}% Accuracy")
    else:
        print("Engine 2 failed to respond.")
