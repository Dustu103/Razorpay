"""
Causal Drop-Off Recovery Training & Policy Evaluation Pipeline
=============================================================
Strictly obeys causal boundaries:
1. Training reads ONLY from data/synthetic/observed/ (train & validation).
2. Fits estimated propensity model pi_hat(A|X).
3. Trains Baseline 1 (S-Learner with X x A interactions) and Baseline 2 (T-Learner).
4. Trains Downside Risk Model P(RTO=1 | X, A, Y=1) on converted orders.
5. Evaluates policies against hidden Oracle on test world:
   - Evaluates: Never Intervene, Always WhatsApp, Naive Propensity, S-Learner Net-EV, T-Learner Net-EV, Oracle.
   - Computes: Net Profit (INR), Recovered Cart (INR), Channel Costs (INR), RTO Losses (INR), Policy Regret (INR).
6. Exports production-ready causal model artifacts to backend/inference-service/app/models/ml/.
"""

import os
import argparse
import joblib
from typing import Dict, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
import lightgbm as lgb              

# ── Feature Preprocessing ───────────────────────────────────────────────────

CATEGORICAL_COLS = ["payment_method", "device", "diagnosis"]
NUMERICAL_COLS = [
    "cart_value", "duration_sec", "attempt_count", "events_count",
    "sequence_entropy", "mean_inter_event_time", "is_returning_customer"
]

class FeaturePreprocessor:
    def __init__(self):
        self.encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        self.feature_names = []

    def fit(self, df: pd.DataFrame):
        self.encoder.fit(df[CATEGORICAL_COLS])
        cat_feature_names = list(self.encoder.get_feature_names_out(CATEGORICAL_COLS))
        self.feature_names = NUMERICAL_COLS + cat_feature_names
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        num_data = df[NUMERICAL_COLS].values
        cat_data = self.encoder.transform(df[CATEGORICAL_COLS])
        return np.hstack([num_data, cat_data])


# ── S-Learner with Action Interactions ──────────────────────────────────────

class SLearner:
    """
    S-Learner: Single model estimating P(Y=1 | X, A).
    Includes explicit interaction terms between X features and Action indicator.
    """
    def __init__(self, actions=("none", "whatsapp", "sms", "email")):
        self.actions = list(actions)
        self.action_to_idx = {a: i for i, a in enumerate(self.actions)}
        self.model = None

    def _build_features(self, X_base: np.ndarray, actions: pd.Series) -> np.ndarray:
        n = len(X_base)
        action_onehot = np.zeros((n, len(self.actions)))
        for i, a in enumerate(actions):
            if a in self.action_to_idx:
                action_onehot[i, self.action_to_idx[a]] = 1.0
        
        # Explicit interaction between base features and action indicators
        interactions = []
        for a_idx in range(len(self.actions)):
            a_col = action_onehot[:, a_idx:a_idx+1]
            interactions.append(X_base * a_col)
        interactions = np.hstack(interactions)
        
        return np.hstack([X_base, action_onehot, interactions])

    def fit(self, X_base: np.ndarray, actions: pd.Series, y: np.ndarray):
        X_all = self._build_features(X_base, actions)
        neg_count = (y == 0).sum()
        pos_count = max(1, (y == 1).sum())
        scale_pos_weight = neg_count / pos_count

        self.model = lgb.LGBMClassifier(
            n_estimators=150,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=40,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            verbose=-1
        )
        self.model.fit(X_all, y)
        return self

    def predict_action_prob(self, X_base: np.ndarray, action: str) -> np.ndarray:
        n = len(X_base)
        mock_actions = pd.Series([action] * n)
        X_all = self._build_features(X_base, mock_actions)
        return self.model.predict_proba(X_all)[:, 1]


# ── T-Learner (Separate Models per Action) ───────────────────────────────────

