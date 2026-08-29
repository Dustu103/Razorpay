"""
generate_synthetic_data.py
──────────────────────────
Generates a synthetic dataset of payment failure transactions and bootstraps
Layer 2 labels using the Groq API (GPT-OSS-120B).

Usage:
  python scripts/generate_synthetic_data.py --count 500 --output data/synthetic_labeled.jsonl

Prerequisites:
  pip install -r requirements.txt
  export GROQ_API_KEY=gsk_...
"""

import argparse
import json
import os
import random
import time
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ── Classification schema (matches Go models) ─────────────────────────────────

CAUSES = [
    "notification_compliance_block",
    "soft_decline",
    "hard_decline",
    "gateway_fault",
    "fraud_filter_block",
]

ACTIONS = [
    "silent_reschedule",
    "retry_scheduled",
    "retry_now",
    "do_not_retry",
    "reverify_and_reverse",
]

# Real-world skew: soft_decline dominates (70–90% of failures)
CAUSE_WEIGHTS = [0.05, 0.70, 0.10, 0.08, 0.07]

# ── Signal tables per cause ────────────────────────────────────────────────────

SIGNALS = {
    "notification_compliance_block": {
        "status_codes": ["FAILED", "MANDATE_REJECTED"],
        "bank_response_codes": [None],
        "npci_response_codes": ["U16", "U30", None],
        "notification_sent": False,  # notification not sent → always L1
    },
    "soft_decline": {
        "status_codes": ["FAILED", "DECLINED"],
        "bank_response_codes": ["51", "61", "65", "91", "96", None],
        "npci_response_codes": [None, "U68"],
    },
    "hard_decline": {
        "status_codes": ["FAILED", "INVALID_CARD", "DO_NOT_HONOUR"],
        "bank_response_codes": ["05", "12", "41", "43", "54", "62"],
        "npci_response_codes": [None],
    },
    "gateway_fault": {
        "status_codes": ["GATEWAY_ERROR", "TIMEOUT", "TECHNICAL_ERROR", "NETWORK_ERROR"],
        "bank_response_codes": [None, "96"],
        "npci_response_codes": [None],
    },
    "fraud_filter_block": {
        "status_codes": ["FAILED", "BLOCKED", "RISK_CHECK_FAILED"],
        "bank_response_codes": ["57", "59", "14", "93"],
        "npci_response_codes": [None, "U69"],
    },
}

BANKS = ["HDFC", "ICICI", "SBI", "AXIS", "KOTAK", "YES", "IDFC", None]

SYSTEM_PROMPT = """You are a payment-failure root-cause classifier for an Indian Razorpay mandate system.
Classify the given transaction into exactly ONE cause and ONE recommended_action.

Valid causes:
- notification_compliance_block
- soft_decline
- hard_decline
- gateway_fault
- fraud_filter_block

Valid actions:
- silent_reschedule
- retry_scheduled
- retry_now
- do_not_retry
- reverify_and_reverse

Respond ONLY with valid JSON, no markdown:
{"cause": "...", "recommended_action": "...", "confidence": 0.0–1.0, "reasoning": "1-2 sentences"}"""


