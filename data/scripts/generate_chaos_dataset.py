"""
generate_chaos_dataset.py

Domain-Driven Synthetic Dataset Generator for Razorpay Payment Failure Root-Cause Classification.

Research-backed chaos data covering:
  - ISO 8583 bank response codes (real-world distribution)
  - RBI E-mandate compliance violations (24-hour window)
  - Indian NPCI / UPI specific error codes
  - Gateway & network fault patterns
  - Fraud / risk filter patterns
  - Real-world noise: whitespace, missing fields, contradictory signals
  - Edge cases: retry storms, boundary timestamps, currency mismatches
"""

import csv
import random
import uuid
import math
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# ISO 8583 Bank Response Code Research
# Source: ISO 8583-1:1987, Mastercard/Visa decline code dictionaries,
#         NPCI documentation, RBI E-mandate circular 2021-2026.
# ---------------------------------------------------------------------------

ISO_8583 = {
    # Soft Declines (transient, retry-able)
    "51": ("soft_decline",        "retry_scheduled", "Insufficient funds"),
    "61": ("soft_decline",        "retry_scheduled", "Exceeds withdrawal amount limit"),
    "65": ("soft_decline",        "retry_scheduled", "Activity limit exceeded"),
    "75": ("soft_decline",        "retry_scheduled", "Allowable PIN tries exceeded - soft"),
    "91": ("soft_decline",        "retry_now",       "Issuer or switch inoperative"),
    "96": ("gateway_fault",       "retry_now",       "System malfunction"),
    "N7": ("soft_decline",        "retry_scheduled", "Decline for CVV2 failure"),

    # Hard Declines (permanent, do not retry)
    "05": ("hard_decline",        "do_not_retry",    "Do not honour"),
    "12": ("hard_decline",        "do_not_retry",    "Invalid transaction"),
    "14": ("hard_decline",        "do_not_retry",    "Invalid card number"),
    "41": ("hard_decline",        "do_not_retry",    "Lost card - pick up"),
    "43": ("hard_decline",        "do_not_retry",    "Stolen card - pick up"),
    "54": ("hard_decline",        "do_not_retry",    "Expired card"),
    "62": ("hard_decline",        "do_not_retry",    "Restricted card"),
    "78": ("hard_decline",        "do_not_retry",    "Card not yet active"),
    "04": ("hard_decline",        "do_not_retry",    "Pick up card - no fraud"),
    "36": ("hard_decline",        "do_not_retry",    "Restricted card - regional"),

    # Fraud / Risk Filter Blocks
    "57": ("fraud_filter_block",  "do_not_retry",    "Transaction not permitted - fraud risk"),
    "59": ("fraud_filter_block",  "reverify_and_reverse", "Suspected fraud"),
    "63": ("fraud_filter_block",  "do_not_retry",    "Security violation"),
    "93": ("fraud_filter_block",  "reverify_and_reverse", "Transaction cannot be completed - violation"),
    "34": ("fraud_filter_block",  "reverify_and_reverse", "Suspected fraud - AML flag"),
    "06": ("fraud_filter_block",  "do_not_retry",    "Error - possible fraud indicator"),

    # Gateway / Network Faults
    "68": ("gateway_fault",       "retry_now",       "Response received too late"),
    "82": ("gateway_fault",       "retry_now",       "Time-out at issuer"),
    "88": ("gateway_fault",       "retry_now",       "Cryptographic failure - gateway"),
    "XX": ("gateway_fault",       "retry_now",       "Unknown network error"),
}