class TLearner:
    """
    T-Learner: Fits separate outcome models P(Y=1 | X, A=a) for each action.
    """
    def __init__(self, actions=("none", "whatsapp", "sms", "email")):
        self.actions = list(actions)
        self.models = {}

    def fit(self, X_base: np.ndarray, actions: pd.Series, y: np.ndarray):
        for a in self.actions:
            mask = (actions == a).values
            X_a = X_base[mask]
            y_a = y[mask]
            neg_count = (y_a == 0).sum()
            pos_count = max(1, (y_a == 1).sum())
            scale_w = neg_count / pos_count

            model = lgb.LGBMClassifier(
                n_estimators=100,
                learning_rate=0.05,
                num_leaves=25,
                min_child_samples=30,
                scale_pos_weight=scale_w,
                random_state=42,
                verbose=-1
            )
            model.fit(X_a, y_a)
            self.models[a] = model
        return self

    def predict_action_prob(self, X_base: np.ndarray, action: str) -> np.ndarray:
        return self.models[action].predict_proba(X_base)[:, 1]


# ── Downside Risk / RTO Model ───────────────────────────────────────────────

class RTOModel:
    """
    Predicts P(RTO=1 | X, A, Y=1) strictly trained on converted orders.
    Conditions on action A using action one-hot and interaction terms,
    matching the InterventionModel and S-Learner architecture.
    """
    def __init__(self, actions=("none", "whatsapp", "sms", "email")):
        self.actions = list(actions)
        self.action_to_idx = {a: i for i, a in enumerate(self.actions)}
        self.model = None

    def _build_features(self, X_base: np.ndarray, actions: pd.Series) -> np.ndarray:
        n = len(X_base)
        action_onehot = np.zeros((n, len(self.actions)))
        for i, a in enumerate(actions):
            if a in self.action_to_idx:
                action_onehot[i, self.action_to_idx[a]] = 1.0

        interactions = []
        for a_idx in range(len(self.actions)):
            a_col = action_onehot[:, a_idx:a_idx+1]
            interactions.append(X_base * a_col)
        interactions = np.hstack(interactions)

        return np.hstack([X_base, action_onehot, interactions])

    def fit(self, X_base: np.ndarray, actions: pd.Series, rto_target: np.ndarray, y: np.ndarray):
        # Strictly train on orders that were completed/recovered
        converted_mask = (y == 1)
        X_conv = X_base[converted_mask]
        actions_conv = actions.iloc[converted_mask] if isinstance(actions, pd.Series) else actions[converted_mask]
        rto_conv = rto_target[converted_mask]

        X_all_conv = self._build_features(X_conv, actions_conv)
        self.model = lgb.LGBMClassifier(
            n_estimators=80,
            learning_rate=0.05,
            num_leaves=20,
            random_state=42,
            verbose=-1
        )
        self.model.fit(X_all_conv, rto_conv)
        return self

    def predict_rto_prob(self, X_base: np.ndarray, action: str) -> np.ndarray:
        n = len(X_base)
        mock_actions = pd.Series([action] * n)
        X_all = self._build_features(X_base, mock_actions)
        return self.model.predict_proba(X_all)[:, 1]


# ── Propensity Estimator ───────────────────────────────────────────────────

class PropensityModel:
    """
    Estimates pi_hat_0(A | X) from logged training data using multinomial logistic regression.
    """
    def __init__(self, actions=("none", "whatsapp", "sms", "email")):
        self.actions = list(actions)
        self.model = LogisticRegression(max_iter=1000, random_state=42)

    def fit(self, X_base: np.ndarray, actions: pd.Series):
        self.model.fit(X_base, actions)
        return self

    def predict_propensities(self, X_base: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X_base)


# ── Policy Evaluation Engine ────────────────────────────────────────────────

