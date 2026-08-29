import os
import joblib
from pydantic import BaseModel
from typing import Dict

class BNPLEdgeInput(BaseModel):
    amount: float
    decline_reason_encoded: int
    tenure_months: int

class BNPLEdgeOutput(BaseModel):
    show_bnpl_offer: bool
    conversion_probability: float

class BNPLEdgeModel:
    def __init__(self, model_dir: str):
        self.model_path = os.path.join(model_dir, "feature_e_edge.joblib")
        self.model = None
        
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"Loaded BNPL Edge model from {self.model_path}")
        else:
            print(f"WARNING: BNPL Edge model not found at {self.model_path}")

    def predict(self, input_data: BNPLEdgeInput) -> BNPLEdgeOutput:
        if self.model is None:
            raise ValueError("BNPL Edge model is not loaded")
            
        features = [[
            input_data.amount,
            input_data.decline_reason_encoded,
            input_data.tenure_months
        ]]
        
        # predict_proba returns [prob_0, prob_1]
        conversion_prob = self.model.predict_proba(features)[0][1]
        
        # We want to be somewhat conservative on the edge offer to prevent checkout clutter
        show_offer = conversion_prob >= 0.50
            
        return BNPLEdgeOutput(
            show_bnpl_offer=show_offer,
            conversion_probability=float(conversion_prob)
        )
