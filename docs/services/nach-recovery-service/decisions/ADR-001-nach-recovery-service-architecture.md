# ADR-001: Dedicated Architecture for NACH Mandate Recovery Service

**Status:** Accepted  
**Date:** 2026-09-05  
**Deciders:** Core Engineering Team  

---

## Context
Recurring payment recovery via NACH mandates involves regulatory timeframes, bank return penalty structures, and clearing house policies that do not exist in instantaneous checkout drop-off or card chargebacks:
1. Mutual fund SIPs cancel after 3 consecutive failures.
2. Loan EMIs impact borrower credit bureau scores after 30 days.
3. Bank retries cost ₹250–₹500 per bounce in bank processing fees.

Initially, NACH rules were embedded as a sub-package inside `classification-service`. However, this violates single responsibility, creates coupling with real-time checkout failure classification, and prevents dedicated telemetry for recurring revenue metrics.

---

## Decision
Create an autonomous microservice `nach-recovery-service` (`backend/nach-recovery-service`) listening on port `3007`:
* Hosts the dedicated **Governor Engine** and **Urgency Dispatch Router**.
* Provides REST APIs (`/health`, `/api/v1/nach-metrics`, `/api/v1/evaluate-mandate`).
* Runs independently in Docker network as `razorpay-nach-recovery`.

---

## Consequences
* **Positive:** Dedicated dashboard metrics for recurring revenue and bank fees saved.
* **Positive:** Decoupled from transient card/UPI classification pipelines.
* **Positive:** Conforms to the standard microservice pattern established by `dropoff-service` and `b2b-recovery-service`.
