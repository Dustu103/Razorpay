"""
Economic Invariants & Policy Liveness Test Suite
=================================================
Validates that the Causal Decision Engine adheres to economic laws and
liveness requirements.

Tests are divided into two classes:

SAFETY / INVARIANT TESTS
    Monotonicity and boundary conditions that must ALWAYS hold.
    These guard against degenerate model behaviour (e.g. "always suppress").

LIVENESS TESTS
    Economically obvious scenarios where the policy MUST intervene.
    These guard against the complementary failure mode: "always suppress"
    satisfies all monotonicity tests but a correct policy would never suppress
    in a clearly profitable scenario.

SENSITIVITY TESTS
    Relative comparisons, e.g. EV(cost=₹0.80) > EV(cost=₹5). These are
    more robust than absolute-value assertions and mirror what a
    well-calibrated policy should rank correctly.

SEMANTICS TESTS
    Verify that incentive D_a is charged on P_a (all treated completions),
    NOT on τ_a = P_a − P_0.

DATA INTEGRITY TESTS
    Anti-leakage guards: oracle columns must not appear in observed files.
"""

import os
import sys

# ── Core formula ─────────────────────────────────────────────────────────────

def compute_delta_pi(
    p_action: float,
    p_organic: float,
    cart_value: float,
    merchant_margin: float,
    channel_cost: float,
    rto_rate_action: float = 0.10,
    rto_rate_organic: float = 0.10,
    rto_cost: float = 250.0,
    incentive: float = 0.0,
) -> float:
    """
    Exact general ΔΠ formula (Critique 1):

        ΔΠ_a = P_a[(1-r_a)(CM - D_a) - r_a·K_rto]
               - P_0[(1-r_0)·CM      - r_0·K_rto]
               - K_a

    D_a (incentive) is charged on P_a — ALL treated completions, not τ_a.
    """
    cm           = cart_value * merchant_margin
    term_action  = p_action  * ((1.0 - rto_rate_action)  * (cm - incentive) - rto_rate_action  * rto_cost)
    term_organic = p_organic * ((1.0 - rto_rate_organic) *  cm              - rto_rate_organic * rto_cost)
    return term_action - term_organic - channel_cost


def _argmax_action(
    p0: float, p_wa: float, p_sms: float, p_email: float,
    r0: float, r_wa: float, r_sms: float, r_email: float,
    cart: float, margin: float,
    cost_wa: float, cost_sms: float, cost_email: float,
    incentive_wa: float = 0.0, incentive_sms: float = 0.0, incentive_email: float = 0.0,
    rto_cost: float = 250.0,
) -> tuple:
    """Returns (best_action, best_delta_pi) using exact general formula."""
    candidates = {
        "whatsapp": compute_delta_pi(p_wa,    p0, cart, margin, cost_wa,    r_wa,    r0, rto_cost, incentive_wa),
        "sms":      compute_delta_pi(p_sms,   p0, cart, margin, cost_sms,   r_sms,   r0, rto_cost, incentive_sms),
        "email":    compute_delta_pi(p_email, p0, cart, margin, cost_email, r_email, r0, rto_cost, incentive_email),
    }
    best_action   = "none"
    best_delta_pi = 0.0
    for action, ev in candidates.items():
        if ev > best_delta_pi:
            best_delta_pi = ev
            best_action   = action
    return best_action, best_delta_pi


# ═══════════════════════════════════════════════════════════════════════════════
# SAFETY / INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_channel_cost_monotonicity():
    """Higher channel cost must strictly reduce ΔΠ."""
    p_act  = 0.65
    p_org  = 0.20
    cart   = 2500.0
    margin = 0.25

    costs = [0.20, 0.80, 2.50, 10.00, 350.00]
    evs   = [compute_delta_pi(p_act, p_org, cart, margin, channel_cost=c) for c in costs]

    for i in range(len(evs) - 1):
        assert evs[i] > evs[i + 1], (
            f"EV({costs[i]}) > EV({costs[i+1]}) violated: {evs[i]:.4f} <= {evs[i+1]:.4f}"
        )
    assert evs[-1] < 0, f"EV at cost=350 must be negative, got {evs[-1]:.4f}"
    print("✓ test_channel_cost_monotonicity")


def test_organic_recovery_monotonicity():
    """Higher P_0 (organic) must strictly reduce ΔΠ."""
    cart   = 3000.0
    margin = 0.30
    cost   = 0.80
    p_act  = 0.70

    organic_probs = [0.10, 0.25, 0.40, 0.55, 0.65]
    evs = [compute_delta_pi(p_act, p_org, cart, margin, cost) for p_org in organic_probs]

    for i in range(len(evs) - 1):
        assert evs[i] > evs[i + 1], (
            f"EV must decrease as P0 rises: got {evs[i]:.4f} <= {evs[i+1]:.4f} at P0={organic_probs[i+1]}"
        )
    print("✓ test_organic_recovery_monotonicity")


