# Classification Service — Documentation Index

> All technical documentation for the `classification-service` lives here.

## Documents

| File | Description |
|------|-------------|
| [ml-pipeline.md](./ml-pipeline.md) | ML Lifecycle, Feature Engineering, SMOTE balancing, Random Forest training & Layer 4 Ensemble logic |
| [multi-llm-integration.md](./multi-llm-integration.md) | Concurrent Groq + Gemini LLM architecture, semaphore worker, 3-second circuit breaker |
| [testing-and-results.md](./testing-and-results.md) | Test harnesses, empirical accuracy benchmarks (96% offline, stress-test results) |

## Service Overview

The `classification-service` is the core intelligence layer of the Razorpay Root-Cause Classifier. It implements a **4-Layer Mixture-of-Experts (MoE)** decision engine:

- **Layer 1** — Deterministic rule engine (zero latency, hard-coded known codes)
- **Layer 2** — Fine-tuned Random Forest ML model (96% offline accuracy)
- **Layer 3** — Multi-LLM inference (Groq + Gemini, concurrent goroutines)
- **Layer 4** — Ensemble tie-breaker (ML confidence vs LLM consensus)

For system-wide context, see the [High-Level Design](../architecture/hld.md).
