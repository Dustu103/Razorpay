import os
import math
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# λ = 0.023 → external debt signal half-life of ~30 days
# In production, calibrate against empirical borrower cohort data
DEBT_SIGNAL_DECAY_LAMBDA = 0.023

def compute_effective_external_debt(raw_debt: float, data_age_days: int, consent_revoked: bool) -> float:
    """
    Pre-engineers the external debt signal before the model sees it.

    Two rules (enforced in preprocessing, NOT inside the ML model):
      1. Consent Gate: If consent is revoked AND data is stale (>30 days),
         the signal is zeroed out entirely to respect the DPDP Act.
         consent_revoked is never passed as a feature to the tree ensemble
         to prevent it from acting as a risk escalator (chilling effect).
      2. Exponential Decay: For fresh-enough data, the signal decays
         with a 30-day half-life to account for snapshot staleness.
    """
    # Hard gate: consent revoked + stale data → zero out to protect legal right
    if consent_revoked and data_age_days > 30:
        return 0.0

    # Exponential decay: effective_debt = raw_debt * e^(-λ * age_days)
    decay_factor = math.exp(-DEBT_SIGNAL_DECAY_LAMBDA * data_age_days)
    return raw_debt * decay_factor


def generate_recovery_data(n_samples=10000):
    np.random.seed(42)

    internal_debt         = np.random.exponential(1000, n_samples)
    raw_external_debt     = np.random.exponential(5000, n_samples)
    days_since_login      = np.random.randint(0, 90, n_samples)
    demographic_age       = np.random.randint(18, 70, n_samples)
    consent_revoked       = np.random.choice([True, False], n_samples, p=[0.20, 0.80])
    data_age_days         = np.random.randint(0, 120, n_samples)

    # Pre-engineer the effective_external_debt signal
    effective_external_debt = np.array([
        compute_effective_external_debt(
            raw_external_debt[i], data_age_days[i], consent_revoked[i]
        )
        for i in range(n_samples)
    ])

    # Label: best recovery channel
    # 0 = Email, 1 = SMS, 2 = Voice
    # Rules encoded from domain knowledge:
    #   - High effective phantom debt + young = SMS (fast, direct)
    #   - High total debt + older = Voice (personal touch for higher stakes)
    #   - Ghosting (no login) + older = Email (non-intrusive)
    #   - Default = Email
    best_channel = []
    for i in range(n_samples):
        eff_debt = effective_external_debt[i]
        age      = demographic_age[i]
        login    = days_since_login[i]
        i_debt   = internal_debt[i]

        if eff_debt > 8000 and age < 30:
            channel = 1  # SMS
        elif (i_debt + eff_debt) > 10000 and age > 50:
            channel = 2  # Voice
        elif login > 30 and age > 40:
            channel = 0  # Email
        elif eff_debt > 5000 and age < 40:
            channel = 1  # SMS
        else:
            channel = 0  # Email

        best_channel.append(channel)

    return pd.DataFrame({
        "internal_debt":          internal_debt,
        "effective_external_debt": effective_external_debt,  # pre-engineered
        "days_since_login":       days_since_login,
        "demographic_age":        demographic_age,
        # NOTE: consent_revoked and data_age_days are deliberately NOT
        # included as model features. They are preprocessing gates only.
        # Passing consent_revoked to the model would create a chilling effect
        # on the DPDP Act Right to Erasure.
        "best_channel":           best_channel
    })


def main():
    print("Generating corrected synthetic data for BNPL Recovery Engine...")
    print("  - Using pre-engineered effective_external_debt with exponential decay")
    print("  - Consent gate enforced in preprocessing (NOT as ML feature)")
    df = generate_recovery_data(10000)

    X = df[["internal_debt", "effective_external_debt", "days_since_login", "demographic_age"]]
    y = df["best_channel"]

    print("\nTraining BNPL Recovery Random Forest model...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)

    models_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'ml')
    os.makedirs(models_dir, exist_ok=True)

    model_path = os.path.join(models_dir, 'feature_f_recovery.joblib')
    joblib.dump(clf, model_path)

    print(f"\nModel saved to {model_path}")
    print(f"Training Accuracy: {clf.score(X, y):.4f}")
    print(f"\nChannel distribution in training set:")
    print(df['best_channel'].value_counts().rename({0:'Email', 1:'SMS', 2:'Voice'}))


if __name__ == "__main__":
    main()
