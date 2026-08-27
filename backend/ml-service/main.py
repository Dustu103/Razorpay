from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import joblib
import pandas as pd
import os
import time

app = FastAPI(title="Razorpay Layer 2 ML Service")

# Load model on startup
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "layer2_payment_failure_model.pkl")
model_pipeline = None

class Transaction(BaseModel):
    id: str
    event_type: Optional[str] = "payment.failed"
    timestamp: Optional[str] = None
    status_code: Optional[str] = None
    bank_response_code: Optional[str] = None
    npci_response_code: Optional[str] = None
    amount_paise: Optional[int] = 0
    currency: Optional[str] = "INR"
    card_network: Optional[str] = None
    card_country_code: Optional[str] = None
    issuer_bank: Optional[str] = None
    retry_count_so_far: Optional[int] = 0
    is_recurring_transaction: Optional[str] = "N"
    cardholder_auth_method: Optional[str] = None
    mandate_notification_sent_at: Optional[str] = None
    debit_scheduled_at: Optional[str] = None

@app.on_event("startup")
def load_model():
    global model_pipeline
    print(f"Loading ML model from {MODEL_PATH}...")
    try:
        model_pipeline = joblib.load(MODEL_PATH)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        # Not exiting here so we can see the error in logs if it fails, 
        # but subsequent /predict calls will fail with 503.

@app.get("/health")
def health_check():
    if model_pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "healthy", "model_version": "v1.0.0-rf"}

@app.post("/predict")
def predict(txn: Transaction):
    if model_pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Convert transaction to a pandas DataFrame of 1 row
    df = pd.DataFrame([txn.model_dump()])
    
    # Run prediction
    start = time.time()
    try:
        # Predict the class
        pred_class = model_pipeline.predict(df)[0]
        
        # Get probability (confidence score)
        # Random Forest predict_proba returns probabilities for all classes
        probs = model_pipeline.predict_proba(df)[0]
        max_prob = max(probs)
        
        # Construct reasoning 
        reason = f"L2_ML_PREDICTION_{pred_class.upper()}"
        
        # Determine action (hardcoded simple mapping based on predicted cause for MVP)
        action = "retry_scheduled"
        if pred_class in ["hard_decline", "fraud_filter_block", "notification_compliance_block"]:
            action = "do_not_retry"
            
        return {
            "transaction_id": txn.id,
            "layer": 2,
            "cause": pred_class,
            "confidence": float(max_prob),
            "reasoning": reason,
            "recommended_action": action,
            "model_version": "scikit-learn-rf-v1"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