def generate_transaction(cause: str) -> dict:
    """Generate a synthetic transaction with signals matching the given cause."""
    sig = SIGNALS[cause]

    status_code = random.choice(sig["status_codes"])
    bank_response_code = random.choice(sig["bank_response_codes"])
    npci_response_code = random.choice(sig.get("npci_response_codes", [None]))
    customer_bank = random.choice(BANKS)

    # Amount in paise: realistic distribution (₹100 to ₹200,000)
    amount = random.choices(
        [random.randint(10000, 100000), random.randint(100000, 5000000), random.randint(5000000, 20000000)],
        weights=[0.65, 0.30, 0.05]
    )[0]

    retry_count = random.choices([0, 1, 2, 3], weights=[0.55, 0.25, 0.15, 0.05])[0]

    now = datetime.now(timezone.utc)
    debit_scheduled_at = now + timedelta(hours=random.randint(1, 72))

    # For compliance blocks: notification not sent (or sent too late)
    if cause == "notification_compliance_block":
        mandate_notification_sent_at = None  # null → compliance block
    else:
        # Sent 25+ hours before debit → passes L1 → falls through to L2
        sent_delta = timedelta(hours=random.randint(25, 72))
        mandate_notification_sent_at = (debit_scheduled_at - sent_delta).isoformat()

    return {
        "gateway_transaction_id": f"gtxn_{random.randbytes(8).hex()}",
        "status_code": status_code,
        "bank_response_code": bank_response_code,
        "npci_response_code": npci_response_code,
        "amount": amount,
        "customer_bank": customer_bank,
        "retry_count_so_far": retry_count,
        "mandate_notification_sent_at": mandate_notification_sent_at,
        "debit_scheduled_at": debit_scheduled_at.isoformat(),
        "_synthetic_cause": cause,  # ground truth label (prefix _ = metadata)
    }


def label_with_groq(client: Groq, txn: dict) -> Optional[dict]:
    """Call Groq to label a transaction. Returns the label dict or None on failure."""
    payload = {
        "status_code": txn["status_code"],
        "bank_response_code": txn["bank_response_code"],
        "npci_response_code": txn["npci_response_code"],
        "amount_paise": txn["amount"],
        "customer_bank": txn["customer_bank"],
        "retry_count_so_far": txn["retry_count_so_far"],
        "has_mandate_notification": txn["mandate_notification_sent_at"] is not None,
    }

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload)},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()
        label = json.loads(raw)

        # Validate schema
        if label.get("cause") not in CAUSES:
            print(f"  [WARN] Invalid cause: {label.get('cause')} — skipping", file=sys.stderr)
            return None
        if label.get("recommended_action") not in ACTIONS:
            print(f"  [WARN] Invalid action: {label.get('recommended_action')} — skipping", file=sys.stderr)
            return None

        return label
    except Exception as e:
        print(f"  [ERROR] Groq call failed: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Generate labeled synthetic payment failure data")
    parser.add_argument("--count", type=int, default=500, help="Number of records to generate")
    parser.add_argument("--output", type=str, default="data/synthetic_labeled.jsonl", help="Output JSONL file path")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM labeling (heuristic labels only)")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("GROQ_API_KEY")
    use_llm = not args.no_llm and bool(api_key)

    if use_llm:
        client = Groq(api_key=api_key)
        print(f"✓ Groq client initialized (openai/gpt-oss-120b)")
    else:
        client = None
        print("⚠  Running without LLM (--no-llm or GROQ_API_KEY not set). Labels will be heuristic only.")

    print(f"Generating {args.count} records → {output_path}")
    written = 0
    skipped = 0

    with open(output_path, "w") as f:
        for i in range(args.count):
            # Sample cause according to real-world skew
            cause = random.choices(CAUSES, weights=CAUSE_WEIGHTS)[0]
            txn = generate_transaction(cause)

            if use_llm:
                label = label_with_groq(client, txn)
                if label is None:
                    skipped += 1
                    # Rate limit: Groq free tier allows ~30 req/min
                    time.sleep(0.1)
                    continue
                record = {**txn, **label}
            else:
                # Heuristic label = same as synthetic cause (for testing only)
                record = {**txn, "cause": cause, "recommended_action": "retry_scheduled", "confidence": 0.75, "reasoning": "Heuristic label."}

            f.write(json.dumps(record) + "\n")
            written += 1

            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{args.count} ({written} written, {skipped} skipped)")
                # Respect Groq free tier: 30 requests/min = 1 per 2s to be safe
                if use_llm:
                    time.sleep(1.5)

    print(f"\n✓ Done. Written: {written}, Skipped: {skipped}")
    print(f"  Output: {output_path.resolve()}")


if __name__ == "__main__":
    main()
