import os
import pickle
import json
import numpy as np
import pandas as pd

# Paths are relative to the root when running in Docker or local backend path
# We support loading from both relative paths: backend/chargeback-service/ or models/chargeback/
MODEL_DIR = os.getenv("CHARGEBACK_MODEL_DIR", "/app/models/chargeback")

class DisputeClassifier:
    def __init__(self):
        self.models = None
        self.meta = None
        self.scaler = None
        self.woe = None
        self.load_artifacts()

    def load_artifacts(self):
        # Locate files
        paths = [MODEL_DIR, "models/chargeback", "../../models/chargeback"]
        base_path = None
        for p in paths:
            if os.path.exists(os.path.join(p, "all_models.pkl")):
                base_path = p
                break
        
        if not base_path:
            raise FileNotFoundError("Could not find chargeback model artifacts directory")

        with open(os.path.join(base_path, "all_models.pkl"), "rb") as f:
            self.models = pickle.load(f)
        with open(os.path.join(base_path, "model_meta.json"), "r") as f:
            self.meta = json.load(f)
        with open(os.path.join(base_path, "feature_scaler.pkl"), "rb") as f:
            self.scaler = pickle.load(f)
        with open(os.path.join(base_path, "woe_encoder.json"), "r") as f:
            self.woe = json.load(f)

    def preprocess(self, raw_data: dict) -> pd.DataFrame:
        """Converts raw user dispute inputs into scaled one-hot features matching model input shape."""
        # 1. Start with base evidence features (0/1)
        data = {
            "has_3ds_auth":              int(raw_data.get("has_3ds_auth", 0)),
            "has_delivery_proof":        int(raw_data.get("has_delivery_proof", 0)),
            "has_avs_cvv_match":         int(raw_data.get("has_avs_cvv_match", 0)),
            "has_ip_device_fingerprint": int(raw_data.get("has_ip_device_fingerprint", 0)),
            "has_prior_comms":           int(raw_data.get("has_prior_comms", 0)),
            "has_signed_receipt":        int(raw_data.get("has_signed_receipt", 0)),
            "has_usage_logs":            int(raw_data.get("has_usage_logs", 0)),
            # Continuous features (raw)
            "days_remaining":            float(raw_data.get("days_remaining", 10)),
            "days_since_transaction":    float(raw_data.get("days_since_transaction", 30)),
            "repeat_dispute_count":      float(raw_data.get("repeat_dispute_count", 0)),
            "transaction_amount_inr":    float(raw_data.get("transaction_amount_inr", 1000)),
        }

        # 2. Evidence completeness score calculation
        from .reason_code_map import REASON_CODE_EVIDENCE_MAP
        code = raw_data.get("reason_code")
        rules = REASON_CODE_EVIDENCE_MAP.get(code, {})
        required = rules.get("required_evidence", [])
        
        if not required:
            data["evidence_completeness_score"] = 2.0
        else:
            present = sum(1 for r in required if data.get(r, 0) == 1)
            if present == 0:
                data["evidence_completeness_score"] = 0.0
            elif present < len(required):
                data["evidence_completeness_score"] = 1.0
            else:
                data["evidence_completeness_score"] = 2.0

        # 2.5. Interaction features
        evidence_cols = ["has_3ds_auth", "has_delivery_proof", "has_avs_cvv_match",
                         "has_ip_device_fingerprint", "has_prior_comms",
                         "has_signed_receipt", "has_usage_logs"]
        
        data["fraud_code_3ds"] = float(data.get("has_3ds_auth", 0))
        data["evidence_density"] = sum(data.get(c, 0) for c in evidence_cols)
        data["deadline_urgency"] = 1.0 - (data.get("days_remaining", 30) / 45.0)
        # ₹10,000 threshold for Indian market — issuers apply intensive manual
        # review above this amount, increasing representment complexity.
        data["high_value_flag"] = 1.0 if data.get("transaction_amount_inr", 0) > 10000 else 0.0
        
        repeat = data.get("repeat_dispute_count", 0)
        data["repeat_fraud_signal"] = 1.0 / (1.0 + repeat) if repeat > 0 else 1.0
        
        if data.get("evidence_completeness_score") == 2.0 and data.get("has_prior_comms") == 1:
            data["full_evidence_with_comms"] = 1.0
        else:
            data["full_evidence_with_comms"] = 0.0

        # 3. WoE encode merchant_category
        cat = raw_data.get("merchant_category", "ecommerce")
        data["merchant_category_woe"] = float(self.woe.get(cat, self.woe.get("ecommerce", 0.0)))

        # 4. Scale continuous features
        scale_cols = [
            "days_remaining", "days_since_transaction", "transaction_amount_inr",
            "repeat_dispute_count", "evidence_density", "deadline_urgency",
            "repeat_fraud_signal"
        ]
        # We need a dataframe to fit/transform correctly
        scale_df = pd.DataFrame([data])
        scale_df[scale_cols] = self.scaler.transform(scale_df[scale_cols])
        
        # 5. One-hot encode reason_code and network
        for f in self.meta["feature_names"]:
            if f.startswith("reason_code_") or f.startswith("network_"):
                scale_df[f] = 0.0

        network = raw_data.get("network", "visa").lower()
        if f"network_{network}" in self.meta["feature_names"]:
            scale_df[f"network_{network}"] = 1.0
        if f"reason_code_{code}" in self.meta["feature_names"]:
            scale_df[f"reason_code_{code}"] = 1.0

        # Align exact columns sequence
        final_df = scale_df[self.meta["feature_names"]]
        return final_df

    def predict(self, raw_data: dict) -> dict:
        """Runs predictions across 5 models, performs weighted ensemble averaging & variance calculation."""
        df = self.preprocess(raw_data)
        
        individual_probs = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for name, model in self.models.items():
            prob = float(model.predict_proba(df)[0, 1])
            individual_probs[name] = round(prob, 4)
            weight = self.meta["ensemble_weights"].get(name, 1.0)
            weighted_sum += prob * weight
            total_weight += weight

        ensemble_prob = weighted_sum / total_weight
        
        # Variance (Standard Deviation)
        probs_list = list(individual_probs.values())
        std_dev = float(np.std(probs_list))

        # Check against calibrated variance threshold with a lower bound of 0.10 to prevent noise
        threshold = max(0.10, self.meta.get("variance_threshold", 0.15))
        disagreement_flag = std_dev > threshold

        # Extract top 3 SHAP features from explainer model if required
        explainer_name = self.meta.get("explainer", "XGBoost")
        top3_features = list(self.meta.get("top3_shap_features", {}).keys())

        # ── Normalize to 3 clean actions ───────────────────────────────────────────────
        # auto_submit   → strong evidence, fight the dispute
        # deflect_via_refund → issue refund, protect VAMP ratio
        # review         → high uncertainty or deadline pressure, human triage
        recommended_action = "review"
        
        # Rule 1: Under 2 days remaining → No time for review, force deflect
        if raw_data.get("days_remaining", 14) <= 2:
            recommended_action = "deflect_via_refund"
        # Rule 2: High disagreement AND very low win rate → clear loss, deflect
        elif disagreement_flag and ensemble_prob < 0.35:
            recommended_action = "deflect_via_refund"
        # Rule 3: Low disagreement (models agree)
        elif not disagreement_flag:
            if ensemble_prob >= 0.70:
                recommended_action = "auto_submit"
            elif ensemble_prob >= 0.40:
                recommended_action = "review"   # moderate — needs merchant confirmation
            else:
                recommended_action = "deflect_via_refund"
        # Rule 4: High disagreement without clear loss → human triage
        else:
            recommended_action = "review"

        return {
            "win_probability":    round(ensemble_prob, 4),
            "variance":           round(std_dev, 4),
            "disagreement_flag": disagreement_flag,
            "individual_predictions": individual_probs,
            "recommended_action": recommended_action,
            "top_features":      top3_features,
            "variance_threshold": threshold
        }
