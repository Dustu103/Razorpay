"""
Multi-Run Real-World Benchmark & Accuracy Evaluation
===================================================
Evaluates the Causal Drop-Off Recovery Engine across:
1. Multiple seeds (5 trials) to compute solid averages & std devs.
2. Distinct real-world merchant traffic verticals:
   - High-Ticket D2C / Electronics (High cart, 35% margin)
   - Fashion & Apparel (COD-heavy, high RTO risk)
   - Quick-Commerce / Essentials (Low cart ₹500, 15% margin, high organic)
   - Digital Goods / Subscriptions (Zero RTO risk, 85% margin)
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score

# Ensure scripts and backend in path
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "backend", "inference-service"))

from scripts.generate_synthetic_dropoffs import generate_causal_dataset
from scripts.train_causal_recovery_pipeline import (
    FeaturePreprocessor,
    SLearner,
    TLearner,
    RTOModel,
    PropensityModel,
    evaluate_economic_policies
)


VERTICALS = {
    "D2C & Electronics": {
        "desc": "High Cart (₹4k-15k), 35% Margin, Moderate RTO",
        "margin": 0.35,
        "rto_cost": 250.0,
        "cost_wa": 0.80,
        "cost_sms": 0.20,
        "cost_email": 0.05,
    },
    "Fashion & Apparel": {
        "desc": "COD Heavy, High RTO Risk (30-40%), 45% Margin",
        "margin": 0.45,
        "rto_cost": 280.0,
        "cost_wa": 0.80,
        "cost_sms": 0.20,
        "cost_email": 0.05,
    },
    "Quick-Commerce / Grocery": {
        "desc": "Low Cart (₹400-900), Thin 15% Margin, High Organic",
        "margin": 0.15,
        "rto_cost": 150.0,
        "cost_wa": 0.80,
        "cost_sms": 0.20,
        "cost_email": 0.05,
    },
    "Digital Goods & SaaS": {
        "desc": "High Margin 85%, Zero RTO Risk",
        "margin": 0.85,
        "rto_cost": 0.0,
        "cost_wa": 0.80,
        "cost_sms": 0.20,
        "cost_email": 0.05,
    }
}


def run_single_experiment(seed: int, vertical_name: str, config: dict, n_samples: int = 10_000):
    # Generate data
    datasets = generate_causal_dataset(
        n_samples=n_samples,
        seed=seed,
        margin=config["margin"],
        rto_cost=config["rto_cost"],
        cost_wa=config["cost_wa"],
        cost_sms=config["cost_sms"],
        cost_email=config["cost_email"],
        output_dir=f"data/benchmark_tmp/{seed}_{vertical_name.replace(' ', '_')}"
    )

    df_train = datasets["train_obs"]
    df_val = datasets["val_obs"]
    df_test_obs = datasets["test_obs"]
    df_test_oracle = datasets["test_oracle"]

    # Preprocessing
    preprocessor = FeaturePreprocessor().fit(df_train)
    X_train = preprocessor.transform(df_train)
    X_test = preprocessor.transform(df_test_obs)

    y_train = df_train["realized_outcome"].values
    actions_train = df_train["assigned_action"]
    rto_train = df_train["realized_rto"].values

    y_test = df_test_obs["realized_outcome"].values
    actions_test = df_test_obs["assigned_action"]
    rto_test = df_test_obs["realized_rto"].values

    # Train S-Learner & RTO Model
    s_learner = SLearner().fit(X_train, actions_train, y_train)
    t_learner = TLearner().fit(X_train, actions_train, y_train)
    rto_model = RTOModel().fit(X_train, actions_train, rto_train, y_train)

    # 1. Model Predictive Accuracy on observational test split
    p_hat_test = np.zeros(len(df_test_obs))
    for a in s_learner.actions:
        mask = (actions_test == a).values
        if mask.sum() > 0:
            p_hat_test[mask] = s_learner.predict_action_prob(X_test[mask], a)

    # Calibrated decision threshold based on conversion base-rate
    base_rate = float(np.mean(y_train))
    pred_labels = (p_hat_test >= base_rate).astype(int)
    clf_acc = accuracy_score(y_test, pred_labels)
    clf_f1 = f1_score(y_test, pred_labels, zero_division=0)
    try:
        clf_auc = roc_auc_score(y_test, p_hat_test)
    except Exception:
        clf_auc = 0.50

    # RTO model accuracy on converted orders
    conv_mask = (y_test == 1)
    if conv_mask.sum() > 0:
        r_hat_test = np.zeros(conv_mask.sum())
        for a in rto_model.actions:
            sub_mask = (actions_test[conv_mask] == a).values
            if sub_mask.sum() > 0:
                r_hat_test[sub_mask] = rto_model.predict_rto_prob(X_test[conv_mask][sub_mask], a)
        rto_acc = accuracy_score(rto_test[conv_mask], (r_hat_test >= 0.50).astype(int))
    else:
        rto_acc = 0.0

    # 2. Economic Policy Performance
    eval_df = evaluate_economic_policies(
        df_test_obs=df_test_obs,
        df_test_oracle=df_test_oracle,
        X_test_base=X_test,
        s_learner=s_learner,
        t_learner=t_learner,
        rto_model=rto_model,
        merchant_margin=config["margin"],
        rto_cost=config["rto_cost"],
        cost_wa=config["cost_wa"],
        cost_sms=config["cost_sms"],
        cost_email=config["cost_email"]
    )

    s_row = eval_df[eval_df["Policy"] == "S-Learner Net-EV"].iloc[0]
    oracle_row = eval_df[eval_df["Policy"] == "True Oracle"].iloc[0]
    naive_row = eval_df[eval_df["Policy"] == "Always WhatsApp"].iloc[0]
    never_row = eval_df[eval_df["Policy"] == "Never Intervene"].iloc[0]

    # Policy Match Accuracy (How often did model pick Oracle's exact best action?)
    oracle_best_action = df_test_oracle.apply(
        lambda r: "whatsapp" if r["oracle_delta_pi_wa"] == max(0, r["oracle_delta_pi_wa"], r["oracle_delta_pi_sms"], r["oracle_delta_pi_email"]) and r["oracle_delta_pi_wa"] > 0
        else ("sms" if r["oracle_delta_pi_sms"] == max(0, r["oracle_delta_pi_sms"], r["oracle_delta_pi_email"]) and r["oracle_delta_pi_sms"] > 0
        else ("email" if r["oracle_delta_pi_email"] > 0 else "none")),
        axis=1
    ).values

    # Model decisions
    p_hat_s = {a: s_learner.predict_action_prob(X_test, a) for a in s_learner.actions}
    r_hat_s = {a: rto_model.predict_rto_prob(X_test, a) for a in rto_model.actions}
    C = df_test_obs["cart_value"].values
    costs = {"none": 0.0, "whatsapp": config["cost_wa"], "sms": config["cost_sms"], "email": config["cost_email"]}

    model_decisions = []
    for i in range(len(df_test_obs)):
        best_a = "none"
        best_d = 0.0
        p0 = p_hat_s["none"][i]
        r0 = r_hat_s["none"][i]
        base_prof = p0 * ((1.0 - r0) * (C[i] * config["margin"]) - r0 * config["rto_cost"])
        for a in ["whatsapp", "sms", "email"]:
            pa = p_hat_s[a][i]
            ra = r_hat_s[a][i]
            ka = costs[a]
            act_prof = pa * ((1.0 - ra) * (C[i] * config["margin"]) - ra * config["rto_cost"]) - ka
            d = act_prof - base_prof
            if d > best_d:
                best_d = d
                best_a = a
        model_decisions.append(best_a)
    model_decisions = np.array(model_decisions)

    policy_match_acc = accuracy_score(oracle_best_action, model_decisions)

    # Near-Optimal Economic Match: Captures >=85% of best Oracle profit
    col_map = {"whatsapp": "wa", "sms": "sms", "email": "email"}
    near_optimal_matches = 0
    for i in range(len(df_test_obs)):
        chosen = model_decisions[i]
        chosen_col = col_map.get(chosen, chosen)
        chosen_ev = 0.0 if chosen == "none" else df_test_oracle[f"oracle_delta_pi_{chosen_col}"].iloc[i]
        best_ev = max(0.0, df_test_oracle["oracle_delta_pi_wa"].iloc[i],
                           df_test_oracle["oracle_delta_pi_sms"].iloc[i],
                           df_test_oracle["oracle_delta_pi_email"].iloc[i])
        if best_ev <= 0.0:
            if chosen == "none":
                near_optimal_matches += 1
        else:
            if chosen_ev >= 0.85 * best_ev:
                near_optimal_matches += 1
    near_optimal_acc = near_optimal_matches / len(df_test_obs)

    return {
        "clf_acc": clf_acc,
        "clf_auc": clf_auc,
        "clf_f1": clf_f1,
        "rto_acc": rto_acc,
        "policy_match_acc": policy_match_acc,
        "near_optimal_acc": near_optimal_acc,
        "net_profit": s_row["Net Profit (INR)"],
        "oracle_profit": oracle_row["Net Profit (INR)"],
        "naive_profit": naive_row["Net Profit (INR)"],
        "never_profit": never_row["Net Profit (INR)"],
        "regret": s_row["Policy Regret (INR)"],
        "intervention_rate": s_row["Intervention Rate (%)"],
    }


def main():
    seeds = [42, 101, 2024, 888, 7]
    print("=" * 78)
    print(f"STARTING MULTI-RUN BENCHMARK: {len(seeds)} TRIALS x {len(VERTICALS)} VERTICALS")
    print("=" * 78)

    all_results = []

    for v_name, config in VERTICALS.items():
        print(f"\nEvaluating Vertical: {v_name} ({config['desc']})")
        v_runs = []
        for s in seeds:
            res = run_single_experiment(seed=s, vertical_name=v_name, config=config)
            v_runs.append(res)
            print(f"  [Seed {s}] Clf AUC={res['clf_auc']:.3f} | Policy Match={res['policy_match_acc']*100:.1f}% | Net Profit=₹{res['net_profit']:,.0f}")

        df_v = pd.DataFrame(v_runs)
        summary = {
            "Vertical": v_name,
            "Outcome AUC": f"{df_v['clf_auc'].mean():.3f} +/- {df_v['clf_auc'].std():.3f}",
            "Outcome F1 (Calibrated)": f"{df_v['clf_f1'].mean():.3f}",
            "RTO Acc": f"{df_v['rto_acc'].mean()*100:.1f}%",
            "Strict Match": f"{df_v['policy_match_acc'].mean()*100:.1f}%",
            "Near-Optimal Match": f"{df_v['near_optimal_acc'].mean()*100:.1f}% +/- {df_v['near_optimal_acc'].std()*100:.1f}%",
            "Net Profit (INR)": f"INR {df_v['net_profit'].mean():,.0f}",
            "Profit Lift vs Naive": f"+INR {df_v['net_profit'].mean() - df_v['naive_profit'].mean():,.0f}",
            "Profit Captured": f"{(df_v['net_profit'].mean() / df_v['oracle_profit'].mean())*100:.1f}%",
        }
        all_results.append(summary)

    res_df = pd.DataFrame(all_results)
    print("\n" + "=" * 90)
    print("FINAL MULTI-RUN BENCHMARK SUMMARY (AVERAGED OVER 5 RUNS):")
    print("=" * 90)
    print(res_df.to_string(index=False))
    print("=" * 90)

    # Clean up temp benchmark data
    import shutil
    if os.path.exists("data/benchmark_tmp"):
        shutil.rmtree("data/benchmark_tmp", ignore_errors=True)


if __name__ == "__main__":
    main()
