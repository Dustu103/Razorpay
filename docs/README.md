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
│   ├── dropoff-service/                       ← Real-Time Checkout Drop-Off Recovery (Go + Causal ML)
│   │   ├── hld.md
│   │   ├── lld.md
│   │   ├── testing-and-results.md
│   │   ├── decisions/
│   │   └── runbooks/
│   │
│   ├── b2b-recovery-service/                  ← Autonomous B2B Overdue Invoice Recovery
│   │   ├── hld.md
│   │   ├── lld.md
│   │   ├── testing-and-results.md
│   │   ├── decisions/
│   │   └── runbooks/
│   │
│   ├── nach-recovery-service/                 ← Autonomous NACH Mandate Recovery Service (Port 3007)
│   │   ├── hld.md
│   │   ├── lld.md
│   │   ├── testing-and-results.md
│   │   ├── decisions/
│   │   └── runbooks/
│   │
│   ├── bnpl-edge-service/                     ← BNPL Edge Payment Authorization
│   │   ├── hld.md
│   │   └── lld.md
│   │
│   ├── chargeback-service/                    ← Autonomous Chargeback Pre-emption (Pillar A)
│   │   ├── architecture.md
│   │   ├── runbooks.md
│   │   └── adr-008.md
│   │
│   ├── classification-service/                ← Root-Cause Classifier & NACH Mandate Recovery Engine
│   │   ├── README.md
│   │   ├── hld.md
│   │   ├── lld.md
│   │   ├── flow.md
│   │   ├── ml-pipeline.md
│   │   ├── multi-llm-integration.md
│   │   ├── nach-testing-and-results.md
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

#### Root-Cause Classification & NACH Mandate Recovery (Pillar B)
| Document | Purpose |
|----------|---------|
| [HLD](./services/classification-service/hld.md) | 5-Layer classification architecture, NACH Layer 0 stopping rules & post-ensemble routing |
| [LLD](./services/classification-service/lld.md) | Go package structure, interfaces, worker orchestration & database models |
| [Flow Diagram](./services/classification-service/flow.md) | Sequence diagram from Redis queue to Layer 0/1/Ensemble to PostgreSQL |
| [ML Pipeline](./services/classification-service/ml-pipeline.md) | ML architecture, SMOTE, Random Forest, Ensemble logic |
| [Multi-LLM Integration](./services/classification-service/multi-llm-integration.md) | Concurrent Groq + Gemini rail-aware inference |
| [NACH Testing & Results](./services/classification-service/nach-testing-and-results.md) | NACH Mandate Recovery batch simulation (+51.3% lift, 114 attempts saved) |
| [Testing & Results](./services/classification-service/testing-and-results.md) | Benchmarks, stress-test results, accuracy |
| [Runbook RB-004](./services/classification-service/runbooks/RB-004-nach-mandate-recovery-operations.md) | Operations, AMC auto-cancellation debugging & invariant monitoring |
| [ADRs](./services/classification-service/decisions/) | Key architectural decisions (Go vs Python, Redis Queues) |

#### Compliance Scanner
| Document | Purpose |
|----------|---------|
| [Architecture](./services/compliance-service/architecture.md) | API design, LLM prompt logic, RBI rule mapping |
| [Multi-LLM Integration](./services/compliance-service/multi-llm-integration.md) | Concurrent Groq + Gemini ensemble, Union strategy |
| [Testing & Results](./services/compliance-service/testing-and-results.md) | E2E test pass results |
| [ADRs](./services/compliance-service/decisions/) | Multi-LLM Union Strategy, JSON schema validation |

#### Checkout Drop-Off Recovery (Causal Revenue Engine)
| Document | Purpose |
|----------|---------|
| [HLD](./services/dropoff-service/hld.md) | Real-time Redis ZSET session tracker & Causal Gateway orchestration |
| [LLD](./services/dropoff-service/lld.md) | Event stream analysis, state machine, and diagnostic classifier |
| [ADR-001](./services/dropoff-service/decisions/ADR-001-causal-dropoff-detection.md) | Causal Net-EV Engine vs naive abandoned cart blasting |
| [Runbooks](./services/dropoff-service/runbooks/RB-001-dropoff-service-operations.md) | Operational runbooks, health checks & queue troubleshooting |
| [Testing & Results](./services/dropoff-service/testing-and-results.md) | Invariants test pass results, vertical benchmarks, and model artifacts |

#### B2B Invoice Recovery (Tax Lever)
| Document | Purpose |
|----------|---------|
| [HLD](./services/b2b-recovery-service/hld.md) | Hybrid event-batch pattern & statutory tax penalty automation |
| [LLD](./services/b2b-recovery-service/lld.md) | Database schemas, cron scheduler, and Groq LLM notice generator |

#### NACH Mandate Recovery (Recurring Revenue Engine)
| Document | Purpose |
|----------|---------|
| [HLD](./services/nach-recovery-service/hld.md) | Governor stopping engine, AMC 3-failure SIP cap, EMI 28-day credit risk |
| [LLD](./services/nach-recovery-service/lld.md) | API schemas, port 3007 endpoints, Go package structure |
| [Testing & Results](./services/nach-recovery-service/testing-and-results.md) | 100-batch simulation results (+51.3% lift, 114 attempts saved) |
| [ADR-001](./services/nach-recovery-service/decisions/ADR-001-nach-recovery-service-architecture.md) | Dedicated microservice architecture |
| [Runbook RB-001](./services/nach-recovery-service/runbooks/RB-001-nach-operations.md) | Operational monitoring, metrics verification & troubleshooting |

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
