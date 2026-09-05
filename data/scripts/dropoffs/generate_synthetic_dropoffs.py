"""
Causal Synthetic Drop-Off & Recovery Simulator
==============================================
Generates a causal environment in which an economic recovery policy can be
tested end-to-end.  The simulator satisfies five design invariants:

INVARIANT 1 – Exact ΔΠ formula (incentive charged on P_a, not τ_a)
    ΔΠ_a = P_a[(1-r_a)(CM - D_a) - r_a·K_rto]
           - P_0[(1-r_0)·CM     - r_0·K_rto]
           - K_a

    The discount D_a applies to EVERY treated customer who completes
    (P_a), not just the incremental ones.  Oracle columns expose
    oracle_delta_pi_{a} so the ML pipeline has a ground-truth regret
    target.

INVARIANT 2 – Gaussian copula; no hardcoded defier rate
    Each channel pair (Y_0, Y_a) is drawn from a bivariate normal with
    correlation rho.  Defier / complier proportions emerge naturally from
    (P_0, P_a, rho).  rho is a CLI argument; sensitivity is explored via
    --rho_sweep across {0.70, 0.80, 0.90, 0.95}.

INVARIANT 3 – T-Learner starvation awareness
    The historical policy is deliberately confounded.  The observed dataset
    is split 70 / 15 / 15 so that downstream experiments can vary the
    None-treatment proportion and measure regret changes.

INVARIANT 4 – Propensity separation (true vs estimated)
    The full pi_0 distribution (all 4 actions) is written to the observed
    split as pi_0_none / pi_0_wa / pi_0_sms / pi_0_email so downstream
    pipelines can estimate π̂_0 from logged data and compare.  The oracle
    also carries the true propensity vector.  Positivity / overlap is
    enforced at epsilon = 0.05 on every row.

INVARIANT 5 – Physical anti-leakage export
    - data/synthetic/observed/{train,validation,test}.parquet (.csv)
    - data/synthetic/oracle/test_counterfactuals.parquet (.csv)
    Oracle columns (Y_wa, Y_sms, … oracle_delta_pi_*) are NEVER written
    to the observed split files.
"""

import os
import math
import argparse
import numpy as np
import pandas as pd
from scipy.stats import norm

# ── Default economic parameters used in oracle ΔΠ computation ────────────────
DEFAULT_MARGIN          = 0.25   # CM  (merchant gross margin fraction)
DEFAULT_RTO_COST        = 250.0  # K_rto  (₹ reverse logistics cost)
DEFAULT_COST_WA         = 0.80   # K_wa   (₹ per WhatsApp notification)
DEFAULT_COST_SMS        = 0.20   # K_sms  (₹ per SMS)
DEFAULT_COST_EMAIL      = 0.05   # K_email
DEFAULT_INCENTIVE_WA    = 0.0    # D_wa   (₹ discount if intervention completes)
DEFAULT_INCENTIVE_SMS   = 0.0
DEFAULT_INCENTIVE_EMAIL = 0.0


# ── Math helpers ──────────────────────────────────────────────────────────────

def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -25.0, 25.0)))


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1.0 - 1e-6)
    return np.log(p / (1.0 - p))


def oracle_delta_pi(
    p_a: np.ndarray,
    p_0: np.ndarray,
    cart: np.ndarray,
    margin: float,
    r_a: np.ndarray,
    r_0: np.ndarray,
    k_rto: float,
    k_a: float,
    d_a: float,
) -> np.ndarray:
    """
    General causal economic value of action a over no-action:

        ΔΠ_a = P_a[(1-r_a)(CM - D_a) - r_a·K_rto]
               - P_0[(1-r_0)·CM     - r_0·K_rto]
               - K_a

    D_a (discount) is applied to P_a—all treated completions pay the
    discount, not only the incremental ones.
    """
    cm = cart * margin
    term_action  = p_a * ((1.0 - r_a) * (cm - d_a) - r_a * k_rto)
    term_organic = p_0 * ((1.0 - r_0) *  cm         - r_0 * k_rto)
    return term_action - term_organic - k_a


# ── Per-channel Gaussian copula draw ─────────────────────────────────────────

