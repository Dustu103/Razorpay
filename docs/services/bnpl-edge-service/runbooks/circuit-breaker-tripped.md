# Runbook: Edge Circuit Breaker Tripped (SLA Violation)

## Symptoms
Alerts fire showing a high rate of `503 Service Unavailable` or `context deadline exceeded` in the `bnpl-edge-service` logs.
The business dashboard shows BNPL checkout fallback offer injections dropping to 0%.

## Root Cause Analysis
This means the `inference-service` (Python) is taking longer than the 50ms SLA to return predictions.

### Step 1: Check Inference Service Load
1. Open the Docker/Kubernetes metrics for the `inference-service` container.
2. Check CPU and Memory utilization. Python ML models (Random Forest) are CPU bound. If CPU is pegged at 100%, the inference gateway cannot process concurrent requests fast enough.

### Step 2: Check Model Complexity
1. Did the Data Science team just deploy a new model (`feature_e_edge.joblib`)? 
2. **Action:** A heavier model (e.g., deeper trees, transitioning from Random Forest to XGBoost) increases inference time. Roll back the model artifact to the previous version and restart the inference container.

### Step 3: Mitigation (Scale Out)
1. If the model is correct but traffic is high (e.g., flash sale), scale out the `inference-service` horizontally.
```bash
docker-compose up --scale inference-service=5 -d
```
2. The Go Edge Gateway will naturally round-robin HTTP requests across the new containers, dropping CPU load and returning inference times back under the 40ms threshold.
