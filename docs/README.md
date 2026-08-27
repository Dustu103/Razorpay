# Feature 1 — Root-Cause Classifier: Documentation Index

> **Project:** Razorpay AI Buildathon 2026 · Feature 1 (Pillar B — Diagnose)

This directory contains all technical and non-technical documentation for Feature 1.

---

## 📁 Structure

```
docs/
├── README.md                        ← You are here
│
├── meetings/
│   ├── group/                       ← Agendas for cross-functional meetings (what docs to present + decisions to make)
│   └── developer/                   ← Agendas for engineering syncs (which LLD/API/DB sections to walk through)
│
├── architecture/
│   ├── hld.md                       ← High-Level Design (system overview, service map)
│   ├── ml-pipeline.md               ← ML Lifecycle, Feature Engineering, Training, & Ensemble Logic
│   ├── multi-llm-integration.md     ← Concurrent Groq + Gemini LLM tie-breaker architecture
│   ├── testing-and-results.md       ← Test harnesses, empirical accuracy metrics, bottlenecks
│   └── flow-diagrams/
│       ├── data-pipeline.md         ← End-to-end data flow
│       └── ...
│
├── ai-service/                      ← Machine Learning pipelines
│   ├── notebooks/                   ← Synthetic data generation & exploration
│   └── scripts/                     ← Fine-tuning and validation scripts
│
├── (Co-located Docs)                ← Service-specific docs live beside their code:
│   ├── backend/ingestion-service/docs/  ← Ingestion API & LLD
│   ├── backend/classification-service/docs/ ← Classification LLD
│   ├── backend/audit-service/docs/      ← Audit API & LLD
│   ├── frontend/docs/                   ← Frontend LLD, UI specs & BFF API
│   └── db/docs/                         ← Database schema & models
```

---

## 🔗 Quick Links

| Document | Purpose |
|----------|---------|
| [HLD](./architecture/hld.md) | Where to start — full system picture |
| [ML Pipeline](./architecture/ml-pipeline.md) | ML architecture, SMOTE balancing, Model training, & Tie-breaker logic |
| [Multi-LLM Integration](./architecture/multi-llm-integration.md) | Concurrent Groq + Gemini Inference Architecture |
| [Data Pipeline](./architecture/flow-diagrams/data-pipeline.md) | End-to-end flow from Webhook to Inference |
| [Testing & Results](./architecture/testing-and-results.md) | Test scripts, 96% offline accuracy, Groq API bottlenecks |
| [Ingestion LLD](../backend/ingestion-service/docs/lld.md) | Ingestion service details |
| [Audit API](../backend/audit-service/docs/api.md) | Audit endpoints |
| [Database](../db/docs/schema.md) | Schema, ERD, dedup strategy |
| [Frontend LLD](../frontend/docs/lld.md) | Component tree, data flow, screens |
