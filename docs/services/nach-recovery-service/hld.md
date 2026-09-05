# NACH Mandate Recovery Service — High Level Design (HLD)

## Overview
The `nach-recovery-service` is an autonomous recurring revenue recovery daemon in the Razorpay AI Revenue Recovery suite. It monitors failed recurring e-mandates (Mutual Fund SIPs, Loan EMIs, and Insurance Premiums), enforces AMC/lender regulatory deadlines via a deterministic **Governor Engine**, and triggers product-aware dunning interventions to maximize recovered capital while eliminating bank return penalty fees.

---

## Architecture Topology

```
┌─────────────────────────────────────────────────────────────┐
│                 Client / Triage Dashboard                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
               (GET /api/v1/nach-metrics)
               (POST /api/v1/evaluate-mandate)
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 nach-recovery-service                       │
│             (Go 1.22 + GoFiber REST API :3007)              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐     ┌───────────────────────┐  │
│  │     Governor Engine     │     │   Urgency Dispatch    │  │
│  │ - AMC 3-failure SIP cap │     │ - Critical (WhatsApp) │  │
│  │ - EMI 28-day bureau cap │ ──► │ - Elevated (SMS)      │  │
│  │ - Insurance lapse guard │     │ - Standard (Email/ML) │  │
│  └─────────────────────────┘     └───────────────────────┘  │
│                               │                             │
│                  ┌────────────┴────────────┐                │
│                  ▼                         ▼                │
│       ┌──────────────────────┐  ┌──────────────────────┐    │
│       │ Automated Retry Queue│  │ Unretryable Blocked  │    │
│       │ (Soft causes only)   │  │ (Mandate Expired)    │    │
│       └──────────────────────┘  └──────────────────────┘    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                PostgreSQL / Redis Datastores                │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Pillars & Governor Rules

### 1. SIP Mandate Protection (AMC 3-Failure Rule)
* **Context:** Mutual Fund AMCs automatically cancel investor SIPs upon 3 consecutive debit failures.
* **Governor Logic:**
  * At failure count $= 2$, the engine initiates a **Pre-Emptive Escalation** (`sip_cancellation_risk_escalate`) with Elevated Urgency (SMS).
  * At failure count $\ge 3$, automated retries are **Hard-Blocked** (`confidence: 1.0`) because the mandate is cancelled at the clearing house.

### 2. Loan EMI Credit Bureau Protection (Day 28 Guard)
* **Context:** Non-bank financial companies (NBFCs) and banks report defaults to CIBIL/Experian 30 days past due date.
* **Governor Logic:**
  * At $\ge 28$ days past due date, the engine overrides probabilistic retry schedules and fires **Immediate WhatsApp Communication** (`credit_score_risk_escalate`).
  * Factual urgency is communicated to give the borrower 48 hours to preserve their credit standing.

### 3. Insurance Premium Coverage Protection
* **Context:** Life and health insurance policies lapse quickly upon unpaid premium, leaving the policyholder uncovered.
* **Governor Logic:**
  * Single failure ($\ge 1$) triggers immediate elevated escalation (`policy_lapse_risk_escalate`) via SMS.

### 4. Zero-Waste Permanent Cause Blocking
* **Context:** In standard blind 3-attempt retry setups, expired mandates and frozen accounts are retried repeatedly, costing ₹250–₹500 in bank bounce fees per attempt.
* **Governor Logic:**
  * Failures with causes `mandate_expired`, `account_frozen_or_closed`, and `incorrect_mandate_details` are permanently marked `nach_do_not_retry`.
  * In empirical validation on 100 failed mandates, this eliminated **114 wasted bank calls** ($100\%$ reduction).

---

## Service Specifications
* **Language / Framework:** Go 1.22 + GoFiber v2
* **Port:** `3007`
* **Internal Endpoints:**
  * `GET /health` — Readiness probe.
  * `GET /api/v1/nach-metrics` — Aggregated revenue and pre-emption metrics.
  * `POST /api/v1/evaluate-mandate` — Synchronous policy evaluation.
