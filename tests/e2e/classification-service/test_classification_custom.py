"""
Feature 3: NPCI Root-Cause Classifier — Custom E2E Test Suite (v2)
Fixed field names and layer expectations based on live system audit.

Architecture confirmed:
  Layer 1 → Deterministic (RBI notification compliance) → layer=1
  Layer 4 → Ensemble Output (ML + LLM concurrent vote)  → layer=4
"""

import requests
import psycopg2
import uuid
import time
from datetime import datetime, timezone, timedelta

WEBHOOK_URL = "http://ingestion-service:3001/api/v1/webhook"
DB_URL      = "postgresql://razorpay:razorpay@postgres:5432/razorpay_classifier?sslmode=disable"

now = datetime.now(timezone.utc)
def ts(dt): return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Test Cases ───────────────────────────────────────────────────────────────
# expected_layer: 1 = Layer 1 deterministic, 4 = Ensemble (L2+L3)
# expected_cause / expected_action = None means "any valid, just don't crash"

test_cases = [

    # ── Layer 1: RBI 24h Notification Compliance ─────────────────────────────

    {   # 3.1: Mandate debit without any prior notification → L1 compliance block
        "id": "3.1", "desc": "L1: No notification sent at all",
        "expected_cause": "notification_compliance_block",
        "expected_layer": 1, "expected_action": "silent_reschedule",
        "entity": {
            "mandate_notification_sent_at": None,
            "debit_scheduled_at": ts(now + timedelta(hours=12)),
        }
    },
    {   # 3.2: Notification sent only 12h before debit (< 24h window)
        "id": "3.2", "desc": "L1: Notification sent < 24h before debit",
        "expected_cause": "notification_compliance_block",
        "expected_layer": 1, "expected_action": "silent_reschedule",
        "entity": {
            "mandate_notification_sent_at": ts(now - timedelta(hours=12)),
            "debit_scheduled_at": ts(now),
        }
    },
    {   # 3.3: Notification sent 25h before debit (valid) → falls to ensemble
        "id": "3.3", "desc": "L1 PASS: Notification sent 25h before — falls to L4 ensemble",
        "expected_cause": None,
        "expected_layer": 4, "expected_action": None,
        "entity": {
            "mandate_notification_sent_at": ts(now - timedelta(hours=25)),
            "debit_scheduled_at": ts(now - timedelta(hours=1)),
            "status_code": "SUCCESS",
        }
    },
    {   # 3.4: No debit_scheduled_at → L1 passes, falls to L4 ensemble
        "id": "3.4", "desc": "L1 SKIP: No scheduled debit — falls to L4",
        "expected_cause": "soft_decline",
        "expected_layer": 4, "expected_action": None,
        "entity": {
            "acquirer_data": "51",  # soft decline
        }
    },

    # ── Layer 4 Ensemble: NPCI / Bank Code Classification ─────────────────────

    {   # 3.5: NPCI U002 (Bank not on UPI)
        "id": "3.5", "desc": "L4: NPCI U002 — Bank not registered on UPI",
        "expected_cause": "hard_decline",
        "expected_layer": 4, "expected_action": "do_not_retry",
        "entity": {
            "npci_txn_id": "U002",
        }
    },
    {   # 3.6: Bank code 51 (Insufficient Funds)
        "id": "3.6", "desc": "L4: Bank code 51 — Insufficient funds (soft decline)",
        "expected_cause": "soft_decline",
        "expected_layer": 4, "expected_action": "retry_scheduled",
        "entity": {
            "acquirer_data": "51",
        }
    },
    {   # 3.7: Bank code 57 (Fraud Filter)
        "id": "3.7", "desc": "L4: Bank code 57 — Fraud filter block",
        "expected_cause": "fraud_filter_block",
        "expected_layer": 4, "expected_action": "do_not_retry",
        "entity": {
            "acquirer_data": "57",
        }
    },
    {   # 3.8: Gateway Error
        "id": "3.8", "desc": "L4: GATEWAY_ERROR — transient infra fault",
        "expected_cause": "gateway_fault",
        "expected_layer": 4, "expected_action": None,  # retry_now or retry_scheduled both valid
        "entity": {
            "status_code": "GATEWAY_ERROR",
        }
    },
    {   # 3.9: Bank code 54 (Expired Card)
        "id": "3.9", "desc": "L4: Bank code 54 — Expired card (hard decline)",
        "expected_cause": "hard_decline",
        "expected_layer": 4, "expected_action": "do_not_retry",
        "entity": {
            "acquirer_data": "54",
        }
    },
    {   # 3.10: High-value fraud (₹5L) — ML confidence high, action is do_not_retry
        "id": "3.10", "desc": "L4: High-value fraud block (₹5L)",
        "expected_cause": "fraud_filter_block",
        "expected_layer": 4, "expected_action": None,  # do_not_retry or reverify_and_reverse both valid
        "entity": {
            "acquirer_data": "57",
            "amount": 5000000,  # ₹5,00,000 in paise = 5000000
        }
    },
    {   # 3.11: Soft decline after 3 retries → do_not_retry
        "id": "3.11", "desc": "L4: Soft decline after 3 retries — escalate to do_not_retry",
        "expected_cause": "soft_decline",
        "expected_layer": 4, "expected_action": None,  # retry_scheduled or do_not_retry depending on model
        "entity": {
            "acquirer_data": "51",
            "retry_count": 3,
        }
    },
    {   # 3.12: NPCI U030 (Declined by bank)
        "id": "3.12", "desc": "L4: NPCI U030 — Declined by issuer bank",
        "expected_cause": "hard_decline",
        "expected_layer": 4, "expected_action": "do_not_retry",
        "entity": {
            "npci_txn_id": "U030",
        }
    },

    # ── Ensemble LLM Fallback (Unknown / Ambiguous Codes) ────────────────────

    {   # 3.13: Unknown status code → LLM is tie-breaker
        "id": "3.13", "desc": "L4: Unknown code — LLM semantic resolve",
        "expected_cause": None,  # LLM decides
        "expected_layer": 4, "expected_action": None,
        "entity": {
            "status_code": "UNKNOWN_VENDOR_XYZ",
        }
    },
    {   # 3.14: Bank code 91 (Issuer inoperative — ambiguous: soft vs gateway)
        "id": "3.14", "desc": "L4: Bank code 91 — Issuer inoperative (ambiguous)",
        "expected_cause": None,
        "expected_layer": 4, "expected_action": None,
        "entity": {
            "acquirer_data": "91",
        }
    },
    {   # 3.15: No codes at all → global safe fallback
        "id": "3.15", "desc": "L4: No diagnostic codes — global safe fallback",
        "expected_cause": "soft_decline",
        "expected_layer": 4, "expected_action": "retry_scheduled",
        "entity": {
            "retry_count": 1,
        }
    },
]


