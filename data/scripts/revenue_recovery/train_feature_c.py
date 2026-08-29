import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def generate_dunning_data(n_samples=2000):
    np.random.seed(42)
    channel_encoded = np.random.randint(0, 3, n_samples)
    time_since_failure_mins = np.random.randint(5, 2880, n_samples)
    customer_tenure_months = np.random.randint(1, 60, n_samples)
    prior_payment_success_rate = np.random.uniform(0.1, 1.0, n_samples)
    
    response_probabilities = []
    for i in range(n_samples):
        ch = channel_encoded[i]
        mins = time_since_failure_mins[i]
        rate = prior_payment_success_rate[i]
        
        if ch == 0:
            base = 0.65
        elif ch == 1:
            base = 0.25
        else:
            base = 0.15
            
        if mins <= 30:
            mult = 1.0
        elif mins <= 120:
            mult = 0.7
        elif mins <= 720:
            mult = 0.4
        else:
            mult = 0.2
            
        prob = base * mult
        if rate > 0.85:
            prob += 0.15
        prob = max(0.0, min(1.0, prob))
        response_probabilities.append(prob)
        
    customer_paid = np.random.binomial(1, response_probabilities)
    return pd.DataFrame({
        "channel_encoded": channel_encoded,
        "time_since_failure_mins": time_since_failure_mins,
        "customer_tenure_months": customer_tenure_months,
        "prior_payment_success_rate": prior_payment_success_rate,
        "customer_paid": customer_paid
    })

def main():
    print("Generating synthetic data for Dunning Optimization...")
    df = generate_dunning_data(n_samples=10000)
    
    X = df[["channel_encoded", "time_since_failure_mins", "customer_tenure_months", "prior_payment_success_rate"]]
    y = df["customer_paid"]
    
    print("Training Feature C Random Forest model...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)
    
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models', 'ml')
    os.makedirs(models_dir, exist_ok=True)
    
    model_path = os.path.join(models_dir, 'feature_c.joblib')
    joblib.dump(clf, model_path)
    
    print(f"Model saved successfully to {model_path}")
    print(f"Model Accuracy on training data: {clf.score(X, y):.4f}")

if __name__ == "__main__":
    main()
