import os
import joblib
from pydantic import BaseModel
from typing import List, Dict, Any

class FalseDeclineInput(BaseModel):
    amount: float
    transaction_velocity: int
    is_known_device: int
    ip_risk_score: float
    merchant_category: str
    transaction_hour: int

class FalseDeclineOutput(BaseModel):
    false_decline_likelihood: float
    recommended_action: str
    contributing_features: List[str]

class FalseDeclineModel:
    def __init__(self, model_dir: str):
        self.model_path = os.path.join(model_dir, "feature_d.joblib")
        self.mc_map = {
            "electronics": 0,
            "travel": 1,
            "gaming": 2,
            "services": 3,
            "retail": 4
        }
        self.model = None
        
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"Loaded False Decline model from {self.model_path}")
        else:
            print(f"WARNING: False Decline model not found at {self.model_path}")

    def predict(self, input_data: FalseDeclineInput) -> FalseDeclineOutput:
        if self.model is None:
            raise ValueError("False Decline model is not loaded")
            
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
