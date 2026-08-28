# Razorpay Enterprise Services: Documentation Index

> **Project:** Razorpay AI Buildathon 2026

---

## 📁 Structure

```
docs/
├── README.md                                  ← You are here
│
├── architecture/                              ← System-wide only (cross-service HLD & flow diagrams)
│   ├── hld.md
│   └── flow-diagrams/
│       └── data-pipeline.md
│
├── services/
│   ├── inference-service/                     ← Centralized ML Inference Gateway
│   │   ├── architecture.md
│   │   └── api.md
│   │
│   ├── chargeback-service/                    ← Autonomous Chargeback Pre-emption (Pillar A)
│   │   ├── architecture.md
│   │   ├── runbooks.md
│   │   └── adr-008.md
│   │
│   ├── classification-service/                ← Root-Cause Classifier (Pillar B)
│   │   ├── README.md
│   │   ├── ml-pipeline.md
│   │   ├── multi-llm-integration.md
│   │   ├── testing-and-results.md
│   │   ├── decisions/
│   │   └── runbooks/
│   │
│   ├── compliance-service/                    ← Compliance Scanner
│   │   ├── README.md
│   │   ├── architecture.md
│   │   ├── multi-llm-integration.md
│   │   ├── testing-and-results.md
│   │   ├── decisions/
│   │   └── runbooks/
│   │
│   ├── frontend/                              ← Next.js Dashboard
│   │   ├── README.md
│   │   ├── architecture.md
│   │   ├── api-docs.md
│   │   ├── lld.md
│   │   ├── screens.md
│   │   └── decisions/
│   │
│   ├── audit-service/                         ← Audit logging backend
│   │   ├── api.md
│   │   └── lld.md
│   │
│   ├── ingestion-service/                     ← Webhook processor
│   │   ├── api.md
│   │   ├── flow.md
│   │   └── lld.md
│   │
│   └── database/                              ← Database models & schema
│       ├── models.md
│       └── schema.md
│
├── design_archive/                            ← Original V1 design documents and product requirements
│
└── operations/                                ← Cross-service / infrastructure runbooks
    └── runbooks/
        └── RB-004-rotate-llm-api-keys.md
```

> **Convention:** Every new service gets its own `docs/services/<service-name>/` folder containing its API docs, Low-Level Design (LLD), `decisions/` (ADRs), and `runbooks/`. `docs/architecture/` is reserved for system-wide cross-service diagrams.

---

## 🔗 Quick Links

### System Architecture
| Document | Purpose |
|----------|---------|
| [HLD](./architecture/hld.md) | Full system picture — start here |
| [Data Pipeline](./architecture/flow-diagrams/data-pipeline.md) | End-to-end webhook-to-inference flow |

### Core ML & AI Services

#### Inference Gateway
| Document | Purpose |
|----------|---------|
| [Architecture](./services/inference-service/architecture.md) | Centralized Python Machine Learning gateway (XGBoost/LightGBM) |
| [API](./services/inference-service/api.md) | HTTP POST predictive endpoints for Payment Failures & Chargebacks |

#### Chargeback Pre-emption (Pillar A)
| Document | Purpose |
|----------|---------|
| [Architecture](./services/chargeback-service/architecture.md) | Dispute deterministic engine and LLM Rebuttal logic |
| [ADR-008](./services/chargeback-service/decisions/ADR-008-chargeback-architecture.md) | Decisions regarding chargeback architecture |
| [Runbooks](./services/chargeback-service/runbooks/RB-007-chargeback-ops.md) | Operations & debugging for chargeback handling |

#### Root-Cause Classification (Pillar B)
| Document | Purpose |
|----------|---------|
| [ML Pipeline](./services/classification-service/ml-pipeline.md) | ML architecture, SMOTE, Random Forest, Ensemble logic |
| [Multi-LLM Integration](./services/classification-service/multi-llm-integration.md) | Concurrent Groq + Gemini inference |
| [Testing & Results](./services/classification-service/testing-and-results.md) | Benchmarks, stress-test results, accuracy |
| [ADRs](./services/classification-service/decisions/) | Key architectural decisions (Go vs Python, Redis Queues) |

#### Compliance Scanner
| Document | Purpose |
|----------|---------|
| [Architecture](./services/compliance-service/architecture.md) | API design, LLM prompt logic, RBI rule mapping |
| [Multi-LLM Integration](./services/compliance-service/multi-llm-integration.md) | Concurrent Groq + Gemini ensemble, Union strategy |
| [Testing & Results](./services/compliance-service/testing-and-results.md) | E2E test pass results |
| [ADRs](./services/compliance-service/decisions/) | Multi-LLM Union Strategy, JSON schema validation |

### Microservices

#### Frontend Dashboard
| Document | Purpose |
|----------|---------|
| [Architecture](./services/frontend/architecture.md) | SSR, Webhook Simulator, 4-Layer badge system |
| [API & Screens](./services/frontend/api-docs.md) | Detailed UI documentation |
| [ADR-006](./services/frontend/decisions/ADR-006-nextjs-ssr-dashboard.md) | Why Next.js SSR App Router |

#### Ingestion Service (Webhook Gateway)
| Document | Purpose |
|----------|---------|
| [API Definition](./services/ingestion-service/api.md) | Webhook payload definitions |
| [LLD & Flow](./services/ingestion-service/flow.md) | Queueing and routing logic |

#### Audit Service (Event Logging)
| Document | Purpose |
|----------|---------|
| [API Definition](./services/audit-service/api.md) | Logging queries and event retrieval |
| [Database Schema](./services/database/schema.md) | PostgreSQL / MongoDB core schemas |

### Operations & Maintenance
| Document | Purpose |
|----------|---------|
| [Rotate API Keys](./operations/runbooks/RB-004-rotate-llm-api-keys.md) | Rotating Groq/Gemini credentials |
| [Classification Runbooks](./services/classification-service/runbooks/) | Debugging workers and redis queues |
| [Compliance Runbooks](./services/compliance-service/runbooks/) | Resolving compliance violations |
