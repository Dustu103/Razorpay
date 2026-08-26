"""
validate_pipeline.py
────────────────────
Loads the generated synthetic_labeled.jsonl dataset and computes:
  - Per-cause accuracy (raw %)
  - Cost-weighted confusion matrix (as per TDD §3.2)
  - Flag: which cause/action pairs fail the per-action confidence thresholds

Usage:
  python scripts/validate_pipeline.py --data data/synthetic_labeled.jsonl

The cost matrix penalizes dangerous misclassifications more than cheap ones.
See TDD §3 for the rationale.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
import sys


# ── Per-action confidence thresholds (mirrors Go models.go) ──────────────────

THRESHOLDS = {
    "reverify_and_reverse": 0.85,
    "retry_scheduled":      0.55,
    "retry_now":            0.55,
    "do_not_retry":         0.55,
    "silent_reschedule":    1.0,  # deterministic — always confident
}

# ── Cost matrix: cost[predicted][actual] ──────────────────────────────────────
# Higher value = more expensive mistake.
# Based on TDD §3 reasoning (false declines cost 13x more than fraud losses).

CAUSES = [
    "notification_compliance_block",
    "soft_decline",
    "hard_decline",
    "gateway_fault",
    "fraud_filter_block",
]

COST_MATRIX = {
    # predicted →
    "notification_compliance_block": {
        "notification_compliance_block": 0,
        "soft_decline": 8,   # missed compliance = RBI penalty risk
        "hard_decline": 8,
        "gateway_fault": 8,
        "fraud_filter_block": 8,
    },
    "soft_decline": {
        "notification_compliance_block": 5,
        "soft_decline": 0,
        "hard_decline": 10,  # calling hard_decline soft = abandoning recoverable revenue
        "gateway_fault": 3,
        "fraud_filter_block": 7,
    },
    "hard_decline": {
        "notification_compliance_block": 5,
        "soft_decline": 2,   # wasted retry, low cost
        "hard_decline": 0,
        "gateway_fault": 2,
        "fraud_filter_block": 5,
    },
    "gateway_fault": {
        "notification_compliance_block": 4,
        "soft_decline": 3,
        "hard_decline": 4,
        "gateway_fault": 0,
        "fraud_filter_block": 6,  # retry_now on a blocked card = velocity flags
    },
    "fraud_filter_block": {
        "notification_compliance_block": 4,
        "soft_decline": 9,   # missing fraud = customer loss or fraud pass-through
        "hard_decline": 6,
        "gateway_fault": 7,
        "fraud_filter_block": 0,
    },
}


def load_records(path: str) -> list:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def validate(records: list):
    total = len(records)
    correct = 0
    total_cost = 0.0
    below_threshold = 0

    cause_correct = defaultdict(int)
    cause_total = defaultdict(int)
    confusion = defaultdict(lambda: defaultdict(int))  # confusion[actual][predicted]

    for r in records:
        actual = r.get("_synthetic_cause", r.get("cause"))
        predicted = r.get("cause")
        confidence = r.get("confidence", 0.0)
        action = r.get("recommended_action", "")

        if not actual or not predicted:
            continue

        cause_total[actual] += 1

        if predicted == actual:
            correct += 1
            cause_correct[actual] += 1

        confusion[actual][predicted] += 1

        # Cost-weighted error
        cost = COST_MATRIX.get(predicted, {}).get(actual, 5)
        total_cost += cost

        # Threshold check
        threshold = THRESHOLDS.get(action, 0.55)
        if confidence < threshold:
            below_threshold += 1

    print("=" * 60)
    print("PIPELINE VALIDATION REPORT")
    print("=" * 60)
    print(f"\nTotal records:   {total}")
    print(f"Overall accuracy: {correct/total*100:.1f}%")
    print(f"Avg cost per txn: {total_cost/total:.2f} (lower = better)")
    print(f"Below threshold:  {below_threshold} ({below_threshold/total*100:.1f}%) → these go to Layer 3")

    print("\n── Per-Cause Accuracy ────────────────────────────────────")
    for cause in CAUSES:
        t = cause_total[cause]
        c = cause_correct[cause]
        if t == 0:
            print(f"  {cause:<40} N/A")
        else:
            pct = c / t * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            status = "✓" if pct >= 80 else "✗"
            print(f"  {status} {cause:<40} {pct:5.1f}% [{bar}] ({c}/{t})")

    print("\n── Cost-Weighted Confusion Matrix ────────────────────────")
    header = f"{'':>32}" + "".join(f"{c[:8]:>10}" for c in CAUSES)
    print(header)
    for actual in CAUSES:
        row = f"  {actual[:30]:>30}"
        for predicted in CAUSES:
            count = confusion[actual][predicted]
            row += f"{count:>10}"
        print(row)

    print("\n── Threshold Compliance ──────────────────────────────────")
    action_below = defaultdict(int)
    action_total = defaultdict(int)
    for r in records:
        action = r.get("recommended_action", "")
        confidence = r.get("confidence", 0.0)
        action_total[action] += 1
        threshold = THRESHOLDS.get(action, 0.55)
        if confidence < threshold:
            action_below[action] += 1

    for action, threshold in THRESHOLDS.items():
        total_a = action_total[action]
        below_a = action_below[action]
        if total_a == 0:
            continue
        pct_fallback = below_a / total_a * 100
        status = "⚠ " if pct_fallback > 20 else "✓ "
        print(f"  {status}{action:<30} threshold={threshold:.2f}  fallback={pct_fallback:.1f}% ({below_a}/{total_a})")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/synthetic_labeled.jsonl")
    args = parser.parse_args()

    path = Path(args.data)
    if not path.exists():
        print(f"[ERROR] Data file not found: {path}", file=sys.stderr)
        print("Run generate_synthetic_data.py first.", file=sys.stderr)
        sys.exit(1)

    records = load_records(str(path))
    print(f"Loaded {len(records)} records from {path}")
    validate(records)


if __name__ == "__main__":
    main()
