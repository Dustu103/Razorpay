import os
import joblib
from pydantic import BaseModel
from typing import List

class DunningInput(BaseModel):
    channel_encoded: int  # 0: Email, 1: SMS, 2: Push
    time_since_failure_mins: int
    customer_tenure_months: int
    prior_payment_success_rate: float

class DunningOutput(BaseModel):
    payment_probability: float
    recommended_channel: str

class DunningModel:
    def __init__(self, model_dir: str):
        self.model_path = os.path.join(model_dir, "feature_c.joblib")
        self.model = None
        
        self.channel_map = {
            0: "email",
            1: "sms",
            2: "push"
        }
        
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"Loaded Dunning Optimization model from {self.model_path}")
        else:
            print(f"WARNING: Dunning Optimization model not found at {self.model_path}")

    def predict(self, input_data: DunningInput) -> DunningOutput:
        if self.model is None:
            raise ValueError("Dunning Optimization model is not loaded")
            
        features = [[
            input_data.channel_encoded,
            input_data.time_since_failure_mins,
            input_data.customer_tenure_months,
            input_data.prior_payment_success_rate
        ]]
        
        prob = self.model.predict_proba(features)[0][1]
        channel_name = self.channel_map.get(input_data.channel_encoded, "email")
            
        return DunningOutput(
            payment_probability=float(prob),
            recommended_channel=channel_name
        )
