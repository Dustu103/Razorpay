import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from data_generator import DataGenerator
from config import MODELS_DIR
from schemas import FalseDeclineInput, FalseDeclineOutput

class FeatureDModel:
    def __init__(self):
        self.model_path = os.path.join(MODELS_DIR, "feature_d.joblib")
        self.mc_map = {
            "electronics": 0,
            "travel": 1,
            "gaming": 2,
            "services": 3,
            "retail": 4
        }
        self.model = self._load_or_train()

    def _load_or_train(self):
        if os.path.exists(self.model_path):
            return joblib.load(self.model_path)
        return self.train_model()

    def train_model(self):
        df = DataGenerator.generate_fraud_data()
        X = df[["amount", "transaction_velocity", "is_known_device", "ip_risk_score", "merchant_category_encoded", "transaction_hour"]]
        y = df["is_fraud"]
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X, y)
        joblib.dump(clf, self.model_path)
        return clf

    def predict(self, input_data: FalseDeclineInput) -> FalseDeclineOutput:
        mc_encoded = self.mc_map.get(input_data.merchant_category.lower(), 4)
        features = [[
            input_data.amount,
            input_data.transaction_velocity,
            input_data.is_known_device,
            input_data.ip_risk_score,
            mc_encoded,
            input_data.transaction_hour
        ]]
        
        fraud_prob = self.model.predict_proba(features)[0][1]
        false_decline_prob = 1.0 - fraud_prob
        
        action = "reverify_and_reverse" if false_decline_prob >= 0.80 else "uphold_block"
        
        contributions = []
        if input_data.ip_risk_score < 0.25:
            contributions.append("low_ip_risk")
        if input_data.transaction_velocity < 3:
            contributions.append("low_transaction_velocity")
        if input_data.is_known_device == 1:
            contributions.append("known_device")
        if input_data.amount < 5000:
            contributions.append("normal_amount")
        if input_data.transaction_hour >= 9 and input_data.transaction_hour <= 22:
            contributions.append("normal_business_hours")
            
        return FalseDeclineOutput(
            false_decline_likelihood=float(false_decline_prob),
            recommended_action=action,
            contributing_features=contributions
        )