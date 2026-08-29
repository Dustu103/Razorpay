import os
import joblib
from pydantic import BaseModel
from typing import List

class RetryRoutingInput(BaseModel):
    hour_of_day: int
    day_of_month: int
    failure_cause_encoded: int
    payment_method_encoded: int
    retry_count: int
    time_since_failure_mins: int

class RetryRoutingOutput(BaseModel):
    retry_success_probability: float
    recommended_action: str

class RetryRoutingModel:
    def __init__(self, model_dir: str):
        self.model_path = os.path.join(model_dir, "feature_b.joblib")
        self.model = None
        
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"Loaded Retry Routing model from {self.model_path}")
        else:
            print(f"WARNING: Retry Routing model not found at {self.model_path}")

    def predict(self, input_data: RetryRoutingInput) -> RetryRoutingOutput:
        if self.model is None:
            raise ValueError("Retry Routing model is not loaded")
            
        features = [[
            input_data.hour_of_day,
            input_data.day_of_month,
            input_data.failure_cause_encoded,
            input_data.payment_method_encoded,
            input_data.retry_count,
            input_data.time_since_failure_mins
        ]]
        
        success_prob = self.model.predict_proba(features)[0][1]
        
        # If the success probability is greater than 60%, we schedule a retry.
        # Otherwise, we abandon the automated retry and fall back to dunning.
        action = "retry_scheduled" if success_prob >= 0.60 else "trigger_dunning"
            
        return RetryRoutingOutput(
            retry_success_probability=float(success_prob),
            recommended_action=action
        )
