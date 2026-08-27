import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import os

def simulate_pipeline():
    print("Loading model and dataset to simulate full Layer 2 + Layer 3 pipeline...")
    
    # Paths
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, "..", "payment_failures", "razorpay_payment_failures_synthetic.csv")
    model_path = os.path.join(base_dir, "..", "..", "backend", "ml-service", "models", "layer2_payment_failure_model.pkl")
    
    # Load
    df = pd.read_csv(csv_path)
    model = joblib.load(model_path)
    
    categorical_features = ['status_code', 'bank_response_code', 'npci_response_code', 'currency', 'card_network', 'card_country_code', 'issuer_bank', 'is_recurring_transaction', 'cardholder_auth_method']
    numeric_features = ['amount_paise', 'retry_count_so_far']
    
    for col in categorical_features:
        df[col] = df[col].fillna('MISSING').astype(str)
        
    X = df[categorical_features + numeric_features]
    y = df['label_cause']
    
    # We only care about the test set
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print(f"\nSimulating pipeline on {len(X_test)} test transactions...")
    
    # ML Predictions
    probs = model.predict_proba(X_test)
    classes = model.classes_
    
    # Go backend Thresholds
    THRESHOLDS = {
        'do_not_retry': 0.85,
        'retry_scheduled': 0.80,
        'retry_now': 0.80,
        'reverify_and_reverse': 0.95,
        'default': 0.50
    }
    
    # Hardcoded action map (simplified from Go backend logic)
    def get_action(cause):
        if cause in ["hard_decline", "fraud_filter_block", "notification_compliance_block"]:
            return "do_not_retry"
        return "retry_scheduled"

    l2_handled = 0
    l2_correct = 0
    l3_fallback = 0
    
    y_test_list = y_test.tolist()
    
    for i in range(len(X_test)):
        max_prob = np.max(probs[i])
        pred_cause = classes[np.argmax(probs[i])]
        true_cause = y_test_list[i]
        
        action = get_action(pred_cause)
        threshold = THRESHOLDS.get(action, THRESHOLDS['default'])
        
        if max_prob >= threshold:
            # ML Model is confident enough. Layer 2 handles it!
            l2_handled += 1
            if pred_cause == true_cause:
                l2_correct += 1
        else:
            # ML Model is not confident. Falls back to Layer 3 (LLM)
            l3_fallback += 1
            
    # Calculate stats
    l2_coverage = l2_handled / len(X_test)
    l2_accuracy_on_handled = l2_correct / l2_handled if l2_handled > 0 else 0
    
    # Assume LLM (Layer 3) has a conservative 95% accuracy on fallbacks
    # In reality, with a powerful model like GPT-4 or Llama-3, it's often 95-98%.
    LLM_ASSUMED_ACCURACY = 0.95
    l3_estimated_correct = int(l3_fallback * LLM_ASSUMED_ACCURACY)
    
    total_correct = l2_correct + l3_estimated_correct
    overall_accuracy = total_correct / len(X_test)
    
    print("\n" + "="*50)
    print("PIPELINE SIMULATION RESULTS (ML + LLM Fallback)")
    print("="*50)
    print(f"Total Test Transactions:  {len(X_test):,}")
    print(f"Handled by Layer 2 (ML):  {l2_handled:,} ({(l2_coverage*100):.1f}% of traffic)")
    print(f"Fell back to Layer 3:     {l3_fallback:,} ({(1 - l2_coverage)*100:.1f}% of traffic)")
    print("-" * 50)
    print(f"Layer 2 Accuracy (on its share): {l2_accuracy_on_handled*100:.2f}%")
    print(f"Layer 3 Assumed Accuracy:        {LLM_ASSUMED_ACCURACY*100:.2f}%")
    print("-" * 50)
    print(f"OVERALL PIPELINE ACCURACY:       {overall_accuracy*100:.2f}%")
    print("="*50)
    print("Note: We mathematically simulate Layer 3's contribution here because running 20,000 real HTTP requests to the Groq API would immediately hit free-tier rate limits.")

if __name__ == "__main__":
    simulate_pipeline()
