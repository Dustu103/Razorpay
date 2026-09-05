# Drop-Off Recovery Service - High Level Design (HLD)

## Overview
The `dropoff-service` is an autonomous real-time daemon in the Razorpay AI Revenue Recovery suite. It monitors active checkout sessions across web and mobile payment interfaces, detects uncompleted checkouts upon abandonment or technical error, diagnoses the root cause, and queries the Causal Inference Gateway to trigger net-EV positive customer interventions.

## Architecture

The service operates as an asynchronous, event-driven detection worker paired with a REST metrics interface.

```
┌───────────────────────────┐
│ Client Checkout Interface │
└─────────────┬─────────────┘
              │ 1. Telemetry heartbeat (session:events)
              ▼
    ┌──────────────────┐
    │  Redis Cluster   │ ◄─── active_checkout_sessions (ZSET)
    └─────────┬────────┘
              │ 2. ZRangeByScore (Expired sessions)
              ▼
┌───────────────────────────┐      3. POST /predict/intervention
│      dropoff-service      │ ─────────────────────────────────► ┌───────────────────┐
│ (Go Worker + Fiber REST)  │                                   │ inference-service │
└─────────────┬─────────────┘ ◄───────────────────────────────── └───────────────────┘
              │                    4. Best Action (ΔΠ, r_a, Message)
              ▼
┌───────────────────────────┐
│   Execution Guardrails    │ (Frequency cap, quiet hours, opt-out check)
└─────────────┬─────────────┘
              │ 5. Trigger channel
              ▼
┌───────────────────────────────────────────┐
│ WhatsApp / SMS / Email Dispatch Gateway   │
└───────────────────────────────────────────┘
```

### 1. Hybrid Active Session Tracking (Redis ZSET)
- Active checkout sessions register in a Redis Sorted Set (`active_checkout_sessions`) scored by `timestamp + expiry_seconds`.
- Granular client telemetry events (e.g. `cart_loaded`, `payment_selected`, `app_switch`, `otp_delay`, `vpa_error`) are continuously appended to a Redis list (`session:{id}:events`).
- A background ticker continuously executes `ZRANGEBYSCORE active_checkout_sessions -inf <now>` to atomically pop sessions whose timers have expired without reaching terminal `payment_status: success`.

### 2. Microservice Topology
- **Language:** Go 1.23
- **Framework:** GoFiber v2 (exposes `/api/v1/dropoff-metrics` for frontend dashboard)
- **State Store:** Redis 7 (stores active sessions, session metadata hash, and event lists)
- **Inference Integration:** HTTP Client calls out to `inference-service` (`POST /predict/intervention`)
- **Port:** `3002`

### 3. Causal Decision Orchestration
Unlike naive commercial abandoned-cart plugins that blast WhatsApp messages to 100% of drop-offs, `dropoff-service` respects causal economic boundaries:
- Evaluates **Incremental Lift** over organic conversion: $\tau_a = P_a - P_0$.
- Evaluates **Downside RTO Risk**: Penalizes actions that drive COD orders likely to result in return-to-origin ($K_{RTO} \approx ₹250$).
- Applies exact causal Net-EV logic:
$$\Delta\Pi_a = P_a[(1 - r_a)(CM - D_a) - r_a K_{RTO}] - P_0[(1 - r_0)CM - r_0 K_{RTO}] - K_a$$
- If $\max_a \Delta\Pi_a \le 0$, the engine strictly **SUPPRESSES** intervention to protect merchant margins and prevent brand fatigue.

### 4. Guardrails & Compliance
- **Frequency Capping**: Maximum 1 intervention per customer per 24 hours.
- **Opt-Out Checking**: Checks Redis blacklist key `customer:{phone}:opt_out`.
- **Quiet Hours**: Respects Indian TRAI DND regulations (no promotional SMS/WhatsApp between 21:00 and 09:00).

## Deployment
- Runs as a Docker container within the primary `docker-compose.yml` network.
- Depends on `redis` and `inference-service`.
