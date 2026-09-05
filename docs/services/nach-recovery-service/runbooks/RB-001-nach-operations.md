# RB-001: NACH Mandate Recovery Service Operations & Troubleshooting

## 1. Service Profile
* **Container Name**: `razorpay-nach-recovery`
* **Internal Port**: `3007`
* **Health Check**: `curl -s http://localhost:3007/health`
* **Metrics API**: `curl -s http://localhost:3007/api/v1/nach-metrics`

---

## 2. Common Operational Issues

### Issue 1: Service Offline or Unhealthy
**Diagnostics:**
```bash
docker compose ps nach-recovery-service
docker logs --tail 50 razorpay-nach-recovery
```
**Resolution:**
```bash
docker compose restart nach-recovery-service
```

### Issue 2: Mandates Accumulating Unprocessed
**Diagnostics:**
```bash
curl -s http://localhost:3007/api/v1/nach-metrics | jq '.total_mandates_evaluated'
```
Verify PostgreSQL has records with `payment_rail = 'nach'`:
```bash
docker compose exec postgres psql -U razorpay -d razorpay_classifier -c \
  "SELECT count(*) FROM transactions WHERE payment_rail = 'nach';"
```
