from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import joblib
import pandas as pd
import os
import time
from .win_probability import DisputeClassifier
from app.models.false_decline import FalseDeclineModel, FalseDeclineInput, FalseDeclineOutput
from app.models.retry_routing import RetryRoutingModel, RetryRoutingInput, RetryRoutingOutput
from app.models.dunning import DunningModel, DunningInput, DunningOutput
from app.models.bnpl_edge import BNPLEdgeModel, BNPLEdgeInput, BNPLEdgeOutput
from app.models.bnpl_recovery import BNPLRecoveryModel, BNPLRecoveryInput, BNPLRecoveryOutput
from app.models.b2b_agent import B2BAgentModel, B2BInvoiceInput, B2BInvoiceOutput
from app.models.intervention_model import InterventionModel, InterventionInput, InterventionOutput

app = FastAPI(title="Razorpay Inference Gateway")

# Paths are resolved via environment variables set in docker-compose
PAYMENT_MODEL_DIR = os.getenv("PAYMENT_MODEL_DIR", "/app/models/ml")
models_dir = PAYMENT_MODEL_DIR

layer2_model = None
retry_model = None
dunning_model = None
false_decline_model = None
bnpl_edge_model = None
bnpl_recovery_model = None
chargeback_model = None
b2b_agent_model = None
intervention_model = None

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
    # NACH rail fields — zero-valued for UPI/card transactions.
    payment_rail: Optional[str] = ""                # "nach" | "upi" | "card" | ""
    product_type: Optional[str] = ""                # "sip" | "loan_emi" | "insurance_premium" | ""
    consecutive_failure_count: Optional[int] = 0    # Consecutive mandate debit failures
    days_since_due_date: Optional[int] = None       # EMI: days elapsed since due date

@app.on_event("startup")
def load_models():
    global layer2_model, retry_model, dunning_model, false_decline_model, bnpl_edge_model, bnpl_recovery_model, chargeback_model
    
    # Load all models into memory once to avoid disk I/O on inference
    layer2_model_path = os.path.join(models_dir, "layer2_payment_failure_model.pkl")
    if os.path.exists(layer2_model_path):
        layer2_model = joblib.load(layer2_model_path)
    
    retry_model = RetryRoutingModel(models_dir)
    dunning_model = DunningModel(models_dir)
    false_decline_model = FalseDeclineModel(models_dir)
    bnpl_edge_model = BNPLEdgeModel(models_dir)
    bnpl_recovery_model = BNPLRecoveryModel(models_dir)

    # Load Chargeback Model
    try:
        chargeback_model = DisputeClassifier()
    except Exception as e:
        print(f"Error loading chargeback model: {e}")

    # B2B Agent — no model file needed, deterministic routing
    global b2b_agent_model, intervention_model
    b2b_agent_model = B2BAgentModel()
    intervention_model = InterventionModel()
    print("[inference] B2B Agent loaded (deterministic + Groq LLM)")
    print("[inference] Intervention Scoring loaded (EV Math)")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "models_loaded": {
            "layer2": layer2_model is not None,
            "retry": retry_model.model is not None,
            "dunning": dunning_model.model is not None,
            "false_decline": false_decline_model.model is not None,
            "bnpl_edge": bnpl_edge_model.model is not None,
            "bnpl_recovery": bnpl_recovery_model.model is not None,
            "intervention": intervention_model is not None and intervention_model.s_model is not None,
            "b2b_agent": b2b_agent_model is not None
        }
    }

@app.post("/predict/payment")
def predict_payment(txn: Transaction):
    if layer2_model is None:
        raise HTTPException(status_code=503, detail="Payment model not loaded")
    
    df = pd.DataFrame([txn.model_dump()])
    try:
        pred_class = layer2_model.predict(df)[0]
        probs = layer2_model.predict_proba(df)[0]
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

@app.post("/predict/false-decline", response_model=FalseDeclineOutput)
async def predict_false_decline(data: FalseDeclineInput):
    """
    Predicts if a fraud_filter_block is actually a false decline (genuine customer).
    """
    if false_decline_model.model is None:
        raise HTTPException(status_code=503, detail="False Decline model not loaded")
    return false_decline_model.predict(data)

@app.post("/predict/checkout-offer", response_model=BNPLEdgeOutput)
async def predict_checkout_offer(data: BNPLEdgeInput):
    """
    Fast edge decision on whether to offer BNPL during a checkout decline.
    """
    if bnpl_edge_model.model is None:
        raise HTTPException(status_code=503, detail="BNPL Edge model not loaded")
    return bnpl_edge_model.predict(data)

@app.post("/predict/bnpl-recovery", response_model=BNPLRecoveryOutput)
async def predict_bnpl_recovery(data: BNPLRecoveryInput):
    """
    Heavy ML analysis for BNPL installment recovery routing based on phantom debt.
    """
    if bnpl_recovery_model.model is None:
        raise HTTPException(status_code=503, detail="BNPL Recovery model not loaded")
    return bnpl_recovery_model.predict(data)

@app.post("/predict/retry", response_model=RetryRoutingOutput)
def predict_retry(req: RetryRoutingInput):
    if retry_model.model is None:
        raise HTTPException(status_code=503, detail="Retry Routing model not loaded")
    
    try:
        return retry_model.predict(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/dunning")
def predict_dunning(req: DunningInput):
    if dunning_model is None:
        raise HTTPException(status_code=503, detail="Dunning model not loaded")

    try:
        return dunning_model.predict(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/b2b-invoice", response_model=B2BInvoiceOutput)
def b2b_invoice_agent(data: B2BInvoiceInput):
    """
    B2B Tax Lever Agent.
    Deterministically routes overdue invoices to the correct Indian Tax statute
    and uses Groq Llama 3 70B to draft a formal legal notice.
    """
    if b2b_agent_model is None:
        raise HTTPException(status_code=503, detail="B2B Agent not loaded")
    try:
        return b2b_agent_model.predict(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/intervention", response_model=InterventionOutput)
def predict_intervention(data: InterventionInput):
    """
    ML scoring model to determine Expected Value of an intervention.
    """
    if intervention_model is None:
        raise HTTPException(status_code=503, detail="Intervention model not loaded")
    try:
        return intervention_model.predict(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
