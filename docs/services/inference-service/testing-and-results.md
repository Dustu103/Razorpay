# Testing & Results (Inference Service)

This document tracks the End-to-End (E2E) testing methodology and the performance benchmarks achieved by the localized Machine Learning models hosted in the Inference Gateway.

## 1. Prototype vs. Production Benchmarks

The original Razorpay Revenue Recovery prototype relied on a single synchronous Gemini API call to orchestrate Root-Cause classification, Retry Logic, and False Decline detection.

We systematically isolated and replaced these heavy network calls with optimized **Scikit-Learn Random Forest Classifiers** running concurrently in this `inference-service`.

**Performance Gains on 500 Unseen Synthetic Transactions:**

| Feature | Model Type | Prototype Latency | Inference Service Latency | Accuracy |
|---------|------------|-------------------|---------------------------|----------|
| **Feature A (Root-Cause)** | Layer 2 XGBoost + Layer 3 LLM | ~2.54 seconds | **~8 - 10 ms** | 90% - 95% |
| **Feature B (Retry Routing)** | Random Forest Classifier | ~2.54 seconds | **~15 - 45 ms** | 74.60% |
| **Feature C (Dunning)** | Random Forest Classifier | ~2.54 seconds | **~15 ms** | 87.60% |
| **Feature D (False Decline)** | Random Forest Classifier | ~2.54 seconds | **~5 - 10 ms** | 97.60% |

> [!TIP]
> **Key Takeaway**
> By removing the Google Gemini network dependency from Features B, C, and D, we reduced classification latency from ~2.5 seconds down to ~20 milliseconds on average, while retaining enterprise-grade accuracy (specifically 97.6% on False Decline).

## 2. E2E Test Suite

The `inference-service` is continuously validated using a custom Python E2E suite located at `tests/e2e/inference-service/`.

### False Decline Testing (`test_false_decline.py`)
Sends parameterized HTTP POST requests to `/predict/false-decline`.
* **Scenario 1:** Low Risk IP + Known Device -> Expects `reverify_and_reverse`
* **Scenario 2:** High Risk IP + Unseen Device -> Expects `uphold_block`
* **Status:** `✅ PASS (3/3 Scenarios)`

### Retry & Dunning Testing (`test_retry_dunning.py`)
Validates the fallback logic between the `retry` and `dunning` endpoints.
* **Retry Payload:** High failure count, older failure time -> Expects `retry_success_probability < 0.60` and action `trigger_dunning`.
* **Dunning Payload:** High customer tenure -> Expects `payment_probability > 0.60` and `recommended_channel: email`.
* **Status:** `✅ PASS (2/2 Scenarios)`

## 3. Go Orchestrator Unit Tests

The `classification-service/tests/unit` directory mocks the `inference-service` HTTP server to validate that the Go worker properly interprets the ML probabilities.
* Validates that `ActionReverifyReverse` overrides `fraud_filter_block` only when likelihood exceeds 0.85.
* Validates that a low retry probability correctly falls back to `EvaluateDunning`.
* **Status:** `✅ PASS (All unit tests compile and run successfully)`