# Indian NPCI UPI / RuPay specific error codes (internal to India's payment stack)
NPCI_CODES = {
    # Soft Declines
    "U30": ("soft_decline",       "retry_scheduled", "NPCI: Debit account limit exceeded"),
    "U31": ("soft_decline",       "retry_scheduled", "NPCI: Credit account limit exceeded"),
    "YF": ("soft_decline",        "retry_scheduled", "NPCI: Payer UPI PIN incorrect"),
    "ZA": ("soft_decline",        "retry_scheduled", "NPCI: Account temporarily blocked"),
    "ZD": ("soft_decline",        "retry_scheduled", "NPCI: Insufficient funds in VPA"),

    # Fraud Flags (high-value or unusual pattern)
    "U69": ("fraud_filter_block", "reverify_and_reverse", "NPCI: Risk threshold breach - potential fraud"),
    "U16": ("fraud_filter_block", "do_not_retry",    "NPCI: Transaction blocked by issuing bank - risk"),
    "U78": ("fraud_filter_block", "do_not_retry",    "NPCI: VPA blocked due to fraud complaints"),

    # Compliance / Mandate Violations
    "BT": ("notification_compliance_block", "silent_reschedule", "NPCI: Pre-debit notification not sent"),
    "U17": ("notification_compliance_block","silent_reschedule",  "NPCI: Mandate notification timing violation"),

    # Hard Declines
    "U13": ("hard_decline",       "do_not_retry",    "NPCI: Account closed"),
    "U28": ("hard_decline",       "do_not_retry",    "NPCI: Account does not exist"),

    # Gateway Faults
    "U09": ("gateway_fault",      "retry_now",       "NPCI: Transaction timed out at acquirer"),
    "U90": ("gateway_fault",      "retry_now",       "NPCI: Gateway timeout - no issuer response"),
    None:  ("soft_decline",       "retry_scheduled", None),   # missing NPCI code
}

# Gateway status codes (from Razorpay's own webhook payload)
GATEWAY_STATUS_CODES = {
    "FAILED":                "FAILED",
    "TIMEOUT":               "TIMEOUT",
    "GATEWAY_ERROR":         "GATEWAY_ERROR",
    "INVALID_CARD":          "INVALID_CARD",
    "BLOCKED":               "BLOCKED",
    "RISK_CHECK_FAILED":     "RISK_CHECK_FAILED",
    "DO_NOT_HONOUR":         "DO_NOT_HONOUR",
    "MANDATE_REJECTED":      "MANDATE_REJECTED",
    "TECHNICAL_ERROR":       "TECHNICAL_ERROR",
    "NETWORK_ERROR":         "NETWORK_ERROR",
    "AUTHENTICATION_FAILED": "AUTHENTICATION_FAILED",
    "CARD_EXPIRED":          "CARD_EXPIRED",
    "INSUFFICIENT_FUNDS":    "INSUFFICIENT_FUNDS",
    "LIMIT_EXCEEDED":        "LIMIT_EXCEEDED",
    "CANCELLED":             "CANCELLED",
}

# Bank names (Indian banks & common international acquirers)
INDIAN_BANKS = [
    "HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Mahindra Bank",
    "Yes Bank", "Punjab National Bank", "Bank of Baroda", "Canara Bank",
    "Union Bank of India", "IndusInd Bank", "Federal Bank", "IDBI Bank",
    "UCO Bank", "Bank of India", "RBL Bank", "Bandhan Bank", "DCB Bank",
    "Karnataka Bank", "Karur Vysya Bank", "City Union Bank",
]

CARD_NETWORKS = ["Visa", "Mastercard", "RuPay", "American Express", "Diners Club"]
CARD_COUNTRIES = ["IN", "US", "GB", "SG", "AE", "AU", "CA", "DE", "FR", "JP"]
CURRENCIES = ["INR", "USD", "GBP", "EUR", "SGD", "AED", "AUD"]
AUTH_METHODS = ["OTP", "3DS", "PIN", "Biometric", "None", "Silent"]

NOISE_BANK_CODES = ["UNKNOWN_999", "  ", "", "ERRTX", "N/A", "NETBK_FAIL", "PGWAY_503"]
NOISE_STATUS = ["  TIMEOUT  ", "failed", "FAIL", "time_out", "NETWORK-ERR", "err_gateway"]

AMOUNTS_PAISE = (
    [500, 1000, 2000, 5000, 10000] * 20 +       # common low amounts
    [50000, 100000, 200000, 500000] * 10 +       # medium amounts
    [1000000, 2000000, 5000000] * 3 +            # high value (fraud magnets)
    [1, 0, 99] * 5                               # edge: zero and tiny amounts
)

