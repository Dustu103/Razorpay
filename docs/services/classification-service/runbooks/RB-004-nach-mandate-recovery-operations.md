# RB-004: NACH Mandate Recovery Engine Operations & Invariant Monitoring

**Trigger:** NACH mandate debit failures reported / high bank bounce penalties / unexpected dunning channel allocations.  
**Severity:** High — non-compliant retries risk AMC auto-cancellation and customer credit score harm.

---

## 1. Overview
The NACH Mandate Recovery Engine operates at **Layer 0** (stopping policy) and **Post-Ensemble** (product-aware dunning) within `classification-service`. It protects recurring payments across three product lines:
* **Mutual Fund SIPs:** Enforces AMC 3-consecutive-failure cancellation threshold (escalates at failure #2, hard-stops at failure #3).
* **Loan EMIs:** Enforces credit bureau reporting window (escalates at 28 days past due date).
* **Insurance Premiums:** Immediate escalation on failure #1 to prevent policy lapse.

---

## 2. Common Operational Issues

### Issue 1: Retries Triggering on AMC-Cancelled SIPs
**Symptoms:**
* Bank returns code `R03` / `R08` on SIP mandates with 3+ previous failures.
* Merchants complain of bank bounce fees (₹250–₹500 per attempt).

**Diagnostics:**
```bash
docker compose exec postgres psql -U razorpay -d razorpay_classifier -c \
  "SELECT id, product_type, consecutive_failure_count, recommended_action, layer \
   FROM transactions t JOIN classifications c ON t.id = c.transaction_id \
   WHERE t.payment_rail = 'nach' AND t.product_type = 'sip' AND t.consecutive_failure_count >= 3 \
   ORDER BY c.created_at DESC LIMIT 10;"
```

**Expected Result:**
* `layer` MUST be `0`.
* `recommended_action` MUST be `sip_cancellation_risk_escalate`.
* Automated retries MUST NOT be scheduled (`ActionRetryScheduled` is forbidden).

**Remediation:**
If retries were queued, inspect `nach/stopping.go` and verify the transaction record has `payment_rail = 'nach'` populated in PostgreSQL.

---

### Issue 2: EMI Approaching 30-Day Credit Bureau Window Not Escalating
**Symptoms:**
* Loan EMIs at day 28+ remain in retry queue instead of dispatching urgent WhatsApp dunning.

**Diagnostics:**
```bash
docker compose exec postgres psql -U razorpay -d razorpay_classifier -c \
  "SELECT t.id, t.days_since_due_date, c.recommended_action, c.reasoning \
   FROM transactions t JOIN classifications c ON t.id = c.transaction_id \
   WHERE t.payment_rail = 'nach' AND t.product_type = 'loan_emi' AND t.days_since_due_date >= 28 \
   LIMIT 5;"
```

**Expected Result:**
* `recommended_action` MUST be `credit_score_risk_escalate`.
* Reasoning must state: `[Layer 0 · NACH EMI Credit Risk] X days since due date... Bypassing retry queue, escalating directly.`

---

### Issue 3: Permanent Failure Retries (Mandate Expired / Account Frozen)
**Symptoms:**
* Mandates with `mandate_expired` or `account_frozen_or_closed` are scheduled for retry.

**Diagnostics:**
Check recent classifications for NACH unretryable causes:
```bash
docker compose exec postgres psql -U razorpay -d razorpay_classifier -c \
  "SELECT t.id, c.cause, c.recommended_action \
   FROM transactions t JOIN classifications c ON t.id = c.transaction_id \
   WHERE t.payment_rail = 'nach' AND c.cause IN ('nach_mandate_expired', 'nach_account_frozen_or_closed', 'nach_incorrect_mandate_details');"
```

**Expected Result:**
* `recommended_action` MUST be `nach_do_not_retry`.

---

## 3. Verification & Live Test Run
To verify all NACH policies in the running environment:
```bash
docker run --rm -v "$(pwd):/app" -w /app razorpay-inference-service:latest python tests/test_nach_recovery.py
```
Expected output:
```text
Total Transactions Evaluated:       100
Layer 0 Pre-emptive Stops:          46
Permanent Unretryable Blocks:       21
Soft Causes Evaluated for Retry:    33
ALL NACH INVARIANTS & POLICIES VALIDATED SUCCESSFULLY.
```
