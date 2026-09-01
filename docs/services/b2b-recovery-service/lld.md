# B2B Recovery Service - Low Level Design (LLD)

## 1. Service Internal Structure

The `b2b-recovery-service` is structured using standard Go idioms, separating configuration, database access, and core business logic.

```text
backend/b2b-recovery-service/
├── cmd/
│   └── server/
│       └── main.go       # Bootstraps Fiber HTTP (health) and the Cron Daemon
├── internal/
│   ├── db/
│   │   └── postgres.go   # Manages pgxpool connection to PostgreSQL
│   ├── models/
│   │   └── models.go     # Core data structures (InvoiceRecord, AgentRequest/Response)
│   └── worker/
│       └── cron.go       # Implements robfig/cron and orchestrates the inference call
├── tests/
│   └── unit/
│       └── worker_test.go
├── Dockerfile
└── go.mod
```

## 2. Core Workflows

### 2.1 The Cron Orchestrator (`cron.go`)
1. **Schedule:** The daemon executes at `00:01` daily via `1 0 * * *` cron syntax.
2. **Database Read:** Queries the `invoices` table for all records where `status = 'overdue'`.
3. **Calculation:** Computes `days_late = CURRENT_DATE - expire_by`.
4. **Agent Dispatch:** Marshals the `models.AgentRequest` and sends an HTTP POST to `http://inference-service:8000/agent/b2b-invoice`.
5. **Database Write:** If the Python agent returns an action starting with `tax_lever_`, the Go daemon executes an `INSERT INTO b2b_tax_lever_approvals` with the drafted email.

### 2.2 The Python Agent Router (`inference-service/app/models/b2b_agent.py`)
This is the deterministic router. It does not use Machine Learning.
*   **Input Validation:** Parses `B2BInvoiceInput` using Pydantic.
*   **Routing Logic:**
    ```python
    if days >= 180:
        return trigger_gst_rule37()
    if days >= 45 and is_msme:
        return trigger_sec_43b()
    ```

### 2.3 The Groq LLM Prompt
When a tax lever is triggered, the native `groq` Python client is invoked with the following system/user prompt topology:

**System Prompt:**
> "You are an expert Indian corporate lawyer and accounts receivable manager."

**User Prompt Payload:**
> "Draft a highly formal, polite, but firm email to a business customer.
> Customer Name: {customer_name}
> Invoice ID: {id}
> Amount Due: ₹{amount_due}
> Days Overdue: {days_late}
> Legal Context: Under Indian Tax Law, specifically {statute}, failure to pay within the statutory limit results in {penalty_desc}.
> Write a concise 3-paragraph email reminding them of the overdue amount and citing the exact legal statute and penalty. Do not invent any facts not provided."

## 3. Database Queries
**Inserting an Approval:**
```sql
INSERT INTO b2b_tax_lever_approvals 
(invoice_id, customer_name, is_msme, days_late, tax_rule_triggered, draft_email_body, status) 
VALUES ($1, $2, $3, $4, $5, $6, 'pending')
```

## 4. Dependencies
*   `github.com/gofiber/fiber/v2`: Exposes port 3006 for `/health`.
*   `github.com/robfig/cron/v3`: Handles the daily tick without exiting the container.
*   `github.com/jackc/pgx/v5`: Performant Postgres driver.
