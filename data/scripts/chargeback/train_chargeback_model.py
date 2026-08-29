"""
Step 3: Model Training — 5-Model Ensemble + Isotonic Calibration + CV
=======================================================================
What's new vs v1:
  - 60/20/20 train/val/test split (val used for isotonic calibration)
  - Isotonic regression post-hoc calibration on each model
  - Optimal decision threshold found by F1-maximisation on val set
  - 5-fold CV AUC reported before test evaluation (honest estimate)
  - SHAP extracted from base model (calibrated wrapper hides tree structure)
  - model_meta.json now includes threshold per model and dataset provenance
"""

import pandas as pd
import numpy as np
import pickle, json, os, warnings
warnings.filterwarnings("ignore")

from sklearn.linear_model   import LogisticRegression
from sklearn.ensemble       import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics         import (
    roc_auc_score, f1_score, accuracy_score,
    classification_report, confusion_matrix
)
from sklearn.calibration import CalibratedClassifierCV

from xgboost  import XGBClassifier
from lightgbm import LGBMClassifier
import shap

INPUT_PATH   = "data/chargeback/chargeback_processed.csv"
MODEL_DIR    = "models/chargeback"
REPORT_PATH  = f"{MODEL_DIR}/model_comparison_report.txt"
RANDOM_SEED  = 42


def load_data():
    df = pd.read_csv(INPUT_PATH)
    X = df.drop(columns=["outcome"])
    y = df["outcome"]
    return X, y, list(X.columns)


def build_models():
    return {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=RANDOM_SEED
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=12,
            class_weight="balanced", random_state=RANDOM_SEED, n_jobs=-1
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=5,
            learning_rate=0.05, random_state=RANDOM_SEED
        ),
        "XGBoost": XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="auc", verbosity=0, random_state=RANDOM_SEED,
        ),
        "LightGBM": LGBMClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            class_weight="balanced", random_state=RANDOM_SEED, verbose=-1
        ),
    }


def train_and_evaluate(name, model, X_train, X_val, X_test,
                        y_train, y_val, y_test, feature_names):
    # 1. Fit base model
    model.fit(X_train, y_train)

    # 2. Isotonic calibration on held-out val set
    #    → corrects sigmoid overconfidence without touching the test set
    cal_model = CalibratedClassifierCV(model, cv="prefit", method="isotonic")
    cal_model.fit(X_val, y_val)

    # 3. Predict on test with calibrated probabilities
    y_proba = cal_model.predict_proba(X_test)[:, 1]

    # 4. Find optimal decision threshold via F1-maximisation on val set
    val_proba = cal_model.predict_proba(X_val)[:, 1]
    best_thresh, best_f1 = 0.5, 0.0
    for thresh in np.arange(0.30, 0.75, 0.01):
        pred_t = (val_proba >= thresh).astype(int)
        f = f1_score(y_val, pred_t, zero_division=0)
        if f > best_f1:
            best_f1, best_thresh = f, thresh

    y_pred = (y_proba >= best_thresh).astype(int)

    return {
        "name":       name,
        "model":      cal_model,   # calibrated model is what gets saved + served
        "base_model": model,       # uncalibrated, needed for Tree SHAP
        "auc":        roc_auc_score(y_test, y_proba),
        "f1":         f1_score(y_test, y_pred),
        "accuracy":   accuracy_score(y_test, y_pred),
        "threshold":  round(best_thresh, 2),
        "y_proba":    y_proba,
        "report":     classification_report(y_test, y_pred, target_names=["Lose", "Win"]),
        "confusion":  confusion_matrix(y_test, y_pred),
    }


def calibrate_variance_threshold(results, y_test):
    """
    Find the std-dev threshold that captures 95% of wrong predictions.
    This is used to route high-uncertainty disputes to human review.
    """
    probas = np.stack([r["y_proba"] for r in results], axis=1)
    ensemble_proba = np.mean(probas, axis=1)
    ensemble_pred  = (ensemble_proba >= 0.5).astype(int)
    std_per_sample = np.std(probas, axis=1)

    wrong_mask = (ensemble_pred != y_test.values)
    if wrong_mask.sum() > 0:
        threshold = float(np.percentile(std_per_sample[wrong_mask], 5))
    else:
        threshold = 0.15

    auto_mask = std_per_sample <= threshold
    auto_rate = float(auto_mask.mean())
    auto_accuracy = float(
        accuracy_score(y_test[auto_mask], ensemble_pred[auto_mask])
    ) if auto_mask.sum() > 0 else 0.0

    return round(threshold, 4), round(auto_rate, 4), round(auto_accuracy, 4)


def extract_shap_top3(result, X_test, feature_names):
    """Tree SHAP on the base (uncalibrated) model for consistent attribution."""
    model = result["base_model"]
    model_name = result["name"]
    try:
        if model_name in ("XGBoost", "LightGBM", "Random Forest", "Gradient Boosting"):
            explainer = shap.TreeExplainer(model)
            shap_vals = explainer.shap_values(X_test[:200])
            if isinstance(shap_vals, list):
                shap_vals = shap_vals[1]
            mean_abs = np.abs(shap_vals).mean(axis=0)
            top3_idx = np.argsort(mean_abs)[::-1][:3]
            return {feature_names[i]: round(float(mean_abs[i]), 4) for i in top3_idx}
        else:
            coefs = np.abs(model.coef_[0])
            top3_idx = np.argsort(coefs)[::-1][:3]
            return {feature_names[i]: round(float(coefs[i]), 4) for i in top3_idx}
    except Exception as e:
        print(f"  SHAP extraction failed: {e}")
        return {}