def _bivariate_copula_outcomes(
    P_base: np.ndarray,
    P_treat: np.ndarray,
    rho: float,
    rng: np.random.Generator,
) -> tuple:
    """
    Draw (Y_0, Y_a) from a bivariate Gaussian copula with correlation rho.

    This correctly represents heterogeneous treatment effects including
    defiers (Y_0=1, Y_a=0) and always-takers / never-takers.
    The defier proportion is NOT hardcoded; it emerges from P_0, P_a, rho.
    """
    n = len(P_base)
    cov = [[1.0, rho], [rho, 1.0]]
    eps = rng.multivariate_normal([0.0, 0.0], cov, size=n)
    U0 = norm.cdf(eps[:, 0])
    Ua = norm.cdf(eps[:, 1])
    Y0 = (U0 < P_base).astype(int)
    Ya = (Ua < P_treat).astype(int)
    return Y0, Ya


# ── Main generator ────────────────────────────────────────────────────────────

def generate_causal_dataset(
    n_samples: int = 50_000,
    rho: float = 0.85,
    seed: int = 42,
    output_dir: str = "data/synthetic",
    margin: float = DEFAULT_MARGIN,
    rto_cost: float = DEFAULT_RTO_COST,
    cost_wa: float = DEFAULT_COST_WA,
    cost_sms: float = DEFAULT_COST_SMS,
    cost_email: float = DEFAULT_COST_EMAIL,
    incentive_wa: float = DEFAULT_INCENTIVE_WA,
    incentive_sms: float = DEFAULT_INCENTIVE_SMS,
    incentive_email: float = DEFAULT_INCENTIVE_EMAIL,
) -> dict:
    """
    Returns a dict with keys {train_obs, val_obs, test_obs, test_oracle}
    as DataFrames, and also writes them to disk.
    """
    rng = np.random.default_rng(seed)
    np.random.seed(seed)   # scipy uses numpy global RNG

    # ── 1. Latent Customer Profiles ──────────────────────────────────────────
    # 9-dimensional correlated latent space (Gaussian copula)
    # Variables: [intent, friction_sens, price_sens,
    #             wa_recept, sms_recept, email_recept,
    #             urgency, reactance, rto_prop]
    d_latent = 9
    corr_matrix = np.eye(d_latent)
    corr_matrix[0, 6] = corr_matrix[6, 0] =  0.40   # intent ↔ urgency
    corr_matrix[2, 7] = corr_matrix[7, 2] =  0.35   # price_sens ↔ reactance
    corr_matrix[0, 8] = corr_matrix[8, 0] = -0.25   # intent ↔ rto_prop (high intent → low RTO)
    corr_matrix[3, 4] = corr_matrix[4, 3] =  0.45   # wa_recept ↔ sms_recept

    latent_raw = rng.multivariate_normal(np.zeros(d_latent), corr_matrix, size=n_samples)
    latent_u   = norm.cdf(latent_raw)

    intent        = latent_u[:, 0]
    friction_sens = latent_u[:, 1]
    price_sens    = latent_u[:, 2]
    wa_recept     = latent_u[:, 3]
    sms_recept    = latent_u[:, 4]
    email_recept  = latent_u[:, 5]
    urgency       = latent_u[:, 6]
    reactance     = latent_u[:, 7]
    rto_prop      = latent_u[:, 8]

    # ── 2. Observable Session & Checkout Telemetry ────────────────────────────
    cart_values = np.round(
        rng.lognormal(mean=7.5, sigma=0.75, size=n_samples), 2
    )
    cart_values = np.clip(cart_values, 150.0, 45_000.0)

    is_returning = (rng.random(n_samples) < (0.25 + 0.30 * intent)).astype(int)

    device_choices = ["mobile_android", "mobile_ios", "desktop"]
    device_weights = [0.72, 0.18, 0.10]
    device = rng.choice(device_choices, size=n_samples, p=device_weights)

    cod_prob = np.clip(0.10 + 0.40 * rto_prop - 0.15 * (cart_values > 5000), 0.05, 0.65)
    rv = rng.random(n_samples)
    payment_methods = np.where(
        rv < cod_prob, "cod",
        np.where(rv < cod_prob + 0.55 * (1 - cod_prob), "upi",
        np.where(rv < cod_prob + 0.85 * (1 - cod_prob), "card", "netbanking"))
    )

    diag_names = [
        "upi_app_switch_abort",
        "otp_timeout",
        "vpa_validation_failure",
        "price_shock_breakdown",
        "genuine_browse_abandon",
    ]
    diagnoses = []
    for i in range(n_samples):
        pm = payment_methods[i]
        w_switch = (0.20 + 0.25 * friction_sens[i]) if pm == "upi"                 else 0.05
        w_otp    = (0.15 + 0.20 * friction_sens[i]) if pm in ["card","netbanking"] else 0.08
        w_vpa    = 0.12                              if pm == "upi"                 else 0.02
        w_price  = 0.10 + 0.35 * price_sens[i]
        w_browse = 0.35 * (1.0 - intent[i])
        ws = np.array([w_switch, w_otp, w_vpa, w_price, w_browse])
        ws /= ws.sum()
        diagnoses.append(rng.choice(diag_names, p=ws))
    diagnoses = np.array(diagnoses)

    duration_sec           = np.clip(rng.integers(10, 600, size=n_samples) +
                                     rng.gamma(3.0, 30.0, size=n_samples).astype(int), 12, 600)
    attempt_counts         = (1
                              + (rng.random(n_samples) < (0.2 + 0.4 * intent)).astype(int)
                              + (rng.random(n_samples) < 0.15).astype(int))
    events_counts          = np.clip(attempt_counts * 2 + rng.integers(2, 9, size=n_samples), 3, 25)
    sequence_entropy       = np.round(0.4 + 0.5 * rng.random(n_samples) +
                                      0.1 * (events_counts / 25), 3)
    mean_inter_event_time  = np.round(duration_sec / np.maximum(1, events_counts), 2)

    # ── 3. Causal Potential Outcomes (Neyman-Rubin Model) ────────────────────
    diag_organic_shift = {
        "upi_app_switch_abort":    0.55,
        "otp_timeout":             0.35,
        "vpa_validation_failure":  0.10,
        "price_shock_breakdown":  -0.80,
        "genuine_browse_abandon": -1.60,
    }
    diag_shifts = np.array([diag_organic_shift[d] for d in diagnoses])

    L0 = (
        -1.70
        + 2.60 * intent
        - 1.40 * friction_sens
        + 0.70 * urgency
        + diag_shifts
        + 0.35 * is_returning
        - 0.25 * np.log(cart_values / 1000.0)
        + rng.normal(0, 0.20, size=n_samples)
    )
    P0 = sigmoid(L0)

    # Channel-level logit shifts
    delta_L_wa = (
        0.90 * wa_recept * intent
        + np.where(diagnoses == "upi_app_switch_abort",   0.65, 0.0)
        + np.where(diagnoses == "price_shock_breakdown",  0.30, 0.0)
        - 1.35 * reactance
        + rng.normal(0, 0.15, size=n_samples)
    )
    delta_L_sms = (
        0.55 * sms_recept * intent
        + np.where(diagnoses == "otp_timeout",              0.50, 0.0)
        + np.where(diagnoses == "vpa_validation_failure",   0.20, 0.0)
        - 0.80 * reactance
        + rng.normal(0, 0.15, size=n_samples)
    )
    delta_L_email = (
        0.35 * email_recept * intent
        + np.where(device == "desktop",                    0.35, 0.0)
        - 0.40 * reactance
        + rng.normal(0, 0.15, size=n_samples)
    )

    P_wa    = sigmoid(L0 + delta_L_wa)
    P_sms   = sigmoid(L0 + delta_L_sms)
    P_email = sigmoid(L0 + delta_L_email)

    # ── INVARIANT 2: Per-channel bivariate copula ─────────────────────────────
    # Each channel gets its own independent bivariate draw correlated at rho.
    # Defier/complier proportions emerge from (P0, P_a, rho)—NOT hardcoded.
    Y0,     Y_wa    = _bivariate_copula_outcomes(P0, P_wa,    rho, rng)
    Y0_sms, Y_sms   = _bivariate_copula_outcomes(P0, P_sms,   rho, rng)
    Y0_email,Y_email= _bivariate_copula_outcomes(P0, P_email, rho, rng)
    # Y0 is the canonical no-action outcome; the other Y0_* are consistent
    # channel-specific noise draws used only inside copula pairs.

    # Conditional RTO rates (separate for baseline and each action)
    logit_r0_base = (
        -2.10
        + 2.20 * rto_prop
        + 1.35 * (payment_methods == "cod").astype(float)
        + 0.25 * np.log(cart_values / 1000.0)
        - 0.55 * is_returning
        + rng.normal(0, 0.15, size=n_samples)
    )
    r0      = sigmoid(logit_r0_base)
    r_wa    = sigmoid(logit_r0_base + 0.05)   # slightly elevated (push delivery)
    r_sms   = sigmoid(logit_r0_base + 0.05)
    r_email = sigmoid(logit_r0_base - 0.05)   # email attracts less impulsive buyers

    # Realise RTO conditional on purchase, using correlated draws per action
    rto_u   = rng.random(n_samples)
    RTO_0     = ((rto_u < r0    ) & (Y0     == 1)).astype(int)
    RTO_wa    = ((rto_u < r_wa  ) & (Y_wa   == 1)).astype(int)
    RTO_sms   = ((rto_u < r_sms ) & (Y_sms  == 1)).astype(int)
    RTO_email = ((rto_u < r_email) & (Y_email== 1)).astype(int)

    # ── INVARIANT 1: Oracle ΔΠ columns ───────────────────────────────────────
    # D_a applied on P_a (all treated completions), not only on τ_a.
    oracle_dpi_wa    = oracle_delta_pi(P_wa,    P0, cart_values, margin,
                                       r_wa,    r0, rto_cost, cost_wa,    incentive_wa)
    oracle_dpi_sms   = oracle_delta_pi(P_sms,   P0, cart_values, margin,
                                       r_sms,   r0, rto_cost, cost_sms,   incentive_sms)
    oracle_dpi_email = oracle_delta_pi(P_email, P0, cart_values, margin,
                                       r_email, r0, rto_cost, cost_email, incentive_email)

    # ── 4. Confounded Historical Logging Policy π_0(A|X) ─────────────────────
    # Intentional confounding:
    #   high cart + tech glitch → WhatsApp
    #   OTP / low cart          → SMS
    #   browse abandon          → None
    #   desktop                 → Email
    actions = ["none", "whatsapp", "sms", "email"]

    s_none  = 1.10 + 1.60 * (diagnoses == "genuine_browse_abandon") - 0.70 * (cart_values > 2500)
    s_wa    = 0.90 + 1.20 * (diagnoses == "upi_app_switch_abort") + 1.10 * (cart_values > 2500) - 0.60 * (cart_values < 800)
    s_sms   = 0.80 + 1.00 * (diagnoses == "otp_timeout") + 0.60 * (cart_values < 1500)
    s_email = 0.50 + 0.80 * (device == "desktop")

    raw_scores = np.stack([s_none, s_wa, s_sms, s_email], axis=1)
    exp_scores = np.exp(raw_scores - raw_scores.max(axis=1, keepdims=True))
    pi_raw     = exp_scores / exp_scores.sum(axis=1, keepdims=True)

    # ── INVARIANT 4: Positivity / overlap enforcement ─────────────────────────
    epsilon    = 0.05
    pi_clipped = np.clip(pi_raw, epsilon, 1.0 - epsilon)
    pi_0       = pi_clipped / pi_clipped.sum(axis=1, keepdims=True)

    # Assign historical treatment
    assigned_action_idx = np.array(
        [rng.choice(4, p=pi_0[i]) for i in range(n_samples)]
    )
    assigned_actions = np.array([actions[idx] for idx in assigned_action_idx])

    # Realised observational outcome follows the assigned action's potential outcome
    y_matrix   = np.stack([Y0, Y_wa, Y_sms, Y_email], axis=1)
    rto_matrix = np.stack([RTO_0, RTO_wa, RTO_sms, RTO_email], axis=1)
    realized_Y   = y_matrix[np.arange(n_samples), assigned_action_idx]
    realized_RTO = rto_matrix[np.arange(n_samples), assigned_action_idx]
    logged_propensity = pi_0[np.arange(n_samples), assigned_action_idx]

    # ── 5. Assemble Datasets ──────────────────────────────────────────────────
    session_ids = [f"sess_{seed}_{i:06d}" for i in range(n_samples)]

    # ── INVARIANT 4: Full pi_0 vector in observed split ───────────────────────
    # The ML pipeline must estimate π̂_0 from logged data.
    # We include the oracle pi_0 distribution so evaluation can compare
    # oracle-propensity vs estimated-propensity modes.
    df_obs = pd.DataFrame({
        "session_id":              session_ids,
        "cart_value":              cart_values,
        "payment_method":          payment_methods,
        "device":                  device,
        "diagnosis":               diagnoses,
        "duration_sec":            duration_sec,
        "attempt_count":           attempt_counts,
        "events_count":            events_counts,
        "sequence_entropy":        sequence_entropy,
        "mean_inter_event_time":   mean_inter_event_time,
        "is_returning_customer":   is_returning,
        # Historical assignment
        "assigned_action":         assigned_actions,
        "realized_outcome":        realized_Y,
        "realized_rto":            realized_RTO,
        # True logging-policy propensities (full distribution) — for oracle mode;
        # production pipelines must estimate π̂_0 from the logged data above.
        "true_propensity_score":   logged_propensity,   # pi_0(assigned_action | X)
        "pi_0_none":               pi_0[:, 0],
        "pi_0_wa":                 pi_0[:, 1],
        "pi_0_sms":                pi_0[:, 2],
        "pi_0_email":              pi_0[:, 3],
    })

    # ── INVARIANT 5: Oracle dataset — counterfactuals NEVER in observed files ──
    df_oracle = pd.DataFrame({
        "session_id":              session_ids,
        # True potential outcome probabilities
        "P0":       P0,
        "P_wa":     P_wa,
        "P_sms":    P_sms,
        "P_email":  P_email,
        # True RTO rates (separate for each action)
        "r0":       r0,
        "r_wa":     r_wa,
        "r_sms":    r_sms,
        "r_email":  r_email,
        # Realised potential outcomes
        "Y0":       Y0,
        "Y_wa":     Y_wa,
        "Y_sms":    Y_sms,
        "Y_email":  Y_email,
        "RTO0":     RTO_0,
        "RTO_wa":   RTO_wa,
        "RTO_sms":  RTO_sms,
        "RTO_email":RTO_email,
        # ── INVARIANT 1: Oracle ΔΠ (ground-truth regret targets) ─────────────
        "oracle_delta_pi_wa":    oracle_dpi_wa,
        "oracle_delta_pi_sms":   oracle_dpi_sms,
        "oracle_delta_pi_email": oracle_dpi_email,
        # Latents for audit / sensitivity analysis
        "latent_intent":     intent,
        "latent_reactance":  reactance,
        "latent_rto_prop":   rto_prop,
        # Oracle propensity mirror
        "pi_0_none":  pi_0[:, 0],
        "pi_0_wa":    pi_0[:, 1],
        "pi_0_sms":   pi_0[:, 2],
        "pi_0_email": pi_0[:, 3],
    })

    # ── 6. Physical Separation & Train/Val/Test Split ─────────────────────────
    n_train = int(0.70 * n_samples)
    n_val   = int(0.15 * n_samples)

    train_obs = df_obs.iloc[:n_train]
    val_obs   = df_obs.iloc[n_train:n_train + n_val]
    test_obs  = df_obs.iloc[n_train + n_val:]
    test_oracle = df_oracle.iloc[n_train + n_val:]

    obs_dir    = os.path.join(output_dir, "observed")
    oracle_dir = os.path.join(output_dir, "oracle")
    os.makedirs(obs_dir,    exist_ok=True)
    os.makedirs(oracle_dir, exist_ok=True)

    try:
        train_obs.to_parquet(  os.path.join(obs_dir,    "train.parquet"),               index=False)
        val_obs.to_parquet(    os.path.join(obs_dir,    "validation.parquet"),           index=False)
        test_obs.to_parquet(   os.path.join(obs_dir,    "test.parquet"),                 index=False)
        test_oracle.to_parquet(os.path.join(oracle_dir, "test_counterfactuals.parquet"), index=False)
        print("Successfully saved Parquet datasets.")
    except Exception as e:
        print(f"Parquet export skipped ({e}), saving CSV only...")

    train_obs.to_csv(  os.path.join(obs_dir,    "train.csv"),               index=False)
    val_obs.to_csv(    os.path.join(obs_dir,    "validation.csv"),           index=False)
    test_obs.to_csv(   os.path.join(obs_dir,    "test.csv"),                 index=False)
    test_oracle.to_csv(os.path.join(oracle_dir, "test_counterfactuals.csv"), index=False)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print(f"Causal Simulator Complete: {n_samples:,} total sessions  |  rho={rho}")
    print(f"Splits — Train: {len(train_obs):,} | Val: {len(val_obs):,} | Test: {len(test_obs):,}")
    print(f"Oracle test counterfactuals: {len(test_oracle):,}  (ISOLATED in {oracle_dir})")
    print("\nAction distribution in training data:")
    print(train_obs["assigned_action"].value_counts(normalize=True).to_string())
    print("\nMean potential outcome probabilities (test world):")
    print(f"  P0 (Organic):  {test_oracle['P0'].mean():.3f}   (realised: {test_oracle['Y0'].mean():.3f})")
    print(f"  P_wa:          {test_oracle['P_wa'].mean():.3f}   (realised: {test_oracle['Y_wa'].mean():.3f})")
    print(f"  P_sms:         {test_oracle['P_sms'].mean():.3f}   (realised: {test_oracle['Y_sms'].mean():.3f})")
    print(f"  P_email:       {test_oracle['P_email'].mean():.3f}   (realised: {test_oracle['Y_email'].mean():.3f})")
    print(f"\nOracleCopulaStats (rho={rho}):")
    tau_wa   = test_oracle["P_wa"]   - test_oracle["P0"]
    tau_sms  = test_oracle["P_sms"]  - test_oracle["P0"]
    defiers_wa  = ((test_oracle["Y0"] == 1) & (test_oracle["Y_wa"]  == 0)).mean()
    defiers_sms = ((test_oracle["Y0"] == 1) & (test_oracle["Y_sms"] == 0)).mean()
    print(f"  WA  CATE mean={tau_wa.mean():.3f} std={tau_wa.std():.3f}  defier_rate={defiers_wa:.3f}")
    print(f"  SMS CATE mean={tau_sms.mean():.3f} std={tau_sms.std():.3f}  defier_rate={defiers_sms:.3f}")
    print(f"\nOracle ΔΠ (per-session, economic parameters: margin={margin}, K_rto={rto_cost}):")
    print(f"  WA:    mean={test_oracle['oracle_delta_pi_wa'].mean():.2f}")
    print(f"  SMS:   mean={test_oracle['oracle_delta_pi_sms'].mean():.2f}")
    print(f"  Email: mean={test_oracle['oracle_delta_pi_email'].mean():.2f}")
    print("=" * 72 + "\n")

    return {
        "train_obs":   train_obs,
        "val_obs":     val_obs,
        "test_obs":    test_obs,
        "test_oracle": test_oracle,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate causal synthetic checkout drop-off data."
    )
    parser.add_argument("--samples",    type=int,   default=50_000, help="Number of sessions")
    parser.add_argument("--rho",        type=float, default=0.85,
                        help="Copula correlation (0-1). Higher = fewer defiers. "
                             "No single value is 'realistic'; use --rho_sweep for sensitivity.")
    parser.add_argument("--seed",       type=int,   default=42,     help="Random seed")
    parser.add_argument("--output_dir", type=str,   default="data/synthetic", help="Output directory")
    parser.add_argument(
        "--rho_sweep", action="store_true",
        help="Generate four datasets at rho in {0.70, 0.80, 0.90, 0.95} "
             "for sensitivity analysis. Each written to its own subdirectory."
    )
    # Economic parameters (for oracle ΔΠ computation)
    parser.add_argument("--margin",         type=float, default=DEFAULT_MARGIN)
    parser.add_argument("--rto_cost",       type=float, default=DEFAULT_RTO_COST)
    parser.add_argument("--cost_wa",        type=float, default=DEFAULT_COST_WA)
    parser.add_argument("--cost_sms",       type=float, default=DEFAULT_COST_SMS)
    parser.add_argument("--cost_email",     type=float, default=DEFAULT_COST_EMAIL)
    parser.add_argument("--incentive_wa",   type=float, default=DEFAULT_INCENTIVE_WA)
    parser.add_argument("--incentive_sms",  type=float, default=DEFAULT_INCENTIVE_SMS)
    parser.add_argument("--incentive_email",type=float, default=DEFAULT_INCENTIVE_EMAIL)
    args = parser.parse_args()

    shared_kwargs = dict(
        n_samples    = args.samples,
        seed         = args.seed,
        margin       = args.margin,
        rto_cost     = args.rto_cost,
        cost_wa      = args.cost_wa,
        cost_sms     = args.cost_sms,
        cost_email   = args.cost_email,
        incentive_wa = args.incentive_wa,
        incentive_sms= args.incentive_sms,
        incentive_email=args.incentive_email,
    )

    if args.rho_sweep:
        # ── INVARIANT 2: Sensitivity analysis across rho values ───────────────
        sweep_rhos = [0.70, 0.80, 0.90, 0.95]
        print(f"\nRho sweep: {sweep_rhos}\n")
        for r in sweep_rhos:
            subdir = os.path.join(args.output_dir, "rho_sweep", f"rho_{int(r*100):03d}")
            generate_causal_dataset(rho=r, output_dir=subdir, **shared_kwargs)
    else:
        generate_causal_dataset(rho=args.rho, output_dir=args.output_dir, **shared_kwargs)