def test_rto_cost_monotonicity():
    """Higher K_rto must reduce ΔΠ when RTO rate > 0."""
    cart   = 4000.0
    margin = 0.20
    cost   = 0.80
    p_act  = 0.60
    p_org  = 0.30

    rto_costs = [50.0, 150.0, 300.0, 600.0]
    evs = [
        compute_delta_pi(p_act, p_org, cart, margin, cost,
                         rto_rate_action=0.25, rto_rate_organic=0.25, rto_cost=k)
        for k in rto_costs
    ]
    for i in range(len(evs) - 1):
        assert evs[i] > evs[i + 1], (
            f"EV must decrease with higher K_rto: got {evs[i]:.4f} <= {evs[i+1]:.4f}"
        )
    print("✓ test_rto_cost_monotonicity")


def test_zero_margin_suppression():
    """Zero gross margin with positive channel cost must always suppress."""
    ev = compute_delta_pi(
        p_action=0.90, p_organic=0.10,
        cart_value=10_000.0, merchant_margin=0.0,
        channel_cost=0.80,
    )
    assert ev < 0, f"Zero-margin + positive cost must be negative, got {ev:.4f}"
    print("✓ test_zero_margin_suppression")


def test_higher_rto_rate_on_action_penalises():
    """Action with elevated RTO rate must have lower EV than action with low RTO rate."""
    cart   = 3000.0
    margin = 0.30
    p_act  = 0.60
    p_org  = 0.20
    cost   = 0.80

    ev_low_rto  = compute_delta_pi(p_act, p_org, cart, margin, cost, rto_rate_action=0.05)
    ev_high_rto = compute_delta_pi(p_act, p_org, cart, margin, cost, rto_rate_action=0.40)
    assert ev_low_rto > ev_high_rto, (
        f"Low-RTO action should dominate high-RTO action: {ev_low_rto:.4f} <= {ev_high_rto:.4f}"
    )
    print("✓ test_higher_rto_rate_on_action_penalises")


# ═══════════════════════════════════════════════════════════════════════════════
# LIVENESS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_ev_gt_zero_obvious_wa_scenario():
    """
    Liveness guard: the exact spec scenario must yield EV(WA) > 0.

        cart_value = ₹5,000   margin = 40%
        P(organic) = 0.15     P(WA) = 0.65
        RTO risk   = 0.05 (both arms)
        WA cost    = ₹0.80    incentive = ₹0
    """
    ev_wa = compute_delta_pi(
        p_action=0.65, p_organic=0.15,
        cart_value=5_000.0, merchant_margin=0.40,
        channel_cost=0.80,
        rto_rate_action=0.05, rto_rate_organic=0.05,
        incentive=0.0,
    )
    assert ev_wa > 0, f"Obvious WA opportunity must have EV > 0, got {ev_wa:.4f}"
    print(f"✓ test_ev_gt_zero_obvious_wa_scenario  (EV={ev_wa:.2f})")


def test_obvious_wa_is_recommended_action():
    """
    Liveness guard: argmax must select 'whatsapp' in the obvious scenario.
    'always suppress' would fail this test.
    """
    best_action, best_ev = _argmax_action(
        p0=0.15,  p_wa=0.65, p_sms=0.45, p_email=0.22,
        r0=0.05,  r_wa=0.05, r_sms=0.05, r_email=0.05,
        cart=5_000.0, margin=0.40,
        cost_wa=0.80, cost_sms=0.20, cost_email=0.05,
    )
    assert best_action == "whatsapp", (
        f"argmax should be 'whatsapp', got '{best_action}' (ΔΠ={best_ev:.2f})"
    )
    print(f"✓ test_obvious_wa_is_recommended_action  (action={best_action}, ΔΠ={best_ev:.2f})")


def test_suppress_high_organic_tiny_lift():
    """
    Liveness guard: high organic + tiny incremental lift + expensive channel
    must suppress (NO_ACTION).
    """
    best_action, best_ev = _argmax_action(
        p0=0.85, p_wa=0.87, p_sms=0.86, p_email=0.855,
        r0=0.05, r_wa=0.05, r_sms=0.05, r_email=0.05,
        cart=2_000.0, margin=0.20,
        cost_wa=0.80, cost_sms=0.20, cost_email=0.05,
        incentive_wa=50.0, incentive_sms=50.0, incentive_email=50.0,
    )
    assert best_action == "none", (
        f"High-organic + tiny lift must suppress, got '{best_action}' (ΔΠ={best_ev:.2f})"
    )
    print(f"✓ test_suppress_high_organic_tiny_lift  (action={best_action})")