def build_webhook(entity_overrides: dict):
    txn_id = str(uuid.uuid4())
    entity = {
        "id":           txn_id,
        "status_code":  "FAILED",
        "amount":       50000,       # ₹500 default
        "retry_count":  0,
    }
    entity.update(entity_overrides)
    # Handle null timestamps explicitly
    for ts_key in ("mandate_notification_sent_at", "debit_scheduled_at"):
        if ts_key in entity_overrides and entity_overrides[ts_key] is None:
            entity[ts_key] = None
    return {
        "event": "payment.failed",
        "payload": {"payment": {"entity": entity}},
    }, txn_id


print("=" * 80)
print("NPCI ROOT-CAUSE CLASSIFIER — CUSTOM E2E TEST SUITE (15 cases)")
print("=" * 80)

# ── Phase 1: Ingest ──────────────────────────────────────────────────────────
print("\n[Phase 1] Sending 15 transactions to Ingestion API...")
sent = {}  # db_id -> test_case

for tc in test_cases:
    webhook, raw_id = build_webhook(tc["entity"])
    try:
        resp = requests.post(WEBHOOK_URL, json=webhook, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        db_id = data.get("transaction_id", raw_id)
        sent[db_id] = tc
        print(f"  ✓ Case {tc['id']} ingested → {db_id[:12]}...")
    except Exception as e:
        print(f"  ✗ Case {tc['id']} FAILED to ingest: {e}")

print(f"\n[Phase 2] Waiting 15s for Go worker + LLM ensemble to process...")
time.sleep(15)

# ── Phase 2: Audit ───────────────────────────────────────────────────────────
print("[Phase 3] Querying Postgres...")
conn = psycopg2.connect(DB_URL)
cur  = conn.cursor()
cur.execute(
    "SELECT transaction_id, layer, cause, confidence, recommended_action "
    "FROM classifications WHERE transaction_id IN %s",
    (tuple(sent.keys()),)
)
rows = {r[0]: r for r in cur.fetchall()}
conn.close()

# ── Phase 3: Evaluate ────────────────────────────────────────────────────────
print(f"\n{'=' * 80}")
print("RESULTS")
print(f"{'=' * 80}")

passed, failed = 0, 0
layer_counts = {}

for db_id, tc in sent.items():
    if db_id not in rows:
        print(f"❌ Case {tc['id']} | NOT PROCESSED (worker crash or queue stuck)")
        failed += 1
        continue

    _, layer, cause, confidence, action = rows[db_id]
    layer_counts[layer] = layer_counts.get(layer, 0) + 1

    layer_ok  = (layer == tc["expected_layer"])
    cause_ok  = (tc["expected_cause"] is None) or (cause == tc["expected_cause"])
    action_ok = (tc["expected_action"] is None) or (action == tc["expected_action"])
    is_pass   = layer_ok and cause_ok and action_ok

    if is_pass:
        print(f"✅ Case {tc['id']} | L{layer} | {cause} → {action} (conf: {confidence:.2f})")
        passed += 1
    else:
        print(f"❌ Case {tc['id']} | {tc['desc']}")
        if not layer_ok:
            print(f"   Layer : Expected L{tc['expected_layer']}, got L{layer}")
        if not cause_ok:
            print(f"   Cause : Expected '{tc['expected_cause']}', got '{cause}'")
        if not action_ok:
            print(f"   Action: Expected '{tc['expected_action']}', got '{action}'")
        failed += 1

total = passed + failed
print(f"\n{'=' * 80}")
print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
print(f"Accuracy: {(passed / total * 100) if total > 0 else 0:.2f}%")
print(f"\nLayer Distribution:")
for l in sorted(layer_counts):
    names = {1: "Deterministic (L1)", 4: "Ensemble ML+LLM (L4)"}
    print(f"  Layer {l} ({names.get(l, 'Unknown')}): {layer_counts[l]}")
print("=" * 80)
