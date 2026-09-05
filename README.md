# Razorpay AI Buildathon 2026: The Revenue Recovery Ecosystem

Welcome to the ultimate Revenue Recovery Ecosystem built for the Razorpay AI Buildathon 2026.

Instead of a single feature, we built a comprehensive, legally compliant **4-Pillar Architecture** designed to stop revenue leaks across the entire payment lifecycle.

## 🏗️ The 4 Pillars

### Pillar A: Chargeback Pre-emption (Prevent)
A production-grade automated triage pipeline for disputes.
*   **VAMP Protection:** Deflects unwinnable cases to protect the merchant's Visa Acquirer Monitoring Program (VAMP) ratio from exceeding the 1.5% limit.
*   **Multi-LLM Rebuttals:** Uses Groq (fast/cheap) and Gemini (complex/heavy) to generate perfect, network-compliant representment drafts.

### Pillar B: Root-Cause Diagnostics (Diagnose)
An intelligent payment failure diagnostics engine.
*   **Deterministic + ML:** Analyzes bank response codes, AVS mismatches, and temporal features to diagnose exactly why a transaction failed.
*   **False Decline Engine:** Identifies when strict fraud filters have blocked a genuine customer, routing them for immediate retry.

### Pillar C: Dual-Engine BNPL Recovery (Recover)
A DPDP Act & RBI compliant recovery system.
*   **Engine 1 (Edge Checkout):** Ultra-low latency Go proxy providing real-time BNPL checkout fallback offers under a strict 50ms circuit breaker.
*   **Engine 2 (Asynchronous Recovery):** Background Go worker orchestrating multi-channel recovery, strictly obeying the DPDP Act (Right to Erasure) and RBI Dunning guidelines (8 AM - 7 PM IST, max 3 contacts/day).

### Pillar D: B2B Tax Lever — Receivables Recovery (Escalate)
A unique compliance-driven B2B revenue recovery engine targeting overdue invoices using Indian Tax Law.
*   **Cron-Based Batch Scanning:** A Go daemon (`robfig/cron/v3`) scans overdue B2B invoices every night. Unlike webhooks that fire only at expiration, this batch architecture ensures that invoices are correctly evaluated at the 45-day and 180-day statutory thresholds.
*   **Deterministic Rules Engine:** Identifies when a buyer has exceeded the Sec 43B(h) MSME payment window (45 days) or the CGST Rule 37 ITC Reversal window (180 days).
*   **Groq LLM Drafting:** Natively calls Groq's Llama 3 70B to generate formal, lawyer-grade legal notices citing the exact Indian Tax statute.
*   **Human-in-the-Loop Approval:** All AI-generated legal notices require human approval via the Next.js Tax Approvals dashboard before dispatch, ensuring regulatory compliance.

---

## 📚 Documentation
Dive into the technical depth of our architecture in the `docs/` folder:
*   **[System Architecture (HLD)](./docs/architecture/hld.md)**
*   **[Chargeback Service (LLD)](./docs/services/chargeback-service/lld.md)**
*   **[BNPL Edge Service (Circuit Breaker ADR)](./docs/services/bnpl-edge-service/decisions/001-fail-silent-sla.md)**
*   **[B2B Recovery Service (HLD)](./docs/services/b2b-recovery-service/hld.md)**
*   **[B2B Recovery Service (LLD)](./docs/services/b2b-recovery-service/lld.md)**
*   **[B2B ADR: Why Cron over Webhooks](./docs/services/b2b-recovery-service/decisions/001-hybrid-cron-webhook.md)**
*   **[B2B ADR: Why Deterministic over ML](./docs/services/b2b-recovery-service/decisions/002-deterministic-over-ml.md)**

## 🚀 Getting Started
```bash
# Copy env file and add your Groq API key
cp .env.example .env

# Start the entire ecosystem
docker-compose up -d --build
```

> **Note:** A `GROQ_API_KEY` is required for the B2B Tax Lever LLM drafting feature and Chargeback Rebuttal generation. The rest of the system (Classification, BNPL Edge) will work without it using deterministic fallbacks.

## 🗺️ Service Map

| Service | Language | Port | Purpose |
| :--- | :--- | :--- | :--- |
| `classification-service` | Go | — | Redis worker: diagnoses payment failures |
| `audit-service` | Go | 3003 | REST API: serves classification results to the UI |
| `bnpl-edge-service` | Go | 8003 | 50ms Edge Proxy: BNPL checkout fallback |
| `chargeback-service` | Python | 3005 | REST API: dispute triage and rebuttal generation |
| `inference-service` | Python | 8000 | ML + LLM: centralized model serving & B2B Agent |
| `b2b-recovery-service` | Go | 3006 | Cron Daemon: B2B tax lever recovery pipeline |
| `compliance-service` | Python | 3004 | REST API: enforces DPDP and RBI guidelines |
| `dropoff-service` | Go | 3002 | REST API & Worker: diagnostics for checkout drop-offs |
| `ingestion-service` | Go | 3001 | REST API: webhook receiver and queue manager |
| `frontend` | Next.js | 3010 | Dashboard UI for all 4 pillars |
| `postgres` | PostgreSQL | 5432 | Shared database |
| `redis` | Redis | 6379 | Message queue and state store |
