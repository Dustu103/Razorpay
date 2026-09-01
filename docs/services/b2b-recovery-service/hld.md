# B2B Recovery Service - High Level Design (HLD)

## Overview
The `b2b-recovery-service` is a background daemon responsible for executing the **B2B Tax Lever** strategy as part of the AI Revenue Recovery track. It identifies overdue B2B invoices and dynamically applies Indian Tax Law penalties (Income Tax Sec 43B for MSMEs and CGST Rule 37 for ITC Reversal) to incentivize prompt payments.

## Architecture

This service acts as the orchestrator for the B2B revenue recovery pipeline. It operates independently of the real-time payment pathways to process delayed dunning logic reliably.

### 1. Hybrid Event-Batch Pattern
Relying solely on real-time webhooks (like `invoice.expired`) is insufficient for time-delayed tasks, because webhooks only fire once at the exact moment of expiration. 

To solve this, the architecture uses a **Hybrid Event-Batch Pattern**:
1. **Event Capture (Ingestion):** Webhooks capture the initial expiration event and mark the invoice as `overdue` in PostgreSQL.
2. **Batch Processing (This Service):** A robust `robfig/cron/v3` daemon wakes up every night at 00:01 and queries PostgreSQL for all invoices where `current_date - expire_by` equals exactly 45 or 180 days.

### 2. Microservice Topology
- **Language:** Go 1.23
- **Web Framework:** GoFiber (for `/health` endpoint and potential future manual triggers).
- **Scheduler:** `robfig/cron/v3`.
- **Database:** PostgreSQL (reads invoices, writes to `b2b_tax_lever_approvals`).
- **Inference Integration:** HTTP Client calls out to `inference-service` (`/agent/b2b-invoice`).

### 3. The LLM Agent Pipeline
Instead of bloated frameworks like LangChain, the `b2b-recovery-service` sends a structured JSON payload to the Python `inference-service`. The Python service applies strict deterministic routing:

*   **< 45 Days Late:** Sends standard gentle reminders.
*   **= 46 Days Late (MSME Vendor):** Triggers Section 43B(h) penalty workflow. Uses native Groq Llama 3 70B to draft a formal legal notice stating the buyer will lose their tax deduction.
*   **= 181 Days Late (Any Vendor):** Triggers GST Rule 37 workflow. Drafts a formal legal notice warning of Input Tax Credit (ITC) reversal.

### 4. Human-in-the-Loop (HITL)
To comply with regulatory standards for AI-generated legal communication, the drafted emails are *never* sent automatically. The `b2b-recovery-service` inserts the drafted email into the `b2b_tax_lever_approvals` table with a status of `pending`. A human operator reviews and approves these drafts via the Next.js UI Dashboard.

## Data Schema

### `b2b_tax_lever_approvals`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | Primary Key |
| `invoice_id` | TEXT | Reference to the original invoice |
| `customer_name` | TEXT | Buyer name |
| `is_msme` | BOOLEAN | Identifies if the vendor is MSME registered |
| `days_late` | INT | Number of days past due date |
| `tax_rule_triggered` | TEXT | e.g. "Sec 43B Penalty" |
| `draft_email_body` | TEXT | The LLM-generated legal threat |
| `status` | TEXT | `pending`, `approved`, or `rejected` |

## Deployment & Monitoring
- Runs as an Alpine Docker container within the primary `docker-compose.yml` network.
- Exposes port `3006` with a `/health` endpoint for Docker Swarm/Kubernetes readiness probes.
