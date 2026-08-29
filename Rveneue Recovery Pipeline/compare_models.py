import sys
import os
import time
import pandas as pd
from dotenv import load_dotenv

# Load env variables for API key
load_dotenv()

# Add the pipeline directory to the path so we can import its modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from models.feature_a import FeatureAClassifier
from schemas import TransactionInput

def main():
    # Load 50 cases from the dataset for a quick benchmark
    dataset_path = os.path.join(os.path.dirname(__file__), "..", "data", "payment_failures", "razorpay_payment_failures_synthetic.csv")
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}")
        return

    df = pd.read_csv(dataset_path)
    
    # Stratified sample of 50 cases (10 per class)
    categories = ['soft_decline', 'hard_decline', 'gateway_fault', 'fraud_filter_block', 'notification_compliance_block']
    frames = []
    for cat in categories:
        subset = df[df['label_cause'] == cat]
        frames.append(subset.sample(min(10, len(subset)), random_state=42))
    
    test_df = pd.concat(frames).reset_index(drop=True)
    
    classifier = FeatureAClassifier()
    if not classifier.model:
        print("WARNING: Gemini API Key not found or invalid. Prototype will use heuristic fallback entirely!")
    
    correct = 0
    total = len(test_df)
    start_time = time.time()
    
    for idx, row in test_df.iterrows():
        tx = TransactionInput(
            status_code=str(row['status_code']),
            npci_response_code=str(row['npci_response_code']),
            retry_count_so_far=int(row['retry_count_so_far']),
            amount=float(row['amount_paise']) / 100,  # prototype expects amount in rupees
            customer_bank=str(row['issuer_bank']),
            time_since_last_failure=0
        )
        
        try:
            result = classifier.classify(tx)
            predicted_cause = result.cause.value
            
            if predicted_cause == row['label_cause']:
                correct += 1
            else:
                print(f"[MISMATCH] Expected: {row['label_cause']} | Got: {predicted_cause}")
                print(f"Reasoning: {result.reasoning}")
                print(f"Tx Context: {tx.model_dump_json()}\n")
        except Exception as e:
            print(f"[ERROR] Failed to classify {tx.model_dump_json()}: {e}")
            
    end_time = time.time()
    
    print("\n" + "="*50)
    print("PROTOTYPE (Feature A) ACCURACY RESULTS")
    print("="*50)
    print(f"Total Evaluated: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {(correct/total)*100:.2f}%")
    print(f"Total Time: {end_time - start_time:.2f} seconds")
    print(f"Average Latency: {(end_time - start_time)/total:.2f} sec/transaction")
    print("="*50)

if __name__ == "__main__":
    main()