# ---------------------------------------------------------------------------
# Scenario weights: how often each root cause appears in the real world.
# Based on Razorpay public blog + industry research data.
# ---------------------------------------------------------------------------
SCENARIO_WEIGHTS = {
    "soft_decline":                  0.42,   # Most common: insufficient funds, limits
    "hard_decline":                  0.22,   # Invalid / expired cards
    "gateway_fault":                 0.18,   # Network / timeout issues
    "notification_compliance_block": 0.10,   # RBI mandate violations (India-specific)
    "fraud_filter_block":            0.08,   # Fraud risk blocks
}

DEBIT_DATE = datetime(2026, 8, 28, 10, 0, 0, tzinfo=timezone.utc)


def weighted_choice(weights_dict):
    keys = list(weights_dict.keys())
    weights = list(weights_dict.values())
    return random.choices(keys, weights=weights, k=1)[0]


def random_timestamp_before(ref, min_hours=25, max_hours=72):
    delta_hours = random.uniform(min_hours, max_hours)
    return ref - timedelta(hours=delta_hours)


def compliance_violation_timestamp():
    """Return a notification timestamp that is < 24 hours before debit (violation)."""
    delta_hours = random.uniform(0.5, 23.5)
    return DEBIT_DATE - timedelta(hours=delta_hours)


