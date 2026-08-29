import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def generate_edge_data(n_samples=5000):
    np.random.seed(42)
    # Features
    amount = np.random.exponential(3000, n_samples) + 500
    decline_reason = np.random.randint(0, 4, n_samples) # 0=InsuffFunds, 1=IssuerRestrict, 2=CrossBorder, 3=Technical
    tenure_months = np.random.randint(0, 60, n_samples)
    
    conversion_probs = []
    for i in range(n_samples):
        amt = amount[i]
        reason = decline_reason[i]
        tenure = tenure_months[i]
        
        prob = 0.10 # Base low conversion
        
        # BNPL is highly effective for Insufficient Funds on large amounts
        if reason == 0 and amt > 2500:
            prob = 0.80
            
        # Loyal customers more likely to accept
        if tenure > 24:
            prob += 0.15
            
        # If technical decline, BNPL is not the issue, just a different rail
        if reason == 3:
            prob = 0.20
            
        prob = max(0.0, min(1.0, prob))
        conversion_probs.append(prob)
        
    converts = np.random.binomial(1, conversion_probs)
    return pd.DataFrame({
        "amount": amount,
        "decline_reason": decline_reason,
        "tenure_months": tenure_months,
        "converts": converts
    })

def main():
    print("Generating synthetic data for Edge BNPL Offer Engine...")
    df = generate_edge_data(10000)
    
    X = df[["amount", "decline_reason", "tenure_months"]]
    y = df["converts"]
    
    print("Training Edge BNPL Random Forest model...")
    clf = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42)
    clf.fit(X, y)
    
    # Save the model
    models_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'ml')
    os.makedirs(models_dir, exist_ok=True)
    
    model_path = os.path.join(models_dir, 'feature_e_edge.joblib')
    joblib.dump(clf, model_path)
    
    print(f"Model saved successfully to {model_path}")
    print(f"Model Accuracy on training data: {clf.score(X, y):.4f}")

if __name__ == "__main__":
    main()
