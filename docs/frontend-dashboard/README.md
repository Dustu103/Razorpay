# Frontend Dashboard — Documentation Index

> All technical documentation for the `frontend` dashboard lives here.

## Documents

| File | Description |
|------|-------------|
| [architecture.md](./architecture.md) | Next.js SSR architecture, Server Actions, Webhook Simulator Panel, 4-Layer badge system |

## Service Overview

The frontend is a **Next.js 15 (App Router)** real-time observability dashboard and testing harness for the classification pipeline. It serves two primary functions:

1. **Live Audit Dashboard** — Displays all classified transactions fetched from the Audit Service, with layer-based filtering, confidence bars, and detailed reasoning views.
2. **Webhook Simulator** — Allows engineers to inject synthetic `payment.failed` events from the browser directly into the Ingestion Service via Next.js Server Actions, triggering the full Multi-LLM pipeline without needing Postman or external tools.

For system-wide context, see the [High-Level Design](../architecture/hld.md).
