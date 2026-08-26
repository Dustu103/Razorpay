# AI Service — Machine Learning Pipelines

This directory contains all offline ML workloads for Feature 1 (Root-Cause Classifier).
Inference (Layer 2 & 3) runs in the cloud/API — this directory handles data, fine-tuning, and validation.

## Architecture

```
ai-service/
├── scripts/
│   ├── generate_synthetic_data.py   ← Bootstrap labeled data using Groq LLM
│   └── validate_pipeline.py         ← Cost-weighted confusion matrix (TDD §3.2)
├── data/                            ← Generated datasets (gitignored)
│   └── synthetic_labeled.jsonl
├── notebooks/                       ← Jupyter notebooks for exploration
└── requirements.txt
```

## Setup

```bash
cd ai-service
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

## Layer 3 — Groq LLM (Free)

Layer 3 uses **Llama 3.1 70B via Groq** (completely free, no credit card).

1. Get a free key at [console.groq.com](https://console.groq.com)
2. Add it to your root `.env` file:
   ```
   GROQ_API_KEY=gsk_your_key_here
   ```

The classification service reads this env var at startup. If it is not set, Layer 3 falls back to heuristics — the pipeline still works.

## Generate Synthetic Data

```bash
# With LLM labeling (recommended — uses Groq free tier)
python scripts/generate_synthetic_data.py --count 500 --output data/synthetic_labeled.jsonl

# Without LLM (heuristic labels — fast, offline)
python scripts/generate_synthetic_data.py --count 500 --no-llm
```

## Validate Pipeline

```bash
python scripts/validate_pipeline.py --data data/synthetic_labeled.jsonl
```

Output includes:
- Per-cause accuracy with pass/fail at 80% threshold
- Cost-weighted confusion matrix (penalizes dangerous misclassifications)
- Per-action threshold compliance (mirrors the Go worker thresholds)

## Key Design Decisions (from TDD v2)

| Decision | Why |
|---|---|
| Groq (free) instead of OpenAI | Zero cost, OpenAI-compatible API, 45ms avg latency |
| Llama 3.1 70B | Best open-weight model for structured classification as of Aug 2026 |
| Temperature = 0.1 | Low temperature → deterministic, consistent classifications |
| Cost-weighted validation | Raw accuracy hides expensive mistakes (e.g. missing fraud costs 9x more than a wrong retry) |
