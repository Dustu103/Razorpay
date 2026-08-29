"""
HuggingFace Dataset Ingestion + Pipeline Refresh
=================================================
Dataset:  MattMMarketing/chargeback-reason-codes
URL:      https://huggingface.co/datasets/MattMMarketing/chargeback-reason-codes

What this script does (no manual download required):
  1. Downloads chargeback-reason-codes.csv directly from HuggingFace
  2. Maps winnability_label → numeric base_win_rate
  3. Normalises network codes to our internal format (visa_10.4, mc_4837, etc.)
  4. Saves raw reference file to datasets/chargeback/source_data/
  5. Rewrites backend/chargeback-service/reason_code_map.py with all 64 codes
  6. Rewrites datasets/scripts/generate_chargeback_data.py with real base rates
  7. Re-runs: generate → clean → train pipeline

Run inside the chargeback-service container:
  docker compose run --rm chargeback-service python /app/datasets/scripts/ingest_hf_reason_codes.py

Or locally (needs: pip install requests pandas numpy scikit-learn xgboost lightgbm shap imbalanced-learn):
  python datasets/scripts/ingest_hf_reason_codes.py
"""

import requests
import pandas as pd
import os
import sys
import json
import textwrap

# ── Config ────────────────────────────────────────────────────────────────────
HF_CSV_URL = (
    "https://huggingface.co/datasets/MattMMarketing/chargeback-reason-codes"
    "/resolve/main/chargeback-reason-codes.csv"
)

# Detect container vs host environment
# In container: WORKDIR=/app, reason_code_map.py is at /app/reason_code_map.py
# On host: it lives at backend/chargeback-service/reason_code_map.py
IN_CONTAINER = os.path.exists("/app/reason_code_map.py")

SAVE_DIR      = "datasets/chargeback/source_data"
RAW_CSV       = f"{SAVE_DIR}/chargeback-reason-codes.csv"

# Write to container path + always write a backup to mounted volume for host sync
REASON_MAP_PATH         = "/app/reason_code_map.py" if IN_CONTAINER else "backend/chargeback-service/reason_code_map.py"
REASON_MAP_VOLUME_COPY  = "datasets/chargeback/source_data/reason_code_map.py"  # persisted
GENERATE_PATH           = "datasets/scripts/generate_chargeback_data.py"

# Winnability label → base win rate (probability the merchant wins IF they fight)
WINNABILITY_TO_RATE = {
    "highly winnable":             0.80,
    "winnable with strong evidence": 0.62,
    "often winnable":              0.50,
    "difficult to win":            0.20,
    "rarely winnable":             0.10,
}

# Network name normalisation — HF uses full names, we use short keys internally
NETWORK_PREFIX = {
    "visa":             "visa",
    "mastercard":       "mc",
    "amex":             "amex",
    "american express": "amex",
    "discover":         "disc",
}

# ── Evidence keyword → our internal field ─────────────────────────────────────
EVIDENCE_KEYWORDS = {
    "avs":                    "has_avs_cvv_match",
    "cvv":                    "has_avs_cvv_match",
    "cvc":                    "has_avs_cvv_match",
    "cid":                    "has_avs_cvv_match",
    "3d secure":              "has_3ds_auth",
    "device fingerprint":     "has_ip_device_fingerprint",
    "ip address":             "has_ip_device_fingerprint",
    "delivery":               "has_delivery_proof",
    "tracking":               "has_delivery_proof",
    "signed":                 "has_signed_receipt",
    "receipt":                "has_signed_receipt",
    "communication":          "has_prior_comms",
    "cancellation policy":    "has_prior_comms",
    "login":                  "has_usage_logs",
    "usage":                  "has_usage_logs",
    "access log":             "has_usage_logs",
}

FRAUD_CODE_KEYWORDS = {"fraud", "unauthorized", "not authorize", "counterfeit", "lost", "stolen"}


def download_csv() -> pd.DataFrame:
    print(f"[1/6] Downloading dataset from HuggingFace...")
    print(f"      {HF_CSV_URL}")
    r = requests.get(HF_CSV_URL, timeout=30)
    r.raise_for_status()
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(RAW_CSV, "wb") as f:
        f.write(r.content)
    df = pd.read_csv(RAW_CSV)
    print(f"      ✓ {len(df)} reason codes downloaded: "
          f"{dict(df['network'].value_counts())}")
    return df


def map_winnability(label: str) -> float:
    label = label.strip().lower()
    for key, rate in WINNABILITY_TO_RATE.items():
        if key in label:
            return rate
    return 0.50  # default