def build_row(i, cause):
    txn_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 10000))
    amount = random.choice(AMOUNTS_PAISE)
    card_network = random.choice(CARD_NETWORKS)
    card_country = random.choice(CARD_COUNTRIES)
    currency = "INR" if card_country == "IN" else random.choice(CURRENCIES)
    bank = random.choice(INDIAN_BANKS)
    retry_count = random.choices([0, 1, 2, 3, 5, 10], weights=[50, 20, 15, 8, 5, 2])[0]
    auth_method = random.choice(AUTH_METHODS)
    is_recurring = random.choices(["Y", "N"], weights=[60, 40])[0]  # mandate-heavy product

    # --- Real-world noise injected with 5% probability -------------------------
    add_noise = random.random() < 0.05

    npci_code = None
    bank_code = None
    status_code = "FAILED"
    notification_sent_at = None
    debit_scheduled_at = DEBIT_DATE.isoformat()
    recommended_action = "retry_scheduled"
    reasoning = ""

    if cause == "notification_compliance_block":
        status_code = random.choice(["FAILED", "MANDATE_REJECTED"])
        # 70% missing notification, 30% sent too late (boundary violation)
        if random.random() < 0.70:
            notification_sent_at = None
            reasoning = "Mandate pre-debit notification was never sent. RBI E-mandate 2026 requires 24h prior notice."
        else:
            notification_sent_at = compliance_violation_timestamp().isoformat()
            reasoning = "Pre-debit notification sent within 24-hour window. RBI violation."
        npci_code = random.choice(["BT", "U17", None])
        recommended_action = "silent_reschedule"

    elif cause == "soft_decline":
        iso_candidates = [k for k, v in ISO_8583.items() if v[0] == "soft_decline"]
        bank_code = random.choice(iso_candidates) if not add_noise else random.choice(NOISE_BANK_CODES)
        status_code = random.choice(["FAILED", "INSUFFICIENT_FUNDS", "LIMIT_EXCEEDED"])
        npci_code = random.choice([k for k in NPCI_CODES if NPCI_CODES[k][0] == "soft_decline" and k is not None] + [None, None])
        notification_sent_at = random_timestamp_before(DEBIT_DATE).isoformat()
        recommended_action = random.choice(["retry_scheduled", "retry_now"])
        reasoning = ISO_8583.get(bank_code, ("", "", "Unknown soft decline"))[2]

    elif cause == "hard_decline":
        iso_candidates = [k for k, v in ISO_8583.items() if v[0] == "hard_decline"]
        bank_code = random.choice(iso_candidates) if not add_noise else random.choice(["INVALID_CARD_NUM", "EXPIRED", "  "])
        status_code = random.choice(["INVALID_CARD", "DO_NOT_HONOUR", "CARD_EXPIRED", "FAILED"])
        npci_code = random.choice([k for k in NPCI_CODES if NPCI_CODES[k][0] == "hard_decline" and k is not None] + [None, None])
        notification_sent_at = random_timestamp_before(DEBIT_DATE).isoformat()
        recommended_action = "do_not_retry"
        reasoning = ISO_8583.get(bank_code, ("", "", "Permanent card-level decline"))[2]

    elif cause == "gateway_fault":
        iso_candidates = [k for k, v in ISO_8583.items() if v[0] == "gateway_fault"]
        bank_code = random.choice(iso_candidates + [None, None, None])  # often missing in gateway faults
        if add_noise:
            status_code = random.choice(NOISE_STATUS)
        else:
            status_code = random.choice(["TIMEOUT", "GATEWAY_ERROR", "NETWORK_ERROR", "TECHNICAL_ERROR", "FAILED"])
        npci_code = random.choice([k for k in NPCI_CODES if NPCI_CODES[k][0] == "gateway_fault" and k is not None] + [None, None])
        notification_sent_at = random_timestamp_before(DEBIT_DATE).isoformat()
        recommended_action = "retry_now"
        reasoning = "Gateway or network-level failure. Issuer was not reached."

    elif cause == "fraud_filter_block":
        iso_candidates = [k for k, v in ISO_8583.items() if v[0] == "fraud_filter_block"]
        bank_code = random.choice(iso_candidates)
        status_code = random.choice(["BLOCKED", "RISK_CHECK_FAILED", "FAILED"])
        npci_code = random.choice([k for k in NPCI_CODES if NPCI_CODES[k][0] == "fraud_filter_block" and k is not None] + [None])
        notification_sent_at = random_timestamp_before(DEBIT_DATE).isoformat()
        # High-value amounts are more common in fraud
        amount = random.choice([500000, 1000000, 2000000, 5000000] + [amount])
        recommended_action = random.choice(["do_not_retry", "reverify_and_reverse"])
        reasoning = ISO_8583.get(bank_code, ("", "", "Fraud/risk flag from issuer"))[2]

    # Inject edge case: contradictory signals (gateway status but fraud bank code, 2% chance)
    if random.random() < 0.02 and cause != "notification_compliance_block":
        status_code = random.choice(["GATEWAY_ERROR", "TIMEOUT"])
        bank_code = random.choice(["57", "59", "34"])
        # The LLM should resolve this → cause stays as originally assigned

    return {
        "transaction_id":                txn_id,
        "event_type":                    "payment.failed",
        "timestamp":                     ts.isoformat(),
        "status_code":                   status_code,
        "bank_response_code":            bank_code if bank_code else "",
        "npci_response_code":            npci_code if npci_code else "",
        "amount_paise":                  amount,
        "currency":                      currency,
        "card_network":                  card_network,
        "card_country_code":             card_country,
        "issuer_bank":                   bank,
        "retry_count_so_far":            retry_count,
        "is_recurring_transaction":      is_recurring,
        "cardholder_auth_method":        auth_method,
        "mandate_notification_sent_at":  notification_sent_at if notification_sent_at else "",
        "debit_scheduled_at":            debit_scheduled_at,
        # Ground-truth labels for supervised ML training
        "label_cause":                   cause,
        "label_recommended_action":      recommended_action,
        "label_reasoning":               reasoning,
    }


def generate(n=50000, output_path=""):
    rows = []
    for i in range(n):
        cause = weighted_choice(SCENARIO_WEIGHTS)
        rows.append(build_row(i, cause))

    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Print distribution stats
    from collections import Counter
    dist = Counter(r["label_cause"] for r in rows)
    print(f"\nGenerated {n:,} rows → {output_path}")
    print("\nLabel Distribution:")
    for cause, count in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  {cause:<40} {count:>6} rows  ({count/n*100:.1f}%)")
    
    noise_count = sum(1 for r in rows if r["bank_response_code"] in [v.strip() for v in NOISE_BANK_CODES] or "  " in r["status_code"])
    print(f"\n  Noisy / malformed rows injected: ~{noise_count}")
    print("  Contradictory signal rows injected: ~2% of non-compliance rows")


if __name__ == "__main__":
    import os, sys

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    out_dir = os.path.join(os.path.dirname(__file__), "..", "payment_failures")
    os.makedirs(out_dir, exist_ok=True)
    
    output_path = os.path.join(out_dir, "razorpay_payment_failures_synthetic.csv")
    generate(n=n, output_path=output_path)
