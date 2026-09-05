"""
Comprehensive Accuracy & Training Methodology Audit
====================================================
Evaluates accuracy across all ML models in models/ml/ on unseen holdout
synthetic data (seed=999) to verify out-of-sample generalization.
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score


def evaluate_feature_b():
    model_path = "models/ml/feature_b.joblib"
    if not os.path.exists(model_path):
        return None
    clf = joblib.load(model_path)

    # Generate unseen holdout test split (Seed 999 - different from train seed 42)
    np.random.seed(999)
    n = 2000
    b_hour = np.random.randint(0, 24, n)
    b_day = np.random.randint(1, 31, n)
    b_cause = np.random.randint(0, 5, n)
    b_method = np.random.randint(0, 4, n)
    b_count = np.random.randint(1, 6, n)
    b_time = np.random.randint(1, 1440, n)

    b_probs = []
    for i in range(n):
        if b_cause[i] == 1:
            p = 0.0
        else:
            p = 0.35
            if b_cause[i] == 2: p = 0.65
            if b_day[i] in [1, 2, 7, 8]: p += 0.20
            if b_count[i] > 3: p -= 0.30
            p = max(0.0, min(1.0, p))
        b_probs.append(p)
    y_true = np.random.binomial(1, b_probs)

    X = pd.DataFrame({
        "hour_of_day": b_hour,
        "day_of_month": b_day,
        "failure_cause_encoded": b_cause,
        "payment_method_encoded": b_method,
        "retry_count": b_count,
        "time_since_failure_mins": b_time,
    })

    y_pred = clf.predict(X)
    return {
        "model": "Feature B (Intelligent Retry Routing)",
        "type": "Random Forest Classifier",
        "training_data": "Synthetic (calibrated to bank clearing cycles)",
        "accuracy": accuracy_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "samples": n
    }


def evaluate_feature_c():
    model_path = "models/ml/feature_c.joblib"
    if not os.path.exists(model_path):
        return None
    clf = joblib.load(model_path)

    np.random.seed(999)
    n = 2000
    channel_encoded = np.random.randint(0, 3, n)
    time_since_failure_mins = np.random.randint(5, 2880, n)
    customer_tenure_months = np.random.randint(1, 60, n)
    prior_payment_success_rate = np.random.uniform(0.1, 1.0, n)

    response_probabilities = []
    for i in range(n):
        ch = channel_encoded[i]
        mins = time_since_failure_mins[i]
        rate = prior_payment_success_rate[i]

        base = 0.65 if ch == 0 else (0.25 if ch == 1 else 0.15)
        mult = 1.0 if mins <= 30 else (0.7 if mins <= 120 else (0.4 if mins <= 720 else 0.2))
        prob = base * mult
        if rate > 0.85: prob += 0.15
        prob = max(0.0, min(1.0, prob))
        response_probabilities.append(prob)

    y_true = np.random.binomial(1, response_probabilities)

    X = pd.DataFrame({
        "channel_encoded": channel_encoded,
        "time_since_failure_mins": time_since_failure_mins,
        "customer_tenure_months": customer_tenure_months,
        "prior_payment_success_rate": prior_payment_success_rate,
    })

    y_pred = clf.predict(X)
    return {
        "model": "Feature C (Dunning Channel Optimization)",
        "type": "Random Forest Classifier",
        "training_data": "Synthetic (calibrated to customer response curves)",
        "accuracy": accuracy_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "samples": n
    }


def evaluate_feature_d():
    model_path = "models/ml/feature_d.joblib"
    if not os.path.exists(model_path):
        return None
    clf = joblib.load(model_path)

    np.random.seed(999)
    n = 2000
    amount = np.random.exponential(1500, n) + 10
    velocity = np.random.randint(1, 10, n)
    device = np.random.binomial(1, 0.8, n)
    ip_risk = np.random.uniform(0.0, 1.0, n)
    merchant_category_encoded = np.random.randint(0, 5, n)
    transaction_hour = np.random.randint(0, 24, n)

    probs = []
    for i in range(n):
        vel = velocity[i]
        amt = amount[i]
        dev = device[i]
        risk = ip_risk[i]

        prob = 0.02
        if vel > 5 and amt > 5000:
            prob = 0.85
        if risk > 0.8 and dev == 0:
            prob = 0.90
        probs.append(max(0.0, min(1.0, prob)))

    y_true = np.random.binomial(1, probs)

    X = pd.DataFrame({
        "amount": amount,
        "transaction_velocity": velocity,
        "is_known_device": device,
        "ip_risk_score": ip_risk,
        "merchant_category_encoded": merchant_category_encoded,
        "transaction_hour": transaction_hour,
    })

    y_pred = clf.predict(X)
    return {
        "model": "Feature D (False Decline Recovery)",
        "type": "Random Forest Classifier",
        "training_data": "Synthetic (calibrated to fraud velocity rules)",
        "accuracy": accuracy_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "samples": n
    }


def evaluate_bnpl_edge():
    model_path = "models/ml/feature_e_edge.joblib"
    if not os.path.exists(model_path):
        return None
    clf = joblib.load(model_path)

    np.random.seed(999)
    n = 2000
    amount = np.random.exponential(3000, n) + 500
    decline_reason = np.random.randint(0, 4, n)
    tenure_months = np.random.randint(0, 60, n)

    conversion_probs = []
    for i in range(n):
        amt = amount[i]
        reason = decline_reason[i]
        tenure = tenure_months[i]
        prob = 0.10
        if reason == 0 and amt > 2500:
            prob = 0.80
        if tenure > 24:
            prob += 0.15
        if reason == 3:
            prob = 0.20
        prob = max(0.0, min(1.0, prob))
        conversion_probs.append(prob)

    y_true = np.random.binomial(1, conversion_probs)

    X = pd.DataFrame({
        "amount": amount,
        "decline_reason": decline_reason,
        "tenure_months": tenure_months,
    })

    y_pred = clf.predict(X)
    return {
        "model": "Feature E (BNPL Edge Offer Engine)",
        "type": "Random Forest Classifier",
        "training_data": "Synthetic (exponential amounts + decline reasons)",
        "accuracy": accuracy_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "samples": n
    }


def main():
    print("=" * 80)
    print("EMPIRICAL ACCURACY AUDIT ACROSS ALL LOCAL MACHINE LEARNING MODELS")
    print("Holdout Test Set: N=2,000 unseen synthetic samples per model (Seed=999)")
    print("=" * 80)

    evals = [
        evaluate_feature_b(),
        evaluate_feature_c(),
        evaluate_feature_d(),
        evaluate_bnpl_edge(),
    ]

    for ev in evals:
        if ev is None: continue
        print(f"Model Name:      {ev['model']}")
        print(f"  Architecture:  {ev['type']}")
        print(f"  Training Data: {ev['training_data']}")
        print(f"  Test Accuracy: {ev['accuracy'] * 100:.2f}% (Holdout N={ev['samples']:,})")
        print(f"  Test F1 Score: {ev['f1']:.4f}")
        print("-" * 80)


if __name__ == "__main__":
    main()
