# RB-001: Drop-Off Recovery Service Operations & Troubleshooting

## 1. Service Overview
* **Container Name**: `razorpay-dropoff`
* **Internal Port**: `3002`
* **Health Check**: `curl -s http://localhost:3002/api/v1/dropoff-metrics`
* **Dependencies**: Redis (`razorpay-redis:6379`), Inference Gateway (`razorpay-inference:8000`)

---

## 2. Common Operational Issues

### Issue 1: Sessions Accumulating in Redis (Worker Stalled)
**Symptoms:**
* Redis key `active_checkout_sessions` grows indefinitely.
* No new interventions logged in `metrics:dropoff:recent_interventions`.

**Diagnostics:**
```bash
# Check size of active sessions
docker exec -it razorpay-redis redis-cli zcard active_checkout_sessions

# Check dropoff service logs
docker logs --tail 50 razorpay-dropoff
```

**Resolution:**
1. Check if `razorpay-inference` is healthy and responding on port 8000:
   ```bash
   curl -s http://localhost:8000/health
   ```
2. If `inference-service` is unreachable, restart it:
   ```bash
   docker restart razorpay-inference
   ```
3. Restart `dropoff-service` to reinitialize the polling goroutine:
   ```bash
   docker restart razorpay-dropoff
   ```

---

### Issue 2: Excessive Message Suppression (Low Intervention Rate)
**Symptoms:**
* High drop-off volume, but nearly all sessions logged as `NO_ACTION` / `SUPPRESSED`.

**Diagnostics:**
1. Verify merchant margin and cart values. If merchant margin is configured as `0` or default RTO costs exceed cart value, the engine will mathematically suppress interventions.
2. Check `InterventionOutput.reasoning` in logs:
   ```
   SUPPRESSED. P0=0.647 r0=0.124 | ΔΠ(WA)=₹-159.30 ΔΠ(SMS)=₹-230.71
   ```
3. If high organic conversion $P_0$ is causing suppression, this is expected causal behavior (preventing margin cannibalization).
