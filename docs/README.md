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
│   └── flow-diagrams/
│       ├── data-pipeline.md         ← End-to-end data flow
│       └── ...
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
| [Data Pipeline](./architecture/flow-diagrams/data-pipeline.md) | End-to-end flow |
| [Ingestion LLD](../backend/ingestion-service/docs/lld.md) | Ingestion service details |
| [Audit API](../backend/audit-service/docs/api.md) | Audit endpoints |
| [Database](../db/docs/schema.md) | Schema, ERD, dedup strategy |
| [Frontend LLD](../frontend/docs/lld.md) | Component tree, data flow, screens |
