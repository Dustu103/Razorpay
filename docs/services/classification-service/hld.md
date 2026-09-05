# Classification Service — High Level Design (HLD)

## Overview
The `classification-service` is the core diagnostic and decision engine in the Razorpay AI Revenue Recovery suite. It operates as an event-driven queue worker that consumes failed recurring transactions (UPI AutoPay, Card Subscriptions, and NACH e-Mandates), classifies the root cause of failure across multi-tiered intelligence layers, and orchestrates optimal recovery actions.

---

## Architectural Topology

```
                  ┌──────────────────────────────┐
                  │   Redis Job Queue (BLPOP)    │
                  │    "classification_jobs"     │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │    Classification Worker     │
                  │         (Go 1.22)            │
                  └──────────────┬───────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
  │   Layer 0   │         │   Layer 1   │         │   Layers    │
  │    NACH     │         │   RBI 24h   │         │  2, 3 & 4   │
  │  Stopping   │         │ Notification│         │ ML + LLM +  │
  │   Policy    │         │ Compliance  │         │  Ensemble   │
  └──────┬──────┘         └──────┬──────┘         └──────┬──────┘
         │                       │                       │
 [Short-Circuit]         [Short-Circuit]                 │
         │                       │                       ▼
         │                       │                ┌─────────────┐
         │                       │                │Post-Ensemble│
         │                       │                │ Routing &   │
         │                       │                │ Dunning (C) │
         │                       │                └──────┬──────┘
         ▼                       ▼                       ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                 PostgreSQL Database Store                   │
  │        (Persists Classifications, Causes & Actions)         │
  └─────────────────────────────────────────────────────────────┘
```

---

## 5-Layer Intelligence Pipeline

The engine executes an ordered 5-layer pipeline from lowest latency/hard compliance rules up to concurrent probabilistic models:

### Layer 0: NACH Mandate Stopping Policy (`nach/stopping.go`)
* **Objective:** Prevents futile and non-compliant bank debit attempts on NACH e-mandates before incurring bank return penalties.
* **Deterministic Rules:**
  * **SIP Mandates:** Escalate pre-emptively at $\ge 2$ consecutive failures (`sip_cancellation_risk_escalate`) *before* the AMC 3-failure auto-cancellation threshold. Hard-stops at $\ge 3$ failures.
  * **Loan EMI Mandates:** Escalate at $\ge 28$ days past due date (`credit_score_risk_escalate`) to initiate high-urgency contact 2 days prior to the 30-day credit bureau reporting window.
  * **Insurance Premiums:** Escalate immediately upon first failure ($\ge 1$, `policy_lapse_risk_escalate`) to prevent policy lapse.
  * **Non-NACH Rail:** Passes through immediately to Layer 1.

### Layer 1: RBI Pre-Debit Notification Compliance (`layer1/rule.go`)
* **Objective:** Enforces the Reserve Bank of India (RBI) recurring mandate pre-debit notification mandate.
* **Rule:** If `mandate_notification_sent_at` is missing or sent $< 24\text{ hours}$ before `debit_scheduled_at`, the debit is blocked with `notification_compliance_block` and rescheduled silently (`silent_reschedule`).

### Layer 2: Fast ML Random Forest Classifier (`layer2/`)
* **Objective:** Sub-millisecond localized inference for structured transaction metadata.
* **Architecture:** Random Forest classifier predicting 6 core cause classes (`soft_decline`, `hard_decline`, `fraud_filter_block`, `insufficient_funds`, `bank_technical_error`, etc.) with calibrated confidence scores.

### Layer 3: Rail-Aware Multi-LLM Classifier (`layer3/llm.go`)
* **Objective:** Semantic reasoning over raw gateway response strings, error codes, and product metadata.
* **Rail Awareness:**
  * For **NACH transactions**: Prompt contextualizes bank return codes, mandate validity, AMC cancellation thresholds, and product urgency.
  * For **UPI/Card transactions**: Focuses on network timeouts, VPA validation errors, and OTP drop-offs.
* **Multi-Provider Fallback:** Groq Llama 3 70B $\rightarrow$ Google Gemini 1.5 Flash $\rightarrow$ Localized Heuristic Fallback.

### Layer 4: Dynamic Confidence Ensemble (`layer4/ensemble.go`)
* **Objective:** Resolves disagreements between ML (Layer 2) and LLM (Layer 3).
* **Policy:**
  * If ML confidence $\ge 0.85$ (or $\ge 0.65$ with agreement) $\rightarrow$ Trust Layer 2.
  * If ML confidence $< 0.55$ or disagreement $\rightarrow$ Trust Layer 3 LLM.

---

## Post-Ensemble Routing & Dunning Optimization

Once root-cause classification is established:
1. **Feature D (False Decline Recovery):** If classified as `fraud_filter_block`, queries inference gateway (`/predict/false-decline`). If likelihood $> 0.85$, overrides action to `reverify_and_reverse`.
2. **Feature B & C (Intelligent Retry & Dunning):** For soft failures (`soft_decline`, `insufficient_funds`, `bank_technical_error`):
   * Queries Retry Model (`/predict/retry`).
   * If retry probability $< 0.60$, queries Dunning Model (`/predict/dunning`).
   * **NACH Urgency Overrides:**
     * `credit_score_risk` (Loan EMI $\ge 28$ days) forces **WhatsApp** dispatch.
     * `investment_lapse_risk` (SIP) and `policy_lapse_risk` (Insurance) force **SMS** minimum.
3. **NACH Permanent Cause Hard-Stops:** If cause is `mandate_expired`, `incorrect_mandate_details`, or `account_frozen_or_closed`, action is locked to `nach_do_not_retry` to prevent bank bounce penalty fees.
