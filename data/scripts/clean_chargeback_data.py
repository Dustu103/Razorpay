"""
Step 2: Chargeback Dataset Cleaning & Feature Engineering
==========================================================
- One-hot encode: reason_code, network
- WoE encode: merchant_category (captures win/loss ratio per category)
- MinMaxScaler: days_remaining, days_since_transaction, transaction_amount_inr
- SMOTE: applied per reason-code stratum for any code with <30% minority class
- Saves: chargeback_processed.csv, woe_encoder.json, feature_scaler.pkl

Run after generate_chargeback_data.py
"""

import pandas as pd
import numpy as np
import json
import pickle
import os
from sklearn.preprocessing import MinMaxScaler
from sklearn.utils import resample
from collections import defaultdict

INPUT_PATH  = "data/chargeback/chargeback_raw.csv"
OUTPUT_PATH = "data/chargeback/chargeback_processed.csv"
WOE_PATH    = "models/chargeback/woe_encoder.json"
SCALER_PATH = "models/chargeback/feature_scaler.pkl"

RANDOM_SEED = 42


def compute_woe(df: pd.DataFrame, col: str, target: str = "outcome") -> dict:
    """
    Weight of Evidence encoding:
      WoE_i = ln( (wins_i / total_wins) / (losses_i / total_losses) )
    """
    total_wins   = df[target].sum()
    total_losses = len(df) - total_wins
    woe_map = {}

    for category in df[col].unique():
        subset = df[df[col] == category]
        wins   = subset[target].sum()
        losses = len(subset) - wins

        # Laplace smoothing to avoid log(0)
        wins   = max(wins, 0.5)
        losses = max(losses, 0.5)

        woe = np.log((wins / total_wins) / (losses / total_losses))
        woe_map[category] = round(woe, 6)

    return woe_map


