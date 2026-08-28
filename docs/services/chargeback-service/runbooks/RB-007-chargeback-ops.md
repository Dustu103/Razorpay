# Operations Runbook: Chargeback Pre-emption Service

> **Service:** `chargeback-service` · **Port:** `3005` · **Container:** `razorpay-chargeback`

---

## 1. Health Monitoring

### 1.1 Health Check
The service exposes a `/health` endpoint:
```bash
curl http://localhost:3005/health
```
Expected response:
```json
{ "status": "healthy", "classifier_loaded": true }
```

If `classifier_loaded` is `false`, it means the ML artifacts failed to load from `/app/datasets/chargeback/`. Check:
```bash
docker exec razorpay-chargeback ls /app/datasets/chargeback/
# Should contain: all_models.pkl, model_meta.json, feature_scaler.pkl, woe_encoder.json
```

### 1.2 Key Metrics to Watch (in logs)
```bash
docker logs razorpay-chargeback --tail 100 -f
```
| Log Pattern | Meaning |
|------------|---------|
| `POST /api/v1/analyze-dispute 200` | Normal dispute analysis |
| `[LLM Routing] Groq failed` | Groq API unreachable, Gemini fallback active |
| `[LLM Routing] Gemini failed` | Gemini API unreachable, static fallback narrative used |
| `Warning: Failed to load classifier artifacts` | ML pickle incompatibility — retrain needed |

### 1.3 VAMP Ratio Monitoring
The VAMP threshold is checked per-request using `merchant_current_dispute_ratio`. To verify a merchant's current status:
- **Safe zone:** ratio ≤ 1.2% — full ensemble routing active
- **Warning zone:** 1.2% ≤ ratio < 1.5% — VAMP deflection for win_prob < 91%
- **Critical zone:** ratio ≥ 1.5% — escalate to merchant risk team immediately

---

## 2. Routing Decision Rules (v2 — Post-Calibration)

The service applies the following decision hierarchy in `win_probability.py`:

| Priority | Rule | Action |
|----------|------|--------|
| 1 (Highest) | `days_remaining ≤ 2` | `deflect_via_refund` — No time for arbitration |
| 2 | VAMP high-risk AND `win_prob < 0.91` | `deflect_via_refund` — Protect dispute ratio |
| 3 | `disagreement_flag = True` AND `win_prob < 0.35` | `deflect_via_refund` — Unwinnable with uncertainty |
| 4 | `disagreement_flag = False` AND `win_prob ≥ 0.70` | `auto_submit` |
| 5 | `disagreement_flag = False` AND `win_prob ≥ 0.40` | `one_tap_approval` |
| 6 | `disagreement_flag = False` AND `win_prob < 0.40` | `deflect_via_refund` |
| 7 (Lowest) | `disagreement_flag = True` (high uncertainty) | `await_merchant_approval` |

**Variance Threshold (σ):** The disagreement flag fires when `std_dev(5-model predictions) > max(0.10, calibrated_threshold)`.

> **Current Calibrated Threshold:** `0.0199` (from `model_meta.json`)  
> **Safety Floor Applied:** `0.10` (to avoid noise from minor scoring differences triggering human review)

---

## 3. VAMP Ratio Alert Procedures

### 3.1 Alert Detection
If a merchant's ratio exceeds 1.2%, the API response will include:
```json
"vamp_advisory": {
  "status": "high_risk",
  "ratio_impact_warning": true,
  "message": "Dispute ratio (X.XX%) is near/exceeding VAMP thresholds (1.5%). Deflecting borderline cases via refund is highly recommended."
}
```

### 3.2 Escalation Steps
1. **Notify Risk Team** with merchant ID and current ratio.
2. **Monitor dispute velocity** — if 30-day volume is rising, apply full deflect mode.
3. **Dashboard override:** The merchant can enable Aggressive VAMP Protection in their settings.
4. **Card Network Contact:** If ratio breaches 1.5%, contact Visa/MC account manager within 48 hours.

---

## 4. Retraining the ML Ensemble

Retrain every **60–90 days** as real dispute outcome labels arrive from card networks.

### Step 1: Update Raw Dataset
Upload new labeled dispute outcomes to `datasets/chargeback/chargeback_raw.csv`.

### Step 2: Clean the Dataset
```bash
docker compose run --rm chargeback-service python /app/datasets/scripts/clean_chargeback_data.py
```

### Step 3: Run Training (inside the service container for version alignment)
```bash
docker compose run --rm chargeback-service python /app/datasets/scripts/train_chargeback_model.py
```
This automatically updates:
- `all_models.pkl` — 5-model ensemble pickle bundle
- `feature_scaler.pkl` — MinMaxScaler fitted to training data
- `woe_encoder.json` — WoE encodings for `merchant_category`
- `model_meta.json` — Ensemble weights, SHAP top-3, variance threshold

### Step 4: Validate with E2E Tests
```bash
docker exec razorpay-chargeback python /app/datasets/scripts/test_chargeback.py
```
Expected: **15/15 scenarios PASSED**. Do not deploy if any routing test fails.

### Step 5: Restart Service
```bash
docker compose restart chargeback-service
```
Verify health: `curl http://localhost:3005/health`

---

## 5. Updating the VAMP Deflection Threshold

The VAMP threshold is defined in `backend/chargeback-service/main.py`:
```python
if merchant_ratio >= 0.012:  # 1.2% warning zone
    vamp_status = "high_risk"
```
And the win-probability cut-off for deflection:
```python
if vamp_status == "high_risk" and win_prob < 0.91:
    recommended_action = "deflect_via_refund"
```
**To change:** Edit these values, rebuild and redeploy:
```bash
docker compose build chargeback-service && docker compose up -d chargeback-service
```

---

## 6. Hallucination Guard — What Gets Redacted

The `hallucination_guard.py` applies the following redactions to all LLM-generated narratives before they reach the merchant UI:

| Pattern | Action | Reason |
|---------|--------|--------|
| ML metrics (`probability`, `xgboost`, `classifier`, etc.) | Replace with `[REDACTED_ML_METRIC]` | Leaking win predictions to banks is a compliance risk |
| Email addresses | Replace with `[REDACTED_EMAIL]` | LLMs hallucinate fake customer emails |
| Phone numbers (Indian 10-digit + US format) | Replace with `[REDACTED_PHONE]` | PII hallucination |
| System prompt prefixes ("As an AI...") | Strip entirely | LLM identity leaks undermine letter credibility |
| Indian PAN numbers (`[A-Z]{5}[0-9]{4}[A-Z]`) | Replace with `[REDACTED_PAN]` | RBI PII mandate |
| Aadhaar patterns (12 digits with spaces/dashes) | Replace with `[REDACTED_AADHAAR]` | RBI PII mandate |
| UPI virtual payment addresses | Replace with `[REDACTED_VPA]` | PII leak prevention |

---

## 7. Known Issues & Mitigations

| Issue | Mitigation |
|-------|-----------|
| sklearn pickle version mismatch on cold start | Always retrain inside the service container (`docker compose run --rm chargeback-service`) |
| LLM narrative is blank (both APIs down) | Service falls back to a static rebuttal template — check `GROQ_API_KEY` and `GEMINI_API_KEY` env vars |
| Model disagreement rate >20% in production | Trigger retraining — synthetic training distribution has drifted from real data |
| `evidence_completeness_score` always returns 2 | Verify `required_evidence` field is populated in `reason_code_map.py` for the given code |
