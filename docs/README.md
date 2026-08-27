# Feature 1 — Root-Cause Classifier: Documentation Index

> **Project:** Razorpay AI Buildathon 2026 · Feature 1 & 2 (Pillar B — Diagnose)

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
├── classification-service/                    ← All docs for the classification pipeline
│   ├── README.md
│   ├── ml-pipeline.md
│   ├── multi-llm-integration.md
│   ├── testing-and-results.md
│   ├── decisions/                             ← ADRs scoped to this service
│   │   ├── ADR-001-random-forest-layer2.md
│   │   ├── ADR-002-groq-over-openai.md
│   │   ├── ADR-003-redis-queue-over-http.md
│   │   ├── ADR-004-go-for-classification-service.md
│   │   └── ADR-005-multi-llm-ensemble.md
│   └── runbooks/                              ← Ops runbooks scoped to this service
│       ├── RB-001-restart-classification-worker.md
│       ├── RB-002-debug-stuck-redis-queue.md
│       └── RB-003-run-e2e-test-pipeline.md
│
├── compliance-service/                        ← All docs for the compliance scanner (Feature 2)
│   ├── README.md
│   ├── architecture.md
│   ├── testing-and-results.md
│   ├── decisions/
│   │   └── ADR-007-compliance-json-schema-input.md
│   └── runbooks/
│       └── RB-005-debug-compliance-violations.md
│
├── frontend-dashboard/                        ← All docs for the Next.js dashboard
│   ├── README.md
│   ├── architecture.md
│   └── decisions/
│       └── ADR-006-nextjs-ssr-dashboard.md
│
└── operations/                                ← Cross-service / infrastructure runbooks
    └── runbooks/
        └── RB-004-rotate-llm-api-keys.md
```

> **Convention:** Every new service gets its own `docs/<service-name>/` folder containing
> `decisions/` and `runbooks/` subfolders. `docs/architecture/` is reserved for system-wide
> cross-service diagrams only. `docs/operations/` is for shared infrastructure runbooks.

---

## 🔗 Quick Links

### System Architecture
| Document | Purpose |
|----------|---------|
| [HLD](./architecture/hld.md) | Full system picture — start here |
| [Data Pipeline](./architecture/flow-diagrams/data-pipeline.md) | End-to-end webhook-to-inference flow |

### Classification Service
| Document | Purpose |
|----------|---------|
| [ML Pipeline](./classification-service/ml-pipeline.md) | ML architecture, SMOTE, Random Forest, Ensemble logic |
| [Multi-LLM Integration](./classification-service/multi-llm-integration.md) | Concurrent Groq + Gemini inference |
| [Testing & Results](./classification-service/testing-and-results.md) | Benchmarks, stress-test results, accuracy |
| [ADR-001](./classification-service/decisions/ADR-001-random-forest-layer2.md) | Why Random Forest for Layer 2 |
| [ADR-002](./classification-service/decisions/ADR-002-groq-over-openai.md) | Why Groq as primary LLM |
| [ADR-003](./classification-service/decisions/ADR-003-redis-queue-over-http.md) | Why Redis queue over sync HTTP |
| [ADR-004](./classification-service/decisions/ADR-004-go-for-classification-service.md) | Why Go for the classification-service |
| [ADR-005](./classification-service/decisions/ADR-005-multi-llm-ensemble.md) | Why concurrent Multi-LLM ensemble |
| [RB-001](./classification-service/runbooks/RB-001-restart-classification-worker.md) | Restart stuck classification worker |
| [RB-002](./classification-service/runbooks/RB-002-debug-stuck-redis-queue.md) | Debug growing Redis queue |
| [RB-003](./classification-service/runbooks/RB-003-run-e2e-test-pipeline.md) | Post-deployment E2E validation |

### Compliance Service (Feature 2)
| Document | Purpose |
|----------|---------|
| [Architecture](./compliance-service/architecture.md) | API design, LLM prompt logic, RBI rule mapping |
| [Testing & Results](./compliance-service/testing-and-results.md) | 13/13 E2E test pass results |
| [ADR-007](./compliance-service/decisions/ADR-007-compliance-json-schema-input.md) | Why JSON schema over web scraper |
| [RB-005](./compliance-service/runbooks/RB-005-debug-compliance-violations.md) | Debug false positives / negatives |

### Frontend Dashboard
| Document | Purpose |
|----------|---------|
| [Architecture](./frontend-dashboard/architecture.md) | SSR, Webhook Simulator, 4-Layer badge system |
| [ADR-006](./frontend-dashboard/decisions/ADR-006-nextjs-ssr-dashboard.md) | Why Next.js SSR App Router |

### Operations (Cross-Service)
| Document | Purpose |
|----------|---------|
| [RB-004](./operations/runbooks/RB-004-rotate-llm-api-keys.md) | Rotate Groq / Gemini API keys |
