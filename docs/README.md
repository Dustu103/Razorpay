# Feature 1 — Root-Cause Classifier: Documentation Index

> **Project:** Razorpay AI Buildathon 2026 · Feature 1 (Pillar B — Diagnose)

This directory contains all technical and operational documentation for Feature 1.

---

## 📁 Structure

```
docs/
├── README.md                             ← You are here
│
├── architecture/                         ← System-wide docs ONLY (not service-specific)
│   ├── hld.md                            ← System HLD (service map, data flow, topology)
│   └── flow-diagrams/
│       └── data-pipeline.md              ← End-to-end webhook-to-inference flow
│
├── classification-service/               ← All docs for the classification-service
│   ├── README.md
│   ├── ml-pipeline.md                    ← ML Lifecycle, Feature Engineering, Training & Ensemble Logic
│   ├── multi-llm-integration.md          ← Concurrent Groq + Gemini LLM tie-breaker architecture
│   └── testing-and-results.md            ← Test harnesses, empirical accuracy metrics, bottlenecks
│
├── compliance-service/                 ← All docs for the mandate compliance scanner (Feature 2)
│   ├── README.md
│   └── architecture.md                   ← API design, LLM Prompt Logic & UI Schema
│
├── frontend-dashboard/                   ← All docs for the frontend dashboard
│   ├── README.md
│   └── architecture.md                   ← SSR architecture, Simulator Panel, 4-Layer badge system
│
├── decisions/                            ← Architecture Decision Records (ADR)
│   ├── README.md                         ← ADR index & status
│   ├── ADR-001-random-forest-layer2.md
│   ├── ADR-002-groq-over-openai.md
│   ├── ADR-003-redis-queue-over-http.md
│   ├── ADR-004-go-for-classification-service.md
│   ├── ADR-005-multi-llm-ensemble.md
│   └── ADR-006-nextjs-ssr-dashboard.md
│
└── runbooks/                             ← Operational runbooks for on-call engineers
    ├── README.md                         ← Runbook index
    ├── RB-001-restart-classification-worker.md
    ├── RB-002-debug-stuck-redis-queue.md
    ├── RB-003-run-e2e-test-pipeline.md
    └── RB-004-rotate-llm-api-keys.md
```

> **Convention:** When a new service is created (e.g. `notification-service`), create a matching
> `docs/notification-service/` folder. The `docs/architecture/` folder is reserved **only** for
> system-wide, cross-service diagrams and the HLD.

---

## 🔗 Quick Links

### Architecture
| Document | Purpose |
|----------|---------|
| [HLD](./architecture/hld.md) | Where to start — full system picture |
| [Data Pipeline](./architecture/flow-diagrams/data-pipeline.md) | End-to-end flow from Webhook to Inference |

### Classification Service
| Document | Purpose |
|----------|---------|
| [ML Pipeline](./classification-service/ml-pipeline.md) | ML architecture, SMOTE balancing, Model training & Tie-breaker logic |
| [Multi-LLM Integration](./classification-service/multi-llm-integration.md) | Concurrent Groq + Gemini Inference Architecture |
| [Testing & Results](./classification-service/testing-and-results.md) | Test scripts, accuracy benchmarks, stress-test results |

### Frontend Dashboard
| Document | Purpose |
|----------|---------|
| [Frontend Architecture](./frontend-dashboard/architecture.md) | SSR Dashboard, Webhook Simulator & 4-Layer UI |

### Compliance Scanner (Feature 2)
| Document | Purpose |
|----------|---------|
| [Compliance Architecture](./compliance-service/architecture.md) | JSON-based LLM UI scanning, Prompt logic, RBI mapping |

### Architecture Decisions (ADRs)
| ADR | Decision |
|-----|----------|
| [ADR-001](./decisions/ADR-001-random-forest-layer2.md) | Why Random Forest for Layer 2 |
| [ADR-002](./decisions/ADR-002-groq-over-openai.md) | Why Groq as primary LLM |
| [ADR-003](./decisions/ADR-003-redis-queue-over-http.md) | Why Redis queue over sync HTTP |
| [ADR-004](./decisions/ADR-004-go-for-classification-service.md) | Why Go for the classification-service |
| [ADR-005](./decisions/ADR-005-multi-llm-ensemble.md) | Why concurrent Multi-LLM over sequential fallback |
| [ADR-006](./decisions/ADR-006-nextjs-ssr-dashboard.md) | Why Next.js SSR for the dashboard |

### Runbooks
| Runbook | Trigger |
|---------|---------|
| [RB-001](./runbooks/RB-001-restart-classification-worker.md) | Worker is stuck / not consuming jobs |
| [RB-002](./runbooks/RB-002-debug-stuck-redis-queue.md) | Redis queue is growing but not draining |
| [RB-003](./runbooks/RB-003-run-e2e-test-pipeline.md) | Post-deployment E2E validation |
| [RB-004](./runbooks/RB-004-rotate-llm-api-keys.md) | Groq or Gemini API key expired |

### Co-located LLDs (next to service code)
| Document | Purpose |
|----------|---------|
| [Ingestion LLD](../backend/ingestion-service/docs/lld.md) | Ingestion service Low-Level Design |
| [Audit API](../backend/audit-service/docs/api.md) | Audit service endpoints |
| [Database Schema](../db/docs/schema.md) | Schema, ERD, dedup strategy |
