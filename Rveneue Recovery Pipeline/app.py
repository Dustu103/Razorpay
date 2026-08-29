from fastapi import FastAPI
from models.feature_d import FeatureDModel
from schemas import PipelineInput, PipelineOutput, FalseDeclineInput, FalseDeclineOutput
from pipeline import RecoveryPipeline
from models import FeatureBModel, FeatureCModel,FeatureDModel

app = FastAPI(title="Razorpay AI Revenue Recovery Engine")

pipeline = RecoveryPipeline()
fd_model = FeatureDModel()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/recover", response_model=PipelineOutput)
def run_recovery(payload: PipelineInput, customer_tenure: int = 12, prior_success_rate: float = 0.8):
    return pipeline.process(payload, customer_tenure, prior_success_rate)

@app.post("/api/false-decline", response_model=FalseDeclineOutput)
def detect_false_decline(payload: FalseDeclineInput):
    return fd_model.predict(payload)

@app.post("/api/train")
def train_models():
    b_model = FeatureBModel()
    c_model = FeatureCModel()
    d_model = FeatureDModel()
    
    b_model.train_model()
    c_model.train_model()
    d_model.train_model()
    
    return {"status": "success", "message": "Models retrained successfully"}

if __name__ == "__main__":
    import uvicorn
    from config import PORT
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)