def infer_evidence(key_evidence_text: str) -> list[str]:
    """
    Parse the free-text key_evidence field and return a list of
    our internal boolean evidence field names.
    """
    text = key_evidence_text.lower() if isinstance(key_evidence_text, str) else ""
    found = set()
    for kw, field in EVIDENCE_KEYWORDS.items():
        if kw in text:
            found.add(field)
    return sorted(found)


def make_internal_code(network: str, code: str) -> str:
    prefix = NETWORK_PREFIX.get(network.strip().lower(), network.lower())
    # Clean the code: replace spaces/slashes with underscores, lowercase
    clean_code = code.strip().replace(" ", "_").replace("/", "_").replace(".", ".")
    return f"{prefix}_{clean_code}"


def build_reason_code_dict(df: pd.DataFrame) -> dict:
    codes = {}
    for _, row in df.iterrows():
        network     = row["network"].strip()
        code_raw    = str(row["code"]).strip()
        internal_id = make_internal_code(network, code_raw)

        base_rate    = map_winnability(str(row.get("winnability_label", "")))
        deadline     = int(str(row.get("response_deadline", "30 days")).split()[0])
        required_ev  = infer_evidence(str(row.get("key_evidence", "")))

        # Build checklist from key_evidence (split on ";")
        ev_raw = str(row.get("key_evidence", ""))
        checklist = [item.strip() for item in ev_raw.split(";") if item.strip()][:4]

        meaning = str(row.get("plain_english_meaning", "")).strip()
        is_fraud = any(kw in meaning.lower() for kw in FRAUD_CODE_KEYWORDS)

        # Normalise network to short key (visa / mc / amex / disc)
        net_short = NETWORK_PREFIX.get(network.lower(), network.lower())

        codes[internal_id] = {
            "network":           net_short,   # short key — used for bucket filtering
            "title":             str(row.get("title", "")).strip(),
            "winnability":       str(row.get("winnability_label", "")).strip(),
            "base_win_rate":     base_rate,
            "deadline_days":     deadline,
            "required_evidence": required_ev,
            "checklist":         checklist,
            "is_fraud_code":     is_fraud,
        }
    return codes


