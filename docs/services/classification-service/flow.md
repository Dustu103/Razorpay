# Classification Flow — Layer 1 → Layer 2 → Persist

**Service:** Classification Service (queue worker)  
**Trigger:** Job dequeued from `classification_jobs` Redis list

---

## Flow Diagram

```mermaid
sequenceDiagram
    participant RQ as Redis Queue
    participant CW as Classification Worker
    participant PG as PostgreSQL
    participant L1 as Layer 1 (Deterministic)
    participant L2 as Layer 2 (ML Model)
    participant L3 as Layer 3 (LLM)
    participant L4 as Layer 4 (Ensemble)

    RQ->>CW: BLPOP classification_jobs<br/>{"transaction_id": "<uuid>"}

    CW->>PG: SELECT * FROM transactions WHERE id = $1
    PG-->>CW: Transaction row (all fields)

    CW->>L1: classifyLayer1(txn)

    alt mandate_notification_sent_at is null OR sent < 24h before debit
        L1-->>CW: ClassificationResult<br/>cause=notification_compliance_block<br/>confidence=1.0, layer=1
        CW->>PG: INSERT INTO classifications (layer=1, ...)
        Note over CW,PG: Done — Fast path exit
    else notification was timely (or debit_scheduled_at is null)
        L1-->>CW: nil (fall through)

        par Layer 2 ML Call
            CW->>L2: classifyLayer2(txn) [15s timeout]
            L2-->>CW: ML Result
        and Layer 3 LLM Call
            CW->>L3: classifyLayer3(txn) [10s timeout]
            L3-->>CW: LLM Result
        end

        CW->>L4: merge(ML, LLM)
        Note right of L4: If ML >= 0.55 or Agreement -> Trust ML<br/>If ML < 0.55 -> Trust LLM

        L4-->>CW: Final ClassificationResult
        CW->>PG: INSERT INTO classifications (layer=4, ...)
    end
```

---

## Layer 1 Decision Logic

```
IF txn.debit_scheduled_at IS NULL:
    → fall through to Layer 2 (cannot make determination)

required_deadline = debit_scheduled_at - 24h

IF mandate_notification_sent_at IS NULL
   OR mandate_notification_sent_at > required_deadline:
    → cause = notification_compliance_block
    → confidence = 1.0
    → action = silent_reschedule
ELSE:
    → fall through to Layer 2
---

## Layer 2, 3, and 4 Logic Details

The legacy stub heuristic has been fully replaced by the live **Mixture-of-Experts (MoE) ML + LLM Ensemble**. 
For a detailed mathematical and structural breakdown of the Layer 2 Random Forest and the Layer 4 Ensemble Tie-Breaker logic, please see [ml-pipeline.md](ml-pipeline.md).
