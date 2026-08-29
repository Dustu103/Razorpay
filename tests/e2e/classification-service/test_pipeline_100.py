import pandas as pd
import requests
import time
import psycopg2
import uuid
import os

def run_test():
    print("Preparing 100 real-world test cases from synthetic dataset...")
    
    # Load dataset
    csv_path = "/data/payment_failures/razorpay_payment_failures_synthetic.csv"
    df = pd.read_csv(csv_path)
    
    # Stratified sample: 20 from each of the 5 classes = 100
    categories = [
        'fraud_filter_block',
        'notification_compliance_block',
        'hard_decline',
        'gateway_fault',
        'soft_decline',
    ]
    frames = []
    for cat in categories:
        subset = df[df['label_cause'] == cat]
        sample_size = min(20, len(subset))
        frames.append(subset.sample(sample_size))
    
    test_df = pd.concat(frames).reset_index(drop=True)
    print(f"Loaded {len(test_df)} test cases across {len(categories)} categories.")
    
    ground_truth = {}
    txn_ids = []
    
    webhook_url = "http://ingestion-service:3001/api/v1/webhook"
    print(f"Sending {len(test_df)} transactions to the live Ingestion API...")
    
    sent_count = 0
    for _, row in test_df.iterrows():
        txn_id = str(uuid.uuid4())
        
        # Build the entity object with ALL available fields
        entity = {
            "id": txn_id,
            "status_code": str(row['status_code']).strip() if pd.notna(row['status_code']) else "FAILED",
            "amount": int(row['amount_paise']) if pd.notna(row['amount_paise']) else 0,
            "retry_count": int(row['retry_count_so_far']) if pd.notna(row['retry_count_so_far']) else 0,
            "currency": str(row['currency']) if pd.notna(row['currency']) else "INR",
        }
        
        # Optional fields
        if pd.notna(row.get('bank_response_code', None)) and str(row['bank_response_code']).strip() not in ('', 'nan'):
            entity["acquirer_data"] = str(row['bank_response_code']).strip()
        if pd.notna(row.get('npci_response_code', None)) and str(row['npci_response_code']).strip() not in ('', 'nan'):
            entity["npci_txn_id"] = str(row['npci_response_code']).strip()
        if pd.notna(row.get('issuer_bank', None)):
            entity["bank"] = str(row['issuer_bank'])
        
        # CRITICAL: send mandate timing fields so Layer 1 can fire for notification_compliance_block
        if pd.notna(row.get('mandate_notification_sent_at', None)):
            entity["mandate_notification_sent_at"] = str(row['mandate_notification_sent_at'])
        if pd.notna(row.get('debit_scheduled_at', None)):
            entity["debit_scheduled_at"] = str(row['debit_scheduled_at'])
        
        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": entity
                }
            }
        }
            
        try:
            resp = requests.post(webhook_url, json=payload, timeout=5)
            if resp.status_code in [200, 201, 202]:
                data = resp.json()
                db_txn_id = data.get('transaction_id', txn_id)
                txn_ids.append(db_txn_id)
                ground_truth[db_txn_id] = {
                    'expected_cause': row['label_cause'],
                    'expected_action': row['label_recommended_action']
                }
                sent_count += 1
            else:
                print(f"  [WARN] Ingestion returned {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"  [ERR] Failed to send: {e}")
            
    print(f"Successfully ingested {sent_count} transactions.")
    print("Waiting 20s for the Go worker + LLM ensemble to finish processing...")
    time.sleep(20)
    
    print("Connecting to Postgres to audit the results...")
    conn = psycopg2.connect("postgresql://razorpay:razorpay@postgres:5432/razorpay_classifier?sslmode=disable")
    cur = conn.cursor()
    
    if not txn_ids:
        print("ERROR: No transactions were ingested. Check ingestion service connectivity.")
        return
    
    query = "SELECT transaction_id, layer, cause, confidence, reasoning, recommended_action FROM classifications WHERE transaction_id IN %s"
    cur.execute(query, (tuple(txn_ids),))
    results = cur.fetchall()
    
    if len(results) == 0:
        print("ERROR: No results found in the database. Worker might have crashed or queue is stuck.")
        return
        
    print(f"\nFound {len(results)} processed classifications in the database.")
    
    l1_count = 0
    l2_count = 0
    l3_count = 0
    l4_count = 0
    correct = 0
    mismatches = []
    per_class = {cat: {'correct': 0, 'total': 0} for cat in categories}
    
    for row in results:
        t_id, layer, cause, conf, reasoning, action = row
        expected = ground_truth.get(t_id, {})
        exp_cause = expected.get('expected_cause', '?')
        
        if layer == 1:   l1_count += 1
        elif layer == 2: l2_count += 1
        elif layer == 3: l3_count += 1
        elif layer == 4: l4_count += 1
            
        per_class.setdefault(exp_cause, {'correct': 0, 'total': 0})
        per_class[exp_cause]['total'] += 1
        
        is_correct = (cause == exp_cause)
        if is_correct:
            correct += 1
            per_class[exp_cause]['correct'] += 1
        else:
            mismatches.append((t_id, exp_cause, cause, layer, conf, reasoning))
    
    # Print mismatches
    if mismatches:
        print("\n" + "="*80)
        print("MISMATCHES")
        print("="*80)
        for t_id, exp, pred, layer, conf, reasoning in mismatches:
            print(f"[ERROR] {t_id}")
            print(f"   Expected: {exp} | Got: {pred} (L{layer}, conf={conf:.2f})")
            print(f"   Reason: {reasoning[:120]}")
            print("-" * 40)
    
    accuracy = correct / len(results) * 100
    
    print("\n" + "="*80)
    print("SUMMARY — REAL-WORLD 100-CASE PIPELINE TEST")
    print("="*80)
    print(f"Total Processed: {len(results)} / {sent_count}")
    print(f"  Layer 1 (Deterministic):    {l1_count}")
    print(f"  Layer 2 (ML only):          {l2_count}")
    print(f"  Layer 3 (LLM only):         {l3_count}")
    print(f"  Layer 4 (Ensemble ML+LLM):  {l4_count}")
    print(f"\nOverall Accuracy: {correct}/{len(results)} = {accuracy:.2f}%")
    print(f"\nPer-Class Breakdown:")
    for cat, stats in per_class.items():
        if stats['total'] > 0:
            pct = stats['correct'] / stats['total'] * 100
            print(f"  {cat:<35} {stats['correct']}/{stats['total']} ({pct:.0f}%)")
    print("="*80)

if __name__ == "__main__":
    run_test()
