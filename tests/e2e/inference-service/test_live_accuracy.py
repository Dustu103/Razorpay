import requests
import time
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score

# Replicate the exact synthetic data generation used during training (Seed 42)
def generate_test_data(n_samples=500):
    np.random.seed(42)
    # Feature B (Retry)
    b_hour = np.random.randint(0, 24, n_samples)
    b_day = np.random.randint(1, 31, n_samples)
    b_cause = np.random.randint(0, 5, n_samples)
    b_method = np.random.randint(0, 4, n_samples)
    b_count = np.random.randint(1, 6, n_samples)
    b_time = np.random.randint(1, 1440, n_samples)
    b_probs = []
    for i in range(n_samples):
        cause = b_cause[i]
        day = b_day[i]
        count = b_count[i]
        if cause == 1: prob = 0.0
        else:
            prob = 0.35
            if cause == 2: prob = 0.65
            if day in [1, 2, 7, 8]: prob += 0.20
            if count > 3: prob -= 0.30
            prob = max(0.0, min(1.0, prob))
        b_probs.append(prob)
    b_target = np.random.binomial(1, b_probs)

    # Feature C (Dunning)
    c_channel = np.random.randint(0, 3, n_samples)
    c_time = np.random.randint(5, 2880, n_samples)
    c_tenure = np.random.randint(1, 60, n_samples)
    c_rate = np.random.uniform(0.1, 1.0, n_samples)
    c_probs = []
    for i in range(n_samples):
        ch = c_channel[i]
        mins = c_time[i]
        rate = c_rate[i]
        if ch == 0: base = 0.65
        elif ch == 1: base = 0.25
        else: base = 0.15
        if mins <= 30: mult = 1.0
        elif mins <= 120: mult = 0.7
        elif mins <= 720: mult = 0.4
        else: mult = 0.2
        prob = base * mult
        if rate > 0.85: prob += 0.15
        prob = max(0.0, min(1.0, prob))
        c_probs.append(prob)
    c_target = np.random.binomial(1, c_probs)

    # Feature D (False Decline)
    d_amount = np.random.exponential(1500, n_samples) + 10
    d_velocity = np.random.randint(1, 10, n_samples)
    d_device = np.random.binomial(1, 0.8, n_samples)
    d_ip = np.random.uniform(0.0, 1.0, n_samples)
    d_cat = np.random.randint(0, 5, n_samples)
    d_probs = []
    for i in range(n_samples):
        amount = d_amount[i]
        vel = d_velocity[i]
        dev = d_device[i]
        ip = d_ip[i]
        
        prob = 0.02
        if vel > 5 and amount > 5000:
            prob = 0.85
        if ip > 0.8 and dev == 0:
            prob = 0.90
            
        prob = max(0.0, min(1.0, prob))
        d_probs.append(prob)
        
    d_target = np.random.binomial(1, d_probs)
    # Target is is_fraud. We want to predict if it's a false decline (i.e. NOT fraud)
    d_target = 1 - d_target

    return pd.DataFrame({
        "b_hour": b_hour, "b_day": b_day, "b_cause": b_cause, "b_method": b_method, "b_count": b_count, "b_time": b_time, "b_target": b_target,
        "c_channel": c_channel, "c_time": c_time, "c_tenure": c_tenure, "c_rate": c_rate, "c_target": c_target,
        "d_amount": d_amount, "d_velocity": d_velocity, "d_device": d_device, "d_ip": d_ip, "d_cat": d_cat, "d_target": d_target
    })

def main():
    print("Generating 500 test cases...")
    df = generate_test_data(500)
    
    urls = {
        "b": "http://localhost:8000/predict/retry",
        "c": "http://localhost:8000/predict/dunning",
        "d": "http://localhost:8000/predict/false-decline"
    }

    preds_b = []
    preds_c = []
    preds_d = []
    
    print("Hitting live Inference Service API for 500 cases...")
    
    start_time = time.time()
    for _, row in df.iterrows():
        # Feature B
        res_b = requests.post(urls["b"], json={
            "hour_of_day": int(row["b_hour"]),
            "day_of_month": int(row["b_day"]),
            "failure_cause_encoded": int(row["b_cause"]),
            "payment_method_encoded": int(row["b_method"]),
            "retry_count": int(row["b_count"]),
            "time_since_failure_mins": int(row["b_time"])
        }).json()
        pred = 1 if res_b.get("retry_success_probability", 0) >= 0.5 else 0
        preds_b.append(pred)
        
        # Feature C
        res_c = requests.post(urls["c"], json={
            "channel_encoded": int(row["c_channel"]),
            "time_since_failure_mins": int(row["c_time"]),
            "customer_tenure_months": int(row["c_tenure"]),
            "prior_payment_success_rate": float(row["c_rate"])
        }).json()
        pred = 1 if res_c.get("payment_probability", 0) >= 0.5 else 0
        preds_c.append(pred)
        
        # Feature D
        res_d = requests.post(urls["d"], json={
            "amount": float(row["d_amount"]),
            "transaction_velocity": int(row["d_velocity"]),
            "is_known_device": int(row["d_device"]),
            "ip_risk_score": float(row["d_ip"]),
            "merchant_category": "retail",
            "transaction_hour": 12
        }).json()
        pred = 1 if res_d.get("false_decline_likelihood", 0) >= 0.5 else 0
        preds_d.append(pred)

    total_time = time.time() - start_time
    
    print("\n" + "="*50)
    print("LIVE API ACCURACY RESULTS")
    print("="*50)
    print(f"Total Inference Time (1500 API calls): {total_time:.2f} seconds")
    print(f"Average API Latency: {(total_time/1500)*1000:.2f} ms per request\n")
    print(f"Feature B (Retry Routing) Accuracy:   {accuracy_score(df['b_target'], preds_b)*100:.2f}%")
    print(f"Feature C (Dunning) Accuracy:         {accuracy_score(df['c_target'], preds_c)*100:.2f}%")
    print(f"Feature D (False Decline) Accuracy:   {accuracy_score(df['d_target'], preds_d)*100:.2f}%")
    print("="*50)

if __name__ == "__main__":
    main()