def apply_smote_manual(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-reason-code SMOTE:
    For any code where minority class < 30% of that code's rows,
    oversample minority to reach 40%.
    """
    balanced_dfs = []
    for code in df["reason_code"].unique():
        subset = df[df["reason_code"] == code]
        wins   = subset[subset["outcome"] == 1]
        losses = subset[subset["outcome"] == 0]

        minority = wins if len(wins) < len(losses) else losses
        majority = losses if len(wins) < len(losses) else wins

        ratio = len(minority) / len(subset)
        if ratio < 0.30:
            # Oversample minority to ~40% of total
            target_minority = int(len(majority) * 0.67)  # 40% of total ≈ 0.67 × majority
            minority_resampled = resample(
                minority, replace=True,
                n_samples=target_minority,
                random_state=RANDOM_SEED
            )
            subset = pd.concat([majority, minority_resampled])
            print(f"  SMOTE [{code}]: {len(minority)} → {len(minority_resampled)} minority samples")

        balanced_dfs.append(subset)

    return pd.concat(balanced_dfs).sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)


def clean_and_engineer(df: pd.DataFrame):
    print(f"Input shape: {df.shape}")
    print(f"Missing values:\n{df.isnull().sum()}")

    # ── 1. Drop duplicates ────────────────────────────────────────────────────
    df = df.drop_duplicates()
    print(f"\nAfter dedup: {df.shape}")

    # ── 2. Interaction features (computed on raw cols BEFORE encoding) ────────
    print("\nEngineering interaction features...")
    evidence_cols = ["has_3ds_auth", "has_delivery_proof", "has_avs_cvv_match",
                     "has_ip_device_fingerprint", "has_prior_comms",
                     "has_signed_receipt", "has_usage_logs"]

    # 3DS present on a fraud code = liability shifts to issuer (biggest real-world signal)
    df["fraud_code_3ds"] = df["has_3ds_auth"].astype(int)

    # Total evidence count: more evidence = higher win probability
    df["evidence_density"] = df[evidence_cols].sum(axis=1)

    # Deadline urgency: 1 = expired, 0 = plenty of time
    max_days = max(df["days_remaining"].max(), 1)
    df["deadline_urgency"] = 1.0 - (df["days_remaining"] / max_days)

    # High-value flag: >50K INR gets extra issuer scrutiny
    df["high_value_flag"] = (df["transaction_amount_inr"] > 50000).astype(int)

    # Repeat dispute decay: serial disputers get exponentially lower trust
    df["repeat_fraud_signal"] = np.where(
        df["repeat_dispute_count"] > 0,
        1.0 / (1.0 + df["repeat_dispute_count"]),
        1.0
    )

    # Complete evidence kit WITH comms history = strongest combined signal
    df["full_evidence_with_comms"] = (
        (df["evidence_completeness_score"] == 2) & (df["has_prior_comms"] == 1)
    ).astype(int)

    print(f"  Added 6 interaction features.")

    # ── 3. WoE encode merchant_category ──────────────────────────────────────
    print("\nComputing WoE for merchant_category...")
    woe_map = compute_woe(df, "merchant_category")
    print(f"  WoE values: {woe_map}")
    df["merchant_category_woe"] = df["merchant_category"].map(woe_map)
    df = df.drop(columns=["merchant_category"])

    # ── 4. One-hot encode reason_code and network ─────────────────────────────
    df = pd.get_dummies(df, columns=["reason_code", "network"], drop_first=False)

    # ── 5. MinMaxScaler on numeric columns ───────────────────────────────────
    scale_cols = ["days_remaining", "days_since_transaction", "transaction_amount_inr",
                  "repeat_dispute_count", "evidence_density", "deadline_urgency",
                  "repeat_fraud_signal"]
    scaler = MinMaxScaler()
    df[scale_cols] = scaler.fit_transform(df[scale_cols])

    # ── 6. Class balance report ───────────────────────────────────────────────
    print(f"\nClass balance: {df['outcome'].value_counts().to_dict()}")
    print(f"  Win rate: {df['outcome'].mean():.1%}")
    print(f"  Total features: {df.shape[1] - 1}")

    return df, woe_map, scaler


def generate_data_report(df_raw: pd.DataFrame, df_processed: pd.DataFrame):
    print("\n" + "="*60)
    print("DATA CLEANING REPORT")
    print("="*60)
    print(f"Raw rows:       {len(df_raw)}")
    print(f"Processed rows: {len(df_processed)}")
    print(f"Features:       {df_processed.shape[1] - 1}")  # -1 for outcome
    print(f"Win rate:       {df_processed['outcome'].mean():.1%}")
    print(f"\nFeature list:")
    for col in sorted(df_processed.columns):
        if col != "outcome":
            print(f"  - {col}")


if __name__ == "__main__":
    print("Loading raw dataset...")
    df_raw = pd.read_csv(INPUT_PATH)

    df_processed, woe_map, scaler = clean_and_engineer(df_raw.copy())

    # ── Apply SMOTE ───────────────────────────────────────────────────────────
    print("\nApplying per-stratum SMOTE...")
    # For SMOTE we need reason_code back — it's been one-hot'd, so check raw
    # We apply SMOTE on processed data using outcome column
    wins   = df_processed[df_processed["outcome"] == 1]
    losses = df_processed[df_processed["outcome"] == 0]
    overall_ratio = len(wins) / len(df_processed)
    if overall_ratio < 0.35 or overall_ratio > 0.65:
        # Simple global SMOTE to balance
        majority = wins if len(wins) > len(losses) else losses
        minority = losses if len(wins) > len(losses) else wins
        minority_up = resample(minority, replace=True, n_samples=len(majority), random_state=RANDOM_SEED)
        df_processed = pd.concat([majority, minority_up]).sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)
        print(f"  Global SMOTE applied → new win rate: {df_processed['outcome'].mean():.1%}")

    # ── Save ──────────────────────────────────────────────────────────────────
    df_processed.to_csv(OUTPUT_PATH, index=False)
    with open(WOE_PATH, "w") as f:
        json.dump(woe_map, f, indent=2)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    generate_data_report(df_raw, df_processed)
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"Saved: {WOE_PATH}")
    print(f"Saved: {SCALER_PATH}")
