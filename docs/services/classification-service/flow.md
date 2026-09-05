# Classification Flow — Layer 0 → Layer 1 → Ensemble → Post-Ensemble

**Service:** Classification Service (queue worker)  
**Trigger:** Job dequeued from `classification_jobs` Redis list

---

## Complete Pipeline Sequence Diagram

```mermaid
sequenceDiagram
    participant RQ as Redis Queue
    participant CW as Classification Worker
    participant PG as PostgreSQL
    participant L0 as Layer 0 (NACH Stopping)
    participant L1 as Layer 1 (RBI Compliance)
    participant L2 as Layer 2 (ML Model)
    participant L3 as Layer 3 (Rail-Aware LLM)
    participant L4 as Layer 4 (Ensemble)
    participant PE as Post-Ensemble (Retry & Dunning)

    RQ->>CW: BLPOP classification_jobs {"transaction_id": "<uuid>"}

    CW->>PG: SELECT * FROM transactions WHERE id = $1
    PG-->>CW: Transaction row (incl. payment_rail, product_type)

    CW->>L0: nach.Check(txn)
    alt Layer 0 Stops (SIP >= 2/3, EMI >= 28d, Insurance >= 1)
        L0-->>CW: StoppingResult (ShouldStop=true, Layer=0)
        CW->>PG: INSERT INTO classifications (layer=0, ...)
        Note over CW,PG: Fast-path exit (NACH hard stop / escalation)
    else Layer 0 Pass (or non-NACH)
        L0-->>CW: ShouldStop=false

        CW->>L1: layer1.Classify(txn)
        alt Mandate Notification missing or < 24h before debit
            L1-->>CW: ClassificationResult (cause=notification_compliance_block, layer=1)
            CW->>PG: INSERT INTO classifications (layer=1, ...)
            Note over CW,PG: Fast-path exit (RBI compliance block)
        else Notification valid
            L1-->>CW: nil (fall through)

            par Concurrent Inference
                CW->>L2: classifyLayer2(txn)
                L2-->>CW: ML Result
            and Rail-Aware LLM
                CW->>L3: classifyLayer3(txn) [Groq/Gemini/Fallback]
                L3-->>CW: LLM Result
            end

            CW->>L4: merge(ML, LLM)
            L4-->>CW: Base ClassificationResult

            CW->>PE: Evaluate Post-Ensemble
            alt Fraud Filter Block
                PE->>PE: CheckFalseDecline -> reverify_and_reverse if prob > 0.85
            else Soft Cause (insufficient_funds / soft_decline)
                PE->>PE: EvaluateRetry -> retry_scheduled or EvaluateDunning
                Note over PE: NACH EMI credit_score_risk forces WhatsApp
            else NACH Hard Cause (mandate_expired, frozen)
                PE->>PE: Force action = nach_do_not_retry
            end
            PE-->>CW: Final ClassificationResult

            CW->>PG: INSERT INTO classifications (layer=4, ...)
        end
    end
```

---

## Decision Logic Breakdown

### 1. Layer 0: NACH Mandate Stopping Logic
```
IF txn.payment_rail != "nach":
    → Continue to Layer 1

IF product_type == "sip":
    IF consecutive_failures >= 3:
        → Hard stop: Action = "sip_cancellation_risk_escalate", conf = 1.0 (AMC cancellation)
    IF consecutive_failures >= 2:
        → Pre-emptive: Action = "sip_cancellation_risk_escalate", conf = 0.95 (Protect mandate)

ELSE IF product_type == "loan_emi":
    IF days_since_due_date >= 28:
        → Action = "credit_score_risk_escalate", conf = 1.0 (2 days prior to 30-day reporting)

ELSE IF product_type == "insurance_premium":
    IF consecutive_failures >= 1:
        → Action = "policy_lapse_risk_escalate", conf = 0.90 (Immediate coverage risk)
```

### 2. Layer 1: RBI 24h Pre-Debit Notification Logic
```
IF txn.debit_scheduled_at IS NULL:
    → Fall through to Layer 2

required_deadline = debit_scheduled_at - 24h

IF mandate_notification_sent_at IS NULL OR mandate_notification_sent_at > required_deadline:
    → Action = "silent_reschedule", Cause = "notification_compliance_block", Layer = 1
```