def evaluate_economic_policies(
    df_test_obs: pd.DataFrame,
    df_test_oracle: pd.DataFrame,
    X_test_base: np.ndarray,
    s_learner: SLearner,
    t_learner: TLearner,
    rto_model: RTOModel,
    merchant_margin: float = 0.25,
    rto_cost: float = 250.0,
    cost_wa: float = 0.80,
    cost_sms: float = 0.20,
    cost_email: float = 0.05,
    incentive_wa: float = 0.0,
    incentive_sms: float = 0.0,
    incentive_email: float = 0.0
) -> pd.DataFrame:
    """
    Evaluates policies on test data against true counterfactual outcomes.
    Exact Decision formula:
    Delta Pi_a = P_a * [(1 - r_a)(C*M - D_a) - r_a*K_rto] - P_0 * [(1 - r_0)C*M - r_0*K_rto] - K_a
    """
    n = len(df_test_obs)
    C = df_test_obs["cart_value"].values
    
    # Costs and incentives
    costs = {"none": 0.0, "whatsapp": cost_wa, "sms": cost_sms, "email": cost_email}
    incentives = {"none": 0.0, "whatsapp": incentive_wa, "sms": incentive_sms, "email": incentive_email}
    
    # 1. Model Predictions
    p_hat_s = {
        "none": s_learner.predict_action_prob(X_test_base, "none"),
        "whatsapp": s_learner.predict_action_prob(X_test_base, "whatsapp"),
        "sms": s_learner.predict_action_prob(X_test_base, "sms"),
        "email": s_learner.predict_action_prob(X_test_base, "email")
    }
    
    p_hat_t = {
        "none": t_learner.predict_action_prob(X_test_base, "none"),
        "whatsapp": t_learner.predict_action_prob(X_test_base, "whatsapp"),
        "sms": t_learner.predict_action_prob(X_test_base, "sms"),
        "email": t_learner.predict_action_prob(X_test_base, "email")
    }
    
    r_hat = {
        "none": rto_model.predict_rto_prob(X_test_base, "none"),
        "whatsapp": rto_model.predict_rto_prob(X_test_base, "whatsapp"),
        "sms": rto_model.predict_rto_prob(X_test_base, "sms"),
        "email": rto_model.predict_rto_prob(X_test_base, "email"),
    }
    
    # 2. Decision Rules (Action Assignment per Policy)
    policies = {}
    
    # Policy 0: Never Intervene (Organic Baseline)
    policies["Never Intervene"] = np.array(["none"] * n)
    
    # Policy 1: Always WhatsApp (Naive commercial tool)
    policies["Always WhatsApp"] = np.array(["whatsapp"] * n)
    
    # Policy 2: Naive High Propensity (Sends WA if P_wa > 0.50, ignoring organic P0)
    policies["Naive Propensity (>50%)"] = np.where(p_hat_s["whatsapp"] > 0.50, "whatsapp", "none")
    
    # Helper to compute argmax Delta Pi
    def decide_policy(p_preds: Dict[str, np.ndarray]) -> np.ndarray:
        decisions = []
        p0 = p_preds["none"]
        r0 = r_hat["none"]
        # Baseline profit under None
        base_profit = p0 * ((1.0 - r0) * (C * merchant_margin) - r0 * rto_cost)
        
        for i in range(n):
            best_action = "none"
            best_delta = 0.0  # Must beat doing nothing (delta > 0)
            
            for a in ["whatsapp", "sms", "email"]:
                pa = p_preds[a][i]
                ra = r_hat[a][i]
                d_a = incentives[a]
                k_a = costs[a]
                
                action_profit = pa * ((1.0 - ra) * (C[i] * merchant_margin - d_a) - ra * rto_cost) - k_a
                delta_pi = action_profit - base_profit[i]
                
                if delta_pi > best_delta:
                    best_delta = delta_pi
                    best_action = a
            decisions.append(best_action)
        return np.array(decisions)
    
    # Policy 3: S-Learner Net-EV Policy
    policies["S-Learner Net-EV"] = decide_policy(p_hat_s)
    
    # Policy 4: T-Learner Net-EV Policy
    policies["T-Learner Net-EV"] = decide_policy(p_hat_t)
    
    # Policy 5: True Oracle Policy (uses true hidden probabilities from oracle dataset)
    true_p = {
        "none": df_test_oracle["P0"].values,
        "whatsapp": df_test_oracle["P_wa"].values,
        "sms": df_test_oracle["P_sms"].values,
        "email": df_test_oracle["P_email"].values
    }
    true_r = {
        "none": df_test_oracle["r0"].values,
        "whatsapp": df_test_oracle["r_wa"].values,
        "sms": df_test_oracle["r_sms"].values,
        "email": df_test_oracle["r_email"].values
    }
    
    oracle_decisions = []
    for i in range(n):
        best_a = "none"
        best_delta = 0.0
        p0_true = true_p["none"][i]
        r0_true = true_r["none"][i]
        base_prof_true = p0_true * ((1.0 - r0_true) * (C[i] * merchant_margin) - r0_true * rto_cost)
        
        for a in ["whatsapp", "sms", "email"]:
            pa_true = true_p[a][i]
            ra_true = true_r[a][i]
            d_a = incentives[a]
            k_a = costs[a]
            act_prof_true = pa_true * ((1.0 - ra_true) * (C[i] * merchant_margin - d_a) - ra_true * rto_cost) - k_a
            delta = act_prof_true - base_prof_true
            if delta > best_delta:
                best_delta = delta
                best_a = a
        oracle_decisions.append(best_a)
    policies["True Oracle"] = np.array(oracle_decisions)
    
    # 3. Simulate Financial Outcomes under each Policy using Counterfactual Realizations
    results = []
    
    # Map realized outcomes from Oracle table
    outcome_map = {
        "none": (df_test_oracle["Y0"].values, df_test_oracle["RTO0"].values),
        "whatsapp": (df_test_oracle["Y_wa"].values, df_test_oracle["RTO_wa"].values),
        "sms": (df_test_oracle["Y_sms"].values, df_test_oracle["RTO_sms"].values),
        "email": (df_test_oracle["Y_email"].values, df_test_oracle["RTO_email"].values)
    }
    
    oracle_profit = None
    
    for pol_name, actions in policies.items():
        total_recovered_cart = 0.0
        total_channel_cost = 0.0
        total_rto_cost = 0.0
        total_gross_margin = 0.0
        total_incentive_spent = 0.0
        total_interventions = 0
        total_recovered_orders = 0
        total_rto_count = 0
        
        for i in range(n):
            a = actions[i]
            y_realized, rto_realized = outcome_map[a]
            y = y_realized[i]
            rto = rto_realized[i]
            
            k_a = costs[a]
            d_a = incentives[a]
            
            if a != "none":
                total_interventions += 1
                total_channel_cost += k_a
                
            if y == 1:
                total_recovered_orders += 1
                total_recovered_cart += C[i]
                if rto == 1:
                    total_rto_count += 1
                    total_rto_cost += rto_cost
                else:
                    total_gross_margin += C[i] * merchant_margin
                    total_incentive_spent += d_a
                    
        net_profit = total_gross_margin - total_incentive_spent - total_rto_cost - total_channel_cost
        
        if pol_name == "True Oracle":
            oracle_profit = net_profit
            
        results.append({
            "Policy": pol_name,
            "Interventions": total_interventions,
            "Intervention Rate (%)": round(100.0 * total_interventions / n, 1),
            "Recovered Orders": total_recovered_orders,
            "RTO Count": total_rto_count,
            "Recovered Cart (INR)": round(total_recovered_cart, 2),
            "Channel Cost (INR)": round(total_channel_cost, 2),
            "RTO Loss (INR)": round(total_rto_cost, 2),
            "Net Profit (INR)": round(net_profit, 2),
        })
        
    df_res = pd.DataFrame(results)
    df_res["Policy Regret (INR)"] = np.round(oracle_profit - df_res["Net Profit (INR)"], 2)
    return df_res


