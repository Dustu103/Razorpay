# RB-002: Debug a Stuck Redis Queue

**Trigger:** Jobs are accumulating in Redis but the worker is not processing them.  
**Severity:** High.

---

## Symptoms

- Dashboard shows no new classifications.
- Redis queue length is non-zero and growing.
- Worker container is `Up` (no crash), but logs show no job dequeue activity.

---

## Steps

### 1. Check the queue depth
```bash
docker compose exec redis redis-cli LLEN classification_jobs
```
A healthy system should return `0` or a small number under burst load.  
If it returns `>100` and is not decreasing, the worker is stuck.

### 2. Inspect the first job in the queue (non-destructive)
```bash
docker compose exec redis redis-cli LRANGE classification_jobs 0 0
```
This shows the raw JSON payload at the front of the queue without removing it.

Check for:
- Malformed JSON — a corrupt payload can cause the worker to panic on unmarshal and loop.
- An extremely large payload — may indicate an upstream bug in the ingestion service.

### 3. Check the semaphore slot count
The worker uses a semaphore of size 50. If all 50 slots are occupied (e.g. all goroutines are hanging on an LLM timeout), no new jobs are dequeued until a slot frees up.

```bash
docker compose logs --tail=200 classification-service | grep "semaphore"
```

If goroutines are stuck on LLM calls, the 3-second `requestTimeout` circuit breaker should release them automatically. Wait 5 seconds and re-check.

### 4. Manually drain a single job for inspection
```bash
docker compose exec redis redis-cli RPOP classification_jobs
```
> ⚠️ This permanently removes the job. Only do this for debugging a corrupt payload.

### 5. Flush the entire queue (last resort)
> ⚠️ **Destructive.** Only use if all queued jobs are test data or confirmed invalid.
```bash
docker compose exec redis redis-cli DEL classification_jobs
```

---

## Prevention

- The ingestion service should validate webhook payloads before enqueuing.
- A Dead Letter Queue (DLQ) pattern is planned to capture failed jobs instead of dropping them. Track in the project backlog.
