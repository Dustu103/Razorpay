import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def generate_retry_data(n_samples=5000):
    np.random.seed(42)
    day_of_month = np.random.randint(1, 31, n_samples)
    hour_of_day = np.random.randint(0, 24, n_samples)
    failure_cause_encoded = np.random.randint(0, 5, n_samples)
    payment_method_encoded = np.random.randint(0, 4, n_samples)
    retry_count = np.random.randint(1, 6, n_samples)
    time_since_failure_mins = np.random.randint(1, 1440, n_samples)
    
    success_probabilities = []
    for i in range(n_samples):
        cause = failure_cause_encoded[i]
        day = day_of_month[i]
        count = retry_count[i]
        
        if cause == 1:
            prob = 0.0
        else:
            prob = 0.35
            if cause == 2:
                prob = 0.65
            if day in [1, 2, 7, 8]:
                prob += 0.20
            if count > 3:
                prob -= 0.30
            prob = max(0.0, min(1.0, prob))
        success_probabilities.append(prob)
        
    retry_success = np.random.binomial(1, success_probabilities)
    return pd.DataFrame({
        "hour_of_day": hour_of_day,
        "day_of_month": day_of_month,
        "failure_cause_encoded": failure_cause_encoded,
        "payment_method_encoded": payment_method_encoded,
        "retry_count": retry_count,
        "time_since_failure_mins": time_since_failure_mins,
        "retry_success": retry_success
    })

def main():
    print("Generating synthetic data for Retry Routing...")
    df = generate_retry_data(n_samples=10000)
    
    X = df[["hour_of_day", "day_of_month", "failure_cause_encoded", "payment_method_encoded", "retry_count", "time_since_failure_mins"]]
    y = df["retry_success"]
    
    print("Training Feature B Random Forest model...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)
    
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models', 'ml')
    os.makedirs(models_dir, exist_ok=True)
    
    model_path = os.path.join(models_dir, 'feature_b.joblib')
    joblib.dump(clf, model_path)
    
    print(f"Model saved successfully to {model_path}")
    print(f"Model Accuracy on training data: {clf.score(X, y):.4f}")

if __name__ == "__main__":
    main()
