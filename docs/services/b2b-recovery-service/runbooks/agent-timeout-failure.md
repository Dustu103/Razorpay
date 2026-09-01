# Runbook: B2B Agent Timeout / Failure

## Symptoms
The `b2b-recovery-service` logs show continuous errors during the nightly `00:01` cron run:
*   `[b2b-recovery] Failed to call agent for INV-XXXX: agent returned status 503`
*   `[b2b-recovery] Failed to call agent for INV-XXXX: context deadline exceeded`

No new drafts are appearing in the `b2b_tax_lever_approvals` table.

## Root Cause Analysis
The Go cron daemon is successfully querying PostgreSQL for overdue invoices, but the POST request to the Python `inference-service` is failing. 
This is usually caused by:
1. **Groq API Rate Limiting:** The Python service is hitting a `429 Too Many Requests` limit with Groq while drafting legal emails.
2. **Inference Service Down:** The Python container has crashed or is unhealthy.

## Resolution Steps

### Step 1: Check Inference Service Health
Check if the python service is alive:
```bash
curl -I http://localhost:8000/health
```
If it returns `503`, restart the inference service:
```bash
docker-compose restart inference-service
```

### Step 2: Check Groq API Logs
Tail the logs of the inference service to look for `429` errors:
```bash
docker logs razorpay-inference-service | grep -i "rate limit"
```
If rate limiting is active, verify that `GROQ_API_KEY` in `docker-compose.yml` is valid and the tier hasn't been exhausted. 

### Step 3: Manual Re-Run of the Cron Job
Because this service is a daily batch job, any invoices missed during the downtime will NOT be processed until the next day at `00:01`.
To manually force the job to run immediately and catch up on the backlog, restart the B2B service (which is configured to run the job once upon startup):
```bash
docker-compose restart b2b-recovery-service
```
Monitor the logs to ensure the backlog of overdue invoices is processed successfully:
```bash
docker logs -f razorpay-b2b-recovery
```
