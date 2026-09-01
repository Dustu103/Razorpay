# ADR 001: Hybrid Event-Batch Architecture for Time-Delayed Triggers

**Date:** 2026-09-01  
**Status:** Accepted  
**Context:** The B2B Recovery Service must evaluate if an unpaid invoice is exactly 45 or 180 days past its expiration date to apply specific Indian Tax Law penalties.

## The Problem (The Temporal Webhook Fallacy)
The initial architectural proposal suggested relying entirely on the Razorpay `invoice.expired` webhook. 

**The Flaw:** Webhooks in payment gateways are point-in-time events. The `invoice.expired` event fires exactly once—the moment the `expire_by` timestamp is breached. When the webhook fires, the invoice is 0 days late. If a microservice only listens to this event stream, it will never be able to trigger an action 45 days *after* the expiration, because Razorpay does not emit a "45-days-late" webhook.

## Decision
We pivoted from a pure Event-Driven Architecture (Webhook Listener) to a **Hybrid Event-Batch Architecture**.

1.  **Event Capture:** The system uses the `invoice.expired` webhook merely to mark the invoice as `overdue` in our local PostgreSQL database.
2.  **Batch Polling (Cron):** A Go daemon (`robfig/cron/v3`) wakes up every night at `00:01` and performs a batch SQL query: 
    `SELECT * FROM invoices WHERE status = 'overdue'`
3.  **Evaluation:** The Go daemon calculates `current_date - expire_by`. If the delta equals exactly 45 or 180, it dispatches the invoice to the AI Agent.

## Consequences
- **Positive:** We guarantee no invoices fall through the cracks. The system reliably re-evaluates all overdue debt every single day.
- **Negative:** Introduces an active polling mechanism which puts a tiny nightly load on the PostgreSQL database, though this is negligible for our scale.
