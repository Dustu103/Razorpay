# RB-003: Run the E2E Test Pipeline

**Trigger:** Post-deployment validation, API key rotation, or after any change to the classification logic.  
**Severity:** Informational.

---

## Prerequisites

- All Docker services are running: `docker compose ps` shows all services `Up`.
- Python dependencies installed in the `ml-service` container:
  ```bash
  docker compose exec ml-service pip install requests pandas psycopg2-binary
  ```

---

## Option A: Browser Simulator (Recommended for Quick Checks)

1. Open the frontend dashboard in your browser (`http://localhost:3000`).
2. Locate the **Test Simulator** panel below the filter bar.
3. Click any preset button (e.g. "Gateway Fault", "Fraud Risk").
4. Wait ~2 seconds.
5. The dashboard table should refresh automatically showing the newly classified transaction.
6. Click the transaction ID to inspect the Layer, Cause, Confidence, and Reasoning.

---

## Option B: Python Script (Recommended for Batch Validation)

### Run the 100-transaction benchmark
```bash
docker compose exec ml-service python datasets/scripts/test_pipeline_100.py
```
Expected output:
```
Submitted 100 transactions...
Waiting for classification...
Accuracy: 82.00% (82/100 correct)
```

### Run the 50-transaction unthrottled stress test
```bash
docker compose exec ml-service python datasets/scripts/test_pipeline_100.py --count 50 --no-sleep
```

---

## Interpreting Results

| Accuracy | Likely Cause | Action |
|----------|-------------|--------|
| > 90% | LLM working normally | ✅ All good |
| 80–90% | Occasional Groq 429 under burst | ⚠️ Monitor; consider paid key |
| 60–80% | Groq rate-limited, Gemini responding | ⚠️ Check Gemini key validity |
| < 60% | Both LLMs failing, pure heuristic fallback | 🚨 Check API keys (see RB-004) |
| ~96% | Both LLMs failing but ML confidence is high → ML trusted | ✅ Ensemble working correctly |

---

## Checking Results Directly in the Database

```bash
docker compose exec postgres psql -U postgres -d razorpay -c \
  "SELECT layer, cause, COUNT(*) FROM classifications GROUP BY layer, cause ORDER BY layer, count DESC;"
```
