# RB-006: Debugging the Inference Gateway

**Service:** `inference-service`  
**Severity:** High  
**Symptom:** Classification or Chargeback services are returning 500 errors, or `win_probability` is stuck at `0.00` across all requests.

## 1. Verify Service Connectivity
The Inference Gateway is isolated in the `razorpay_default` docker network.
Run a health check from within another container (e.g. `chargeback-service`):

```bash
docker exec -it razorpay-chargeback curl http://inference-service:8000/health
```
**Expected Output:**
```json
{"status":"healthy","classifier_loaded":true}
```

## 2. Check for Missing Pickles / Mounts
If the health check returns a 503 or fails to load models, verify the volume mounts:
```bash
docker inspect razorpay-inference | grep models
```
Ensure that `/app/models/` inside the container maps correctly to the host's `models/` or `data/` directory.

## 3. Python Dependency Issues (libgomp1)
If the service logs show `OSError: libgomp.so.1: cannot open shared object file: No such file or directory`, this means the LightGBM/XGBoost C++ bindings are failing to load.

**Fix:** Ensure the Dockerfile installs `libgomp1`.
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1
```
Rebuild the image: `docker compose up -d --build inference-service`

## 4. Check for Inconsistent Version Warnings
If you see `InconsistentVersionWarning: Trying to unpickle estimator Pipeline from version 1.9.0 when using version 1.5.0` in the logs, it means the `.pkl` files were trained on a newer/older version of `scikit-learn` than what is running in the container.
- Update `backend/inference-service/requirements.txt` to match the exact `scikit-learn` version used in training.