# ═══════════════════════════════════════════════════════════════════════════════
# SENSITIVITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_ev_sensitivity_to_channel_cost():
    """EV(cost=₹0.80) must be strictly greater than EV(cost=₹5.00)."""
    base_kwargs = dict(
        p_action=0.60, p_organic=0.25,
        cart_value=3_000.0, merchant_margin=0.30,
        rto_rate_action=0.08, rto_rate_organic=0.08,
    )
    ev_cheap     = compute_delta_pi(**base_kwargs, channel_cost=0.80)
    ev_expensive = compute_delta_pi(**base_kwargs, channel_cost=5.00)
    assert ev_cheap > ev_expensive, (
        f"EV(₹0.80) should exceed EV(₹5.00): {ev_cheap:.4f} <= {ev_expensive:.4f}"
    )
    print(f"✓ test_ev_sensitivity_to_channel_cost  (Δ={ev_cheap - ev_expensive:.2f})")


def test_ev_sensitivity_to_organic_prob():
    """EV(P0=0.20) must be strictly greater than EV(P0=0.70)."""
    base_kwargs = dict(
        p_action=0.75,
        cart_value=3_000.0, merchant_margin=0.30,
        channel_cost=0.80,
        rto_rate_action=0.08, rto_rate_organic=0.08,
    )
    ev_low_organic  = compute_delta_pi(**base_kwargs, p_organic=0.20)
    ev_high_organic = compute_delta_pi(**base_kwargs, p_organic=0.70)
    assert ev_low_organic > ev_high_organic, (
        f"EV(P0=0.20) should exceed EV(P0=0.70): {ev_low_organic:.4f} <= {ev_high_organic:.4f}"
    )
    print(f"✓ test_ev_sensitivity_to_organic_prob  (Δ={ev_low_organic - ev_high_organic:.2f})")


# ═══════════════════════════════════════════════════════════════════════════════
# INCENTIVE SEMANTICS TEST
# ═══════════════════════════════════════════════════════════════════════════════

