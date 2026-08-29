import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def generate_fraud_data(n_samples=5000):
    np.random.seed(42)
    amount = np.random.exponential(1500, n_samples) + 10
    transaction_velocity = np.random.randint(1, 10, n_samples)
    is_known_device = np.random.binomial(1, 0.8, n_samples)
    ip_risk_score = np.random.uniform(0.0, 1.0, n_samples)
    merchant_category_encoded = np.random.randint(0, 5, n_samples)
    transaction_hour = np.random.randint(0, 24, n_samples)
    
    fraud_probabilities = []
    for i in range(n_samples):
        vel = transaction_velocity[i]
        amt = amount[i]
        device = is_known_device[i]
        risk = ip_risk_score[i]
        
        prob = 0.02
        if vel > 5 and amt > 5000:
            prob = 0.85
        if risk > 0.8 and device == 0:
            prob = 0.90
        prob = max(0.0, min(1.0, prob))
        fraud_probabilities.append(prob)
        
    is_fraud = np.random.binomial(1, fraud_probabilities)
    return pd.DataFrame({
        "amount": amount,
        "transaction_velocity": transaction_velocity,
        "is_known_device": is_known_device,
        "ip_risk_score": ip_risk_score,
        "merchant_category_encoded": merchant_category_encoded,
        "transaction_hour": transaction_hour,
        "is_fraud": is_fraud
    })

def main():
    print("Generating synthetic data for False Decline Detection...")
    df = generate_fraud_data(n_samples=10000)
    
    X = df[["amount", "transaction_velocity", "is_known_device", "ip_risk_score", "merchant_category_encoded", "transaction_hour"]]
    y = df["is_fraud"]
    
    print("Training Feature D Random Forest model...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)
    
    # Save the model
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models', 'ml')
    os.makedirs(models_dir, exist_ok=True)
    
    model_path = os.path.join(models_dir, 'feature_d.joblib')
    joblib.dump(clf, model_path)
    
    print(f"Model saved successfully to {model_path}")
    print(f"Model Accuracy on training data: {clf.score(X, y):.4f}")

if __name__ == "__main__":
    main()