def write_reason_code_map(codes: dict):
    print(f"[3/6] Writing reason_code_map.py ({len(codes)} codes)...")
    print(f"      Container: {IN_CONTAINER} → {REASON_MAP_PATH}")
    lines = [
        "# AUTO-GENERATED by ingest_hf_reason_codes.py",
        "# Source: MattMMarketing/chargeback-reason-codes (HuggingFace)",
        "# License: CC BY 4.0 — ChargebackKit (chargebackkit.app/reason-codes)",
        "# DO NOT EDIT MANUALLY — re-run ingest_hf_reason_codes.py to refresh",
        "",
        "REASON_CODE_EVIDENCE_MAP = {",
    ]
    for code_id, meta in codes.items():
        lines.append(f'    "{code_id}": {{')
        lines.append(f'        "network":           "{meta["network"]}",')
        lines.append(f'        "title":             "{meta["title"]}",')
        lines.append(f'        "winnability":       "{meta["winnability"]}",')
        lines.append(f'        "base_win_rate":      {meta["base_win_rate"]},')
        lines.append(f'        "deadline_days":      {meta["deadline_days"]},')
        lines.append(f'        "is_fraud_code":      {str(meta["is_fraud_code"])},')
        lines.append(f'        "required_evidence": {json.dumps(meta["required_evidence"])},')
        lines.append(f'        "checklist":         {json.dumps(meta["checklist"])},')
        lines.append(f'    }},')
    lines.append("}")
    lines.append("")
    content = "\n".join(lines)
    os.makedirs(os.path.dirname(REASON_MAP_PATH) or ".", exist_ok=True)
    with open(REASON_MAP_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    # Also save to mounted volume so host can sync it
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(REASON_MAP_VOLUME_COPY, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"      ✓ Written {len(codes)} entries")
    print(f"      ✓ Backup saved to {REASON_MAP_VOLUME_COPY}")


def write_generate_script(codes: dict):
    """
    Rewrite generate_chargeback_data.py using the real HF base rates.
    """
    print(f"[4/6] Rewriting {GENERATE_PATH} with real base win rates...")

    # Build the REASON_CODES dict string
    rc_lines = []
    for code_id, meta in codes.items():
        required_json = json.dumps(meta["required_evidence"])
        rc_lines.append(
            f'    "{code_id}": {{"network": "{meta["network"]}", '
            f'"base": {meta["base_win_rate"]}, '
            f'"is_fraud": {str(meta["is_fraud_code"])}, '
            f'"required": {required_json}}},'
        )
    rc_block = "\n".join(rc_lines)

    # Derive network buckets using the normalised short keys
    visa_codes  = [c for c, m in codes.items() if m["network"] == "visa"]
    mc_codes    = [c for c, m in codes.items() if m["network"] == "mc"]
    amex_codes  = [c for c, m in codes.items() if m["network"] == "amex"]
    disc_codes  = [c for c, m in codes.items() if m["network"] == "disc"]
    # Approximate market share probs (Visa 40%, MC 30%, Amex 20%, Discover 10%)
    net_probs = f"[0.40, 0.30, 0.20, 0.10]"
    net_names = '["visa", "mastercard", "amex", "discover"]'

    script = f'''\
"""
Step 1: Synthetic Chargeback Dispute Dataset Generator
=======================================================
AUTO-GENERATED by ingest_hf_reason_codes.py
Dataset source: MattMMarketing/chargeback-reason-codes (HuggingFace CC BY 4.0)

Base win rates are derived from the real winnability_label field:
  "Highly winnable"              → 0.80
  "Winnable with strong evidence"→ 0.62
  "Often winnable"               → 0.50

Generates {5000} labeled chargeback dispute records across Visa, MC, Amex, Discover.
"""

import numpy as np
import pandas as pd
import math
import random
import os

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

N_SAMPLES = 5000

REASON_CODES = {{
{rc_block}
}}

FRAUD_CODES = {{k for k, v in REASON_CODES.items() if v["is_fraud"]}}

VISA_CODES  = [k for k, v in REASON_CODES.items() if v["network"] == "visa"]
MC_CODES    = [k for k, v in REASON_CODES.items() if v["network"] == "mc"]
AMEX_CODES  = [k for k, v in REASON_CODES.items() if v["network"] == "amex"]
DISC_CODES  = [k for k, v in REASON_CODES.items() if v["network"] == "disc"]

MERCHANT_CATEGORIES = ["ecommerce", "saas", "travel", "fintech", "retail", "healthcare"]


def sample_reason_code() -> str:
    network = np.random.choice(["visa", "mc", "amex", "disc"], p=[0.40, 0.30, 0.20, 0.10])
    if   network == "visa": return random.choice(VISA_CODES)
    elif network == "mc":   return random.choice(MC_CODES)
    elif network == "amex": return random.choice(AMEX_CODES)
    else:                   return random.choice(DISC_CODES)


def compute_evidence_completeness(row: dict, required: list) -> int:
    if not required:
        return 2
    present = sum(1 for r in required if row.get(r, 0) == 1)
    if present == 0:               return 0
    elif present < len(required):  return 1
    else:                          return 2


def compute_label(row: dict) -> int:
    code = row["reason_code"]
    meta = REASON_CODES[code]
    base = meta["base"]

    # Start score from the real HF base rate
    S = base * 5.0   # scale into sigmoid space so 0.80 → S~4, 0.50 → S~2.5

    # Evidence completeness bonus/penalty
    S += (row["evidence_completeness_score"] - 1) * 1.5  # 0→-1.5, 1→0, 2→+1.5

    # 3DS liability shift for fraud codes
    if row["has_3ds_auth"] == 1 and code in FRAUD_CODES:
        S += 2.0

    # CE 3.0 full match bonus for Visa 10.4 equivalent codes
    if meta["is_fraud"] and meta["network"] == "visa":
        if row["has_ip_device_fingerprint"] == 1 and row["has_avs_cvv_match"] == 1:
            S += 1.5
        else:
            S -= 1.0

    # Repeat dispute penalty (friendly fraud signal)
    if row["repeat_dispute_count"] >= 2:
        S -= 1.2 * math.sqrt(row["repeat_dispute_count"])

    # Deadline pressure
    if row["days_remaining"] <= 2:
        S -= 1.5
    elif row["days_remaining"] <= 5:
        S -= 0.5

    # Staleness penalty
    if row["days_since_transaction"] > 90:
        S -= 1.0

    # High-value issuer scrutiny
    if row["transaction_amount_inr"] > 100000:
        S -= 0.5

    p_win = 1 / (1 + math.exp(-(S - 2.5)))
    return 1 if random.random() < p_win else 0


def generate_dataset(n: int) -> pd.DataFrame:
    records = []
    for _ in range(n):
        code = sample_reason_code()
        meta = REASON_CODES[code]

        row = {{
            "reason_code":               code,
            "network":                   meta["network"],
            "has_3ds_auth":              np.random.binomial(1, 0.65),
            "has_delivery_proof":        np.random.binomial(1, 0.55),
            "has_avs_cvv_match":         np.random.binomial(1, 0.70),
            "has_ip_device_fingerprint": np.random.binomial(1, 0.60),
            "has_prior_comms":           np.random.binomial(1, 0.45),
            "has_signed_receipt":        np.random.binomial(1, 0.30),
            "has_usage_logs":            np.random.binomial(1, 0.40),
            "days_remaining":            np.random.randint(1, 46),
            "days_since_transaction":    np.random.randint(1, 121),
            "repeat_dispute_count":      int(np.random.choice(
                                            [0, 1, 2, 3, 4, 5, 8],
                                            p=[0.55, 0.20, 0.10, 0.07, 0.04, 0.02, 0.02]
                                        )),
            "transaction_amount_inr":    round(np.random.exponential(scale=8000) + 100, 2),
            "merchant_category":         random.choice(MERCHANT_CATEGORIES),
        }}

        row["evidence_completeness_score"] = compute_evidence_completeness(row, meta["required"])
        row["outcome"] = compute_label(row)
        records.append(row)

    return pd.DataFrame(records)


if __name__ == "__main__":
    print(f"Generating {{N_SAMPLES}} synthetic chargeback records...")
    print(f"  Networks covered: Visa, Mastercard, Amex, Discover")
    print(f"  Reason codes:     {{len(REASON_CODES)}} (sourced from HuggingFace MattMMarketing dataset)")
    df = generate_dataset(N_SAMPLES)

    os.makedirs("datasets/chargeback", exist_ok=True)
    df.to_csv("datasets/chargeback/chargeback_raw.csv", index=False)

    print(f"\\nDataset saved: datasets/chargeback/chargeback_raw.csv")
    print(f"Shape: {{df.shape}}")
    print(f"\\nOverall win rate: {{df['outcome'].mean():.1%}}")
    print(f"\\nWin rate by network:")
    print(df.groupby("network")["outcome"].agg(["count", "mean"]).round(3))
    print(f"\\nWin rate by reason_code (bottom 5):")
    print(df.groupby("reason_code")["outcome"].mean().sort_values().head(5).round(3))
    print(f"\\nWin rate by reason_code (top 5):")
    print(df.groupby("reason_code")["outcome"].mean().sort_values().tail(5).round(3))
'''

    with open(GENERATE_PATH, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"      ✓ Written with {len(codes)} reason codes, 4 networks")


def run_pipeline():
    """Run generate → clean → train in sequence."""
    import subprocess

    steps = [
        ("Generate synthetic data",  ["python", GENERATE_PATH]),
        ("Clean & feature-engineer", ["python", "datasets/scripts/clean_chargeback_data.py"]),
        ("Train 5-model ensemble",   ["python", "datasets/scripts/train_chargeback_model.py"]),
    ]

    for label, cmd in steps:
        print(f"\n[{'5' if 'Generate' in label else '6' if 'Train' in label else '5'}/6] {label}...")
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"      ✗ Step failed: {label}")
            sys.exit(1)
        print(f"      ✓ Done")


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("  HuggingFace Chargeback Reason Code Ingestion Pipeline")
    print("  Dataset: MattMMarketing/chargeback-reason-codes (CC BY 4.0)")
    print("=" * 65)

    # 1. Download
    df = download_csv()

    # 2. Parse + map
    print(f"[2/6] Parsing winnability labels and evidence fields...")
    codes = build_reason_code_dict(df)
    print(f"      ✓ {len(codes)} codes parsed")
    print(f"      Base rate distribution:")
    from collections import Counter
    rates = Counter(v["base_win_rate"] for v in codes.values())
    for rate, count in sorted(rates.items(), reverse=True):
        print(f"        {rate:.0%}  → {count} codes")

    # 3. Rewrite reason_code_map.py
    write_reason_code_map(codes)

    # 4. Rewrite generate_chargeback_data.py
    write_generate_script(codes)

    # 5 + 6. Re-run full pipeline
    print(f"\n[5/6] Running generate → clean → train pipeline...")
    run_pipeline()

    print("\n" + "=" * 65)
    print("  ✅ Ingestion complete!")
    print(f"  - reason_code_map.py  → {len(codes)} codes")
    print(f"  - chargeback_raw.csv  → 5,000 rows (4 networks)")
    print(f"  - all_models.pkl      → retrained on real winnability rates")
    print("=" * 65)
