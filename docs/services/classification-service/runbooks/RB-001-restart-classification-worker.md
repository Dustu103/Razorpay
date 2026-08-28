# RB-001: Restart the Classification Worker

**Trigger:** Worker is not consuming jobs / queue is growing but classifications table is not updating.  
**Severity:** High — no new classifications are being produced.

---

## Symptoms

- Redis queue length is growing (see RB-002 to check queue depth).
- `classifications` table row count is not increasing.
- `docker logs` for `classification-service` shows no recent activity or a panic/fatal error.

---

## Steps

### 1. Check current worker status
```bash
docker compose ps classification-service
```
Expected: `Up`. If `Exit 1` or `Restarting`, proceed.

### 2. Check the worker logs for the root cause
```bash
docker compose logs --tail=100 classification-service
```
Look for:
- `FATAL` — a panic or unrecoverable error.
- `dial tcp: connection refused` — Redis or Postgres is down (check those services first).
- `context deadline exceeded` — LLM timeout storm (normal under rate-limits, worker should recover automatically).

### 3. Restart the service
```bash
docker compose restart classification-service
```

### 4. Verify it's consuming jobs
```bash
docker compose logs -f classification-service
```
Within 5 seconds you should see:
```
INFO  worker: dequeued job <txn_id>
INFO  layer1: no rule match, passing to layer2
...
INFO  worker: job <txn_id> complete, cause=soft_decline
```

### 5. Verify the database is being written
```bash
docker compose exec postgres psql -U postgres -d razorpay -c \
  "SELECT id, created_at FROM classifications ORDER BY created_at DESC LIMIT 5;"
```

---

## Escalation

If the worker exits immediately after restart, check:
1. `GROQ_API_KEY` is set and valid in `.env`.
2. Redis is reachable: `docker compose exec classification-service redis-cli -h redis ping`.
3. Postgres is reachable: `docker compose exec classification-service pg_isready -h postgres`.