# ── Main Training & Execution ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Train causal recovery pipeline and evaluate against Oracle.")
    default_data = "data/dropoffs" if os.path.exists("data/dropoffs") else "data/synthetic"
    parser.add_argument("--data_dir", type=str, default=default_data, help="Data directory path")
    parser.add_argument("--models_dir", type=str, default="backend/inference-service/app/models/ml", help="Model export dir")
    args = parser.parse_args()
    
    obs_dir = os.path.join(args.data_dir, "observed")
    oracle_dir = os.path.join(args.data_dir, "oracle")
    
    # 1. Load strictly from observed datasets for training
    train_path = os.path.join(obs_dir, "train.csv")
    val_path = os.path.join(obs_dir, "validation.csv")
    test_path = os.path.join(obs_dir, "test.csv")
    
    print("="*75)
    print("Causal Recovery Pipeline Training")
    print(f"Loading observed training data from: {train_path}")
    df_train = pd.read_csv(train_path)
    df_val = pd.read_csv(val_path)
    df_test_obs = pd.read_csv(test_path)
    
    # 2. Fit Feature Preprocessor
    print("Fitting Feature Preprocessor...")
    preprocessor = FeaturePreprocessor().fit(df_train)
    X_train = preprocessor.transform(df_train)
    X_val = preprocessor.transform(df_val)
    X_test = preprocessor.transform(df_test_obs)
    
    y_train = df_train["realized_outcome"].values
    actions_train = df_train["assigned_action"]
    rto_train = df_train["realized_rto"].values
    
    # 3. Fit Propensity Estimator (pi_hat_0)
    print("Fitting Propensity Estimator (pi_hat(A|X))...")
    propensity_model = PropensityModel().fit(X_train, actions_train)
    
    # 4. Train Baseline 1: S-Learner with Interactions
    print("Training Baseline 1: S-Learner with explicit X x A interaction terms...")
    s_learner = SLearner().fit(X_train, actions_train, y_train)
    
    # 5. Train Baseline 2: T-Learner (Separate Models per Action)
    print("Training Baseline 2: T-Learner (separate models per action)...")
    t_learner = TLearner().fit(X_train, actions_train, y_train)
    
    # 6. Train Downside Risk / RTO Model
    print("Training Downside Risk Model P(RTO=1 | X, A, Y=1)...")
    rto_model = RTOModel().fit(X_train, actions_train, rto_train, y_train)
    
    # 7. Evaluate on Hidden Test World (Oracle)
    oracle_test_path = os.path.join(oracle_dir, "test_counterfactuals.csv")
    print(f"\nLoading Oracle Test World for Policy Regret Evaluation from: {oracle_test_path}")
    df_test_oracle = pd.read_csv(oracle_test_path)
    
    print("\nRunning Financial Evaluation across all policies on 7,500 test drop-offs...")
    eval_df = evaluate_economic_policies(
        df_test_obs=df_test_obs,
        df_test_oracle=df_test_oracle,
        X_test_base=X_test,
        s_learner=s_learner,
        t_learner=t_learner,
        rto_model=rto_model,
        merchant_margin=0.25,
        rto_cost=250.0,
        cost_wa=0.80,
        cost_sms=0.20,
        cost_email=0.05
    )
    
    print("\n" + "="*85)
    print("POLICY FINANCIAL EVALUATION RESULTS (INR):")
    print(eval_df.to_string(index=False))
    print("="*85 + "\n")
    
    # 8. Export Production Artifacts
    import json
    metadata = {
        "actions": s_learner.actions,
        "categorical_cols": CATEGORICAL_COLS,
        "numerical_cols": NUMERICAL_COLS,
        "feature_names": preprocessor.feature_names
    }
    
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    target_dirs = [args.models_dir, os.path.join(repo_root, "models", "ml")]
    for out_dir in target_dirs:
        os.makedirs(out_dir, exist_ok=True)
        # Export native models without custom class wrapper dependencies
        joblib.dump(preprocessor.encoder, os.path.join(out_dir, "causal_preprocessor_encoder.pkl"))
        joblib.dump(s_learner.model, os.path.join(out_dir, "causal_s_model.pkl"))
        joblib.dump(rto_model.model, os.path.join(out_dir, "causal_rto_model.pkl"))
        joblib.dump(propensity_model.model, os.path.join(out_dir, "causal_propensity_clf.pkl"))
        
        with open(os.path.join(out_dir, "causal_metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
            
        print(f"All native causal model artifacts successfully exported to: {out_dir}")
    print()

if __name__ == "__main__":
    main()