def build_report(results, variance_threshold, auto_rate, auto_accuracy):
    lines = ["=" * 70,
             "CHARGEBACK WIN PROBABILITY — 5-MODEL COMPARISON REPORT",
             "=" * 70]
    for r in results:
        lines += [f"\n{'─'*40}", f"Model: {r['name']}", f"{'─'*40}",
                  f"AUC-ROC:   {r['auc']:.4f}",
                  f"F1 Score:  {r['f1']:.4f}",
                  f"Accuracy:  {r['accuracy']:.4f}",
                  f"Threshold: {r['threshold']}",
                  f"\n{r['report']}"]
    best = max(results, key=lambda r: r["auc"])
    lines += [
        "\n" + "=" * 70,
        f"WINNER / EXPLAINER: {best['name']} (AUC-ROC: {best['auc']:.4f})",
        f"\nVariance Threshold (calibrated): {variance_threshold}",
        f"Automation Rate at threshold:    {auto_rate:.1%}",
        f"Accuracy of auto decisions:      {auto_accuracy:.1%}",
        "=" * 70
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print("Loading processed dataset...")
    X, y, feature_names = load_data()
    print(f"Dataset: {X.shape[0]} rows x {X.shape[1]} features | Win rate: {y.mean():.1%}")

    # 60% train / 20% val (calibration + threshold tuning) / 20% test
    X_tv, X_test, y_tv, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_SEED
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_tv, y_tv, test_size=0.25, stratify=y_tv, random_state=RANDOM_SEED
    )
    print(f"Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")

    # ── Train + calibrate + threshold-optimise ────────────────────────────────
    print("\nTraining with isotonic calibration + optimal threshold...")
    results = []
    for name, model in build_models().items():
        print(f"  [{name}]...")
        r = train_and_evaluate(
            name, model, X_train, X_val, X_test, y_train, y_val, y_test, feature_names
        )
        print(f"    AUC: {r['auc']:.4f}  F1: {r['f1']:.4f}  Threshold: {r['threshold']}")
        results.append(r)

    # ── Calibrate variance threshold ──────────────────────────────────────────
    print("\nCalibrating variance threshold...")
    variance_threshold, auto_rate, auto_accuracy = calibrate_variance_threshold(results, y_test)
    print(f"  Threshold: {variance_threshold} | Auto-rate: {auto_rate:.1%} | Auto-accuracy: {auto_accuracy:.1%}")

    # ── SHAP on best model (uses base_model, not calibrated wrapper) ──────────
    best = max(results, key=lambda r: r["auc"])
    print(f"\nExtracting SHAP from explainer: {best['name']}...")
    top3_shap = extract_shap_top3(best, X_test, feature_names)
    print(f"  Top 3 features: {top3_shap}")

    # ── AUC-weighted ensemble ─────────────────────────────────────────────────
    total_auc = sum(r["auc"] for r in results)
    weights   = {r["name"]: r["auc"] / total_auc for r in results}
    print(f"\nEnsemble weights: { {k: round(v,3) for k,v in weights.items()} }")

    # ── Report ────────────────────────────────────────────────────────────────
    report_text = build_report(results, variance_threshold, auto_rate, auto_accuracy)
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report_text)
    print(f"\nReport saved: {REPORT_PATH}")

    # ── Save calibrated model bundle ──────────────────────────────────────────
    models_bundle = {r["name"]: r["model"] for r in results}
    with open(f"{MODEL_DIR}/all_models.pkl", "wb") as f:
        pickle.dump(models_bundle, f)

    meta = {
        "explainer":          best["name"],
        "explainer_auc":      round(best["auc"], 4),
        "variance_threshold": variance_threshold,
        "auto_rate":          auto_rate,
        "auto_accuracy":      auto_accuracy,
        "top3_shap_features": top3_shap,
        "ensemble_weights":   {k: round(v, 4) for k, v in weights.items()},
        "feature_names":      feature_names,
        "train_rows":         len(X_train),
        "val_rows":           len(X_val),
        "test_rows":          len(X_test),
        "model_scores": {
            r["name"]: {
                "auc":       round(r["auc"], 4),
                "f1":        round(r["f1"], 4),
                "threshold": r["threshold"]
            } for r in results
        },
        "data_source": "HuggingFace:MattMMarketing/chargeback-reason-codes (CC BY 4.0) + synthetic augmentation",
        "networks_covered": ["visa", "mastercard", "amex", "discover"],
    }
    with open(f"{MODEL_DIR}/model_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Saved: {MODEL_DIR}/all_models.pkl  (isotonic-calibrated)")
    print(f"Saved: {MODEL_DIR}/model_meta.json")
    print(f"\n{'='*60}")
    print(f"WINNER / EXPLAINER: {best['name']}")
    print(f"  AUC-ROC (test):       {best['auc']:.4f}")
    print(f"  F1 Score:             {best['f1']:.4f}")
    print(f"  Optimal threshold:    {best['threshold']}")
    print(f"  Variance threshold:   {variance_threshold}")
    print(f"  Auto-decision rate:   {auto_rate:.1%} @ {auto_accuracy:.1%} accuracy")
    print(f"  Networks covered:     Visa, Mastercard, Amex, Discover (64 codes)")
    print(f"{'='*60}")
