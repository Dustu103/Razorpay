import pandas as pd
import requests
import time
import psycopg2
import uuid
import os

def run_test():
    print("Preparing 100 critical real-world test cases...")
    
    # Load dataset
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, "..", "payment_failures", "razorpay_payment_failures_synthetic.csv")
    df = pd.read_csv(csv_path)
    
    df_fraud = df[df['label_cause'] == 'fraud_filter_block'].sample(15, random_state=99)
    df_compliance = df[df['label_cause'] == 'notification_compliance_block'].sample(15, random_state=99)
    df_hard = df[df['label_cause'] == 'hard_decline'].sample(30, random_state=99)
    df_gateway = df[df['label_cause'] == 'gateway_fault'].sample(20, random_state=99)
    df_soft = df[df['label_cause'] == 'soft_decline'].sample(20, random_state=99)
    
    test_df = pd.concat([df_fraud, df_compliance, df_hard, df_gateway, df_soft])
    
    ground_truth = {}
    txn_ids = []
    
    webhook_url = "http://ingestion-service:3001/api/v1/webhook"
    print("Sending 100 transactions to the live Ingestion API (this will trigger Layer 2 and Layer 3 Groq API)...")
    
    sent_count = 0
    for _, row in test_df.iterrows():
        txn_id = str(uuid.uuid4())
        # We'll get the actual transaction_id from the API response
        # ground_truth will be populated after successful API response
        
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": txn_id,
                        "status_code": row['status_code'] if pd.notna(row['status_code']) else "",
                        "amount": int(row['amount_paise']),
                        "retry_count": int(row['retry_count_so_far'])
                    }
                }
            }
        }
        
        if pd.notna(row['bank_response_code']):
            payload["payload"]["payment"]["entity"]["acquirer_data"] = str(row['bank_response_code'])
        if pd.notna(row['npci_response_code']):
            payload["payload"]["payment"]["entity"]["npci_txn_id"] = str(row['npci_response_code'])
        if pd.notna(row['issuer_bank']):
            payload["payload"]["payment"]["entity"]["bank"] = str(row['issuer_bank'])
            
        try:
            resp = requests.post(webhook_url, json=payload)
            time.sleep(2.5) # Avoid Groq 30 RPM rate limit
            if resp.status_code in [200, 202]:
                data = resp.json()
                db_txn_id = data.get('transaction_id')
                if db_txn_id:
                    txn_ids.append(db_txn_id)
                    ground_truth[db_txn_id] = {
                        'expected_cause': row['label_cause'],
                        'expected_action': row['label_recommended_action']
                    }
                sent_count += 1
            else:
                print(f"Failed status: {resp.status_code}")
        except Exception as e:
            print(f"Failed to send: {e}")
            
    print(f"Successfully ingested {sent_count} transactions.")
    print("Waiting 10 seconds for the Go worker to finish processing...")
    time.sleep(10)
    
    print("Connecting to Postgres to audit the results...")
    conn = psycopg2.connect("postgresql://razorpay:razorpay@postgres:5432/razorpay_classifier?sslmode=disable")
    cur = conn.cursor()
    
    query = "SELECT transaction_id, layer, cause, confidence, reasoning, recommended_action FROM classifications WHERE transaction_id IN %s"
    cur.execute(query, (tuple(txn_ids),))
    results = cur.fetchall()
    
    if len(results) == 0:
        print("ERROR: No results found in the database. Worker might have crashed or queue is stuck.")
        return
        
    print(f"\nFound {len(results)} processed classifications in the database.")
    
    l2_count = 0
    l3_count = 0
    correct = 0
    
    print("\n" + "="*80)
    print("CRITICAL AUDIT: REAL-WORLD DATA TEST (100 TRANSACTIONS)")
    print("="*80)
    
    for row in results:
        t_id, layer, cause, conf, reasoning, action = row
        expected = ground_truth.get(t_id, {})
        
        if layer == 2:
            l2_count += 1
        elif layer == 3:
            l3_count += 1
            
        is_correct = (cause == expected.get('expected_cause'))
        if is_correct:
            correct += 1
        else:
            print(f"[ERROR] Mismatch on {t_id}")
            print(f"   -> Expected: {expected.get('expected_cause')} | Predicted: {cause} (Layer {layer}, Conf: {conf:.2f})")
            print(f"   -> LLM/ML Reasoning: {reasoning}")
            print("-" * 40)
            
    accuracy = correct / len(results)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total Processed: {len(results)} / 100")
    print(f"Handled by Layer 2 (High-Speed ML): {l2_count}")
    print(f"Handled by Layer 3 (LLM Fallback):  {l3_count}")
    print(f"Overall Accuracy on Live Pipeline:  {accuracy*100:.2f}%")
    print("="*80)

if __name__ == "__main__":
    run_test()