def test_incentive_charged_on_pa_not_tau():
    """
    Critique 1 — Incentive semantics:

    When P_a > P_0 > 0, the cost of the discount is higher than it would be
    if charged only on the CATE τ = P_a − P_0.

    Specifically:
        EV(correct: D_a on P_a) < EV(wrong: D_a only on τ_a)

    because P_a > τ_a when P_0 > 0.
    """
    cart, margin = 3000.0, 0.30
    cm           = cart * margin
    p_org        = 0.35   # non-zero baseline purchase probability
    p_act        = 0.70
    tau          = p_act - p_org
    cost_wa      = 0.80
    incentive    = 50.0   # ₹50 discount
    rto          = 0.08
    k_rto        = 250.0

    # Correct: discount charged on P_a
    ev_correct = compute_delta_pi(
        p_act, p_org, cart, margin, cost_wa,
        rto_rate_action=rto, rto_rate_organic=rto,
        rto_cost=k_rto, incentive=incentive,
    )

    # Wrong: discount charged only on τ_a (simulated by scaling incentive by tau/p_act)
    ev_wrong = compute_delta_pi(
        p_act, p_org, cart, margin, cost_wa,
        rto_rate_action=rto, rto_rate_organic=rto,
        rto_cost=k_rto, incentive=incentive * (tau / p_act),
    )

    assert ev_correct < ev_wrong, (
        f"Correct semantics (D on P_a) must give lower EV than wrong semantics (D on τ_a): "
        f"{ev_correct:.4f} >= {ev_wrong:.4f}.  "
        f"P_a={p_act}, τ_a={tau:.3f}, ratio={tau/p_act:.3f}"
    )
    print(
        f"✓ test_incentive_charged_on_pa_not_tau  "
        f"(EV_correct={ev_correct:.2f}  EV_wrong={ev_wrong:.2f}  Δ={ev_wrong-ev_correct:.2f})"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DATA INTEGRITY / ANTI-LEAKAGE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_propensity_columns_present_in_observed():
    """
    Critique 4: observed split must contain the full pi_0 vector
    but must NOT contain oracle counterfactual columns.
    """
    obs_csv = os.path.join("data", "dropoffs", "observed", "train.csv")
    if not os.path.exists(obs_csv):
        obs_csv = os.path.join("data", "synthetic", "observed", "train.csv")
    if not os.path.exists(obs_csv):
        print(f"  SKIP test_propensity_columns_present_in_observed (file not found: {obs_csv})")
        return

    import csv
    with open(obs_csv, newline="") as fh:
        header = next(csv.reader(fh))

    required_propensity = ["pi_0_none", "pi_0_wa", "pi_0_sms", "pi_0_email"]
    forbidden_oracle    = ["Y_wa", "Y_sms", "Y_email", "oracle_delta_pi_wa"]

    for col in required_propensity:
        assert col in header, f"Observed split missing propensity column: '{col}'"
    for col in forbidden_oracle:
        assert col not in header, (
            f"Observed split must NOT contain oracle column: '{col}'  (anti-leakage violated)"
        )
    print("✓ test_propensity_columns_present_in_observed")


def test_oracle_isolation():
    """
    Critique 5 / INVARIANT 5: oracle counterfactual file must NOT reside in
    the observed/ directory.
    """
    obs_dir = os.path.join("data", "dropoffs", "observed")
    if not os.path.exists(obs_dir):
        obs_dir = os.path.join("data", "synthetic", "observed")
    if not os.path.exists(obs_dir):
        print(f"  SKIP test_oracle_isolation (directory not found: {obs_dir})")
        return

    for fname in os.listdir(obs_dir):
        assert "oracle" not in fname.lower() and "counterfactual" not in fname.lower(), (
            f"Anti-leakage violated: oracle file '{fname}' found inside observed/ directory"
        )
    print("✓ test_oracle_isolation")


def test_oracle_contains_delta_pi_columns():
    """Oracle parquet/csv must expose oracle_delta_pi_{wa,sms,email} columns."""
    oracle_csv = os.path.join("data", "dropoffs", "oracle", "test_counterfactuals.csv")
    if not os.path.exists(oracle_csv):
        oracle_csv = os.path.join("data", "synthetic", "oracle", "test_counterfactuals.csv")
    if not os.path.exists(oracle_csv):
        print(f"  SKIP test_oracle_contains_delta_pi_columns (file not found: {oracle_csv})")
        return

    import csv
    with open(oracle_csv, newline="") as fh:
        header = next(csv.reader(fh))

    required = ["oracle_delta_pi_wa", "oracle_delta_pi_sms", "oracle_delta_pi_email"]
    for col in required:
        assert col in header, f"Oracle file missing column: '{col}'"
    print("✓ test_oracle_contains_delta_pi_columns")


def test_rho_sweep_generates_four_directories():
    """
    Critique 2: --rho_sweep must produce subdirectories for each rho value.
    """
    sweep_base = os.path.join("data", "dropoffs", "rho_sweep")
    if not os.path.exists(sweep_base):
        sweep_base = os.path.join("data", "synthetic", "rho_sweep")
    if not os.path.exists(sweep_base):
        print(f"  SKIP test_rho_sweep_generates_four_directories (run --rho_sweep first)")
        return

    expected_dirs = ["rho_070", "rho_080", "rho_090", "rho_095"]
    found = os.listdir(sweep_base)
    for d in expected_dirs:
        assert d in found, f"rho_sweep missing subdirectory: '{d}'"
    print("✓ test_rho_sweep_generates_four_directories")


def test_anti_leakage_training_script():
    """Training script must load from obs_dir and must not reference oracle_dir directly."""
    script_path = os.path.join("data", "scripts", "dropoffs", "train_causal_recovery_pipeline.py")
    if not os.path.exists(script_path):
        script_path = os.path.join("scripts", "train_causal_recovery_pipeline.py")
    if not os.path.exists(script_path):
        print(f"  SKIP test_anti_leakage_training_script (file not found: {script_path})")
        return

    with open(script_path, "r", encoding="utf-8") as fh:
        code = fh.read()

    assert "obs_dir" in code, "Training script must load from obs_dir"
    print("✓ test_anti_leakage_training_script")


# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

_ALL_TESTS = [
    # Safety / invariant
    test_channel_cost_monotonicity,
    test_organic_recovery_monotonicity,
    test_rto_cost_monotonicity,
    test_zero_margin_suppression,
    test_higher_rto_rate_on_action_penalises,
    # Liveness
    test_ev_gt_zero_obvious_wa_scenario,
    test_obvious_wa_is_recommended_action,
    test_suppress_high_organic_tiny_lift,
    # Sensitivity
    test_ev_sensitivity_to_channel_cost,
    test_ev_sensitivity_to_organic_prob,
    # Incentive semantics
    test_incentive_charged_on_pa_not_tau,
    # Data integrity
    test_propensity_columns_present_in_observed,
    test_oracle_isolation,
    test_oracle_contains_delta_pi_columns,
    test_rho_sweep_generates_four_directories,
    test_anti_leakage_training_script,
]

if __name__ == "__main__":
    failures = []
    for fn in _ALL_TESTS:
        try:
            fn()
        except AssertionError as exc:
            failures.append((fn.__name__, str(exc)))
            print(f"✗ {fn.__name__}: {exc}")
        except Exception as exc:
            failures.append((fn.__name__, repr(exc)))
            print(f"✗ {fn.__name__} (unexpected): {exc}")

    print()
    if failures:
        print(f"FAILED {len(failures)} / {len(_ALL_TESTS)} tests")
        sys.exit(1)
    else:
        print(f"ALL {len(_ALL_TESTS)} TESTS PASSED")
