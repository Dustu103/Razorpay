# Frontend — Screen Specifications
# Feature 1 — Classifier Inspector

---

## Screen 1: Transaction List (`/`)

**Purpose:** Show all recent payment failure classifications at a glance. Allow filtering by cause and layer.

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 Razorpay Classifier Inspector          [Feature 1 — Pillar B]│
├─────────────────────────────────────────────────────────────────┤
│  Filter: [Cause ▼] [Layer: All · 1 · 2]                         │
├──────────┬────────┬───────────┬────────────┬────────────────────┤
│ Txn ID   │ Layer  │ Cause     │ Confidence │ Action             │
├──────────┼────────┼───────────┼────────────┼────────────────────┤
│ pay_xyz1 │ ⚡ L1  │ 🟡 notif  │ ████ 100%  │ silent_reschedule  │
│ pay_xyz2 │ 🤖 L2  │ 🔵 soft   │ ███░  75%  │ retry_scheduled    │
│ pay_xyz3 │ 🤖 L2  │ 🔴 hard   │ ███░  75%  │ do_not_retry       │
│ pay_xyz4 │ 🤖 L2  │ 🟠 gway   │ ███░  75%  │ retry_scheduled    │
│ pay_xyz5 │ 🤖 L2  │ 🟣 fraud  │ ███░  75%  │ do_not_retry       │
└──────────┴────────┴───────────┴────────────┴────────────────────┘
  Showing 5 of 5 · Load more
```

### Behaviour
- Clicking any row navigates to `/classifications/<id>`
- Filter changes update URL query params and re-fetch (no client-side mutation)
- `confidence=0` rows show a ⚠️ warning and "Manual Review" label instead of confidence bar

---

## Screen 2: Transaction Detail (`/classifications/[id]`)

**Purpose:** Full audit view for a single classification. Proves reasoning is real and traceable.

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back to list                                                  │
│                                                                  │
│  Transaction: pay_xyz1                        [⚡ Layer 1 · Rule]│
│  ─────────────────────────────────────────────────────────────  │
│  Cause:    🟡 notification_compliance_block                      │
│  Action:   silent_reschedule                                     │
│  Confidence: ████████████████████ 100%                           │
│                                                                  │
│  Reasoning                                                       │
│  ─────────────────────────────────────────────────────────────  │
│  The pre-debit notification was either not sent or was sent      │
│  less than 24 hours before the scheduled debit, violating the   │
│  RBI E-mandate Framework 2026 requirement.                       │
│                                                                  │
│  Input Payload Sent to Classifier                                │
│  ─────────────────────────────────────────────────────────────  │
│  status_code:              FAILED                                │
│  npci_response_code:       —                                     │
│  bank_response_code:       —                                     │
│  amount:                   ₹999.00                               │
│  customer_bank:            HDFC                                  │
│  retry_count_so_far:       0                                     │
│  mandate_notification_sent_at:  null                             │
│  debit_scheduled_at:       2026-08-22 10:00 IST                  │
│                                                                  │
│  Classified: 2026-08-22 10:01 IST · Model: —                    │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Badge Variants

| Layer | Badge | Model shown? |
|-------|-------|--------------|
| 1 | `⚡ Layer 1 · Rule · Deterministic` (green) | No — deterministic |
| 2 | `🤖 Layer 2 · Model · stub-v1.0-heuristic` (blue) | Yes — `model_version` |

### Confidence Bar Variants

| Confidence | Display |
|-----------|---------|
| 1.0 | Green full bar |
| 0.75 | Green partial bar |
| 0.0 | ⚠️ Red "Manual Review Required" |
