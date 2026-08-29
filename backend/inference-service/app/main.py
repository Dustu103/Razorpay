from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import joblib
import pandas as pd
import os
import time

from .win_probability import DisputeClassifier
from .models.false_decline import FalseDeclineModel, FalseDeclineInput

app = FastAPI(title="Razorpay Centralized Inference Gateway")

# Paths are resolved via environment variables set in docker-compose
PAYMENT_MODEL_DIR = os.getenv("PAYMENT_MODEL_DIR", "/app/models/ml")
PAYMENT_MODEL_PATH = os.path.join(PAYMENT_MODEL_DIR, "layer2_payment_failure_model.pkl")

payment_model = None
chargeback_model = None
false_decline_model = None

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
def load_models():
    global payment_model, chargeback_model, false_decline_model
    
    # Load Payment Failure Model
    print(f"Loading Payment ML model from {PAYMENT_MODEL_PATH}...")
    try:
        if os.path.exists(PAYMENT_MODEL_PATH):
            payment_model = joblib.load(PAYMENT_MODEL_PATH)
            print("Payment Model loaded successfully.")
        else:
            print(f"Warning: Payment model not found at {PAYMENT_MODEL_PATH}")
    except Exception as e:
        print(f"Error loading payment model: {e}")

    # Load Chargeback Model
    print(f"Loading Chargeback ML model...")
    try:
        chargeback_model = DisputeClassifier()
        print("Chargeback Model loaded successfully.")
    except Exception as e:
        print(f"Error loading chargeback model: {e}")

    # Load False Decline Model
    print(f"Loading False Decline ML model from {PAYMENT_MODEL_DIR}...")
    try:
        false_decline_model = FalseDeclineModel(PAYMENT_MODEL_DIR)
        print("False Decline Model loaded successfully.")
    except Exception as e:
        print(f"Error loading false decline model: {e}")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "payment_model_loaded": payment_model is not None,
        "chargeback_model_loaded": chargeback_model is not None,
        "false_decline_model_loaded": false_decline_model is not None
    }

@app.post("/predict/payment")
def predict_payment(txn: Transaction):
    if payment_model is None:
        raise HTTPException(status_code=503, detail="Payment model not loaded")
    
    df = pd.DataFrame([txn.model_dump()])
    try:
        pred_class = payment_model.predict(df)[0]
        probs = payment_model.predict_proba(df)[0]
        max_prob = max(probs)
        reason = f"L2_ML_PREDICTION_{pred_class.upper()}"
        
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

@app.post("/predict/chargeback")
def predict_chargeback(req: Dict[str, Any]):
    if chargeback_model is None:
        raise HTTPException(status_code=503, detail="Chargeback model not loaded")
    
    try:
        results = chargeback_model.predict(req)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/false-decline")
def predict_false_decline(req: FalseDeclineInput):
    if false_decline_model is None:
        raise HTTPException(status_code=503, detail="False Decline model not loaded")
    
    try:
        return false_decline_model.predict(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
