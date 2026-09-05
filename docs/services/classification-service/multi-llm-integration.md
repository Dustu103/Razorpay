# Multi-LLM Integration (Layer 3)

> **Feature:** Resilient AI Root-Cause Inference via Multi-LLM Concurrency
> **Scope:** `backend/classification-service/internal/layer3`

## 1. Overview

The `classification-service` leverages an advanced Multi-LLM architecture (Mixture-of-Experts) to infer the root cause of failed transactions that cannot be handled by deterministic logic or high-confidence ML.

To eliminate Single Point of Failure (SPOF) risks, latency spikes, and provider-level rate-limiting (e.g., HTTP 429), Layer 3 queries multiple LLM providers **concurrently**. 

## 2. Supported LLM Providers

We have implemented integrations with:

1.  **Groq (`llama3-70b-8192`)**
    *   **Advantage:** Ultra-low latency Llama-based inference.
    *   **Risk:** Highly aggressive rate limits on free developer tiers.
2.  **Google Gemini (`gemini-1.5-flash`)**
    *   **Advantage:** State-of-the-art context window and highly structured JSON output capabilities.
    *   **Risk:** Occasional `context deadline exceeded` in testing environments if invalid API keys are intercepted by networking layers.

## 3. Concurrent Inference Architecture

When a transaction enters Layer 3, the service spawns distinct Go routines for every configured LLM provider.

```go
func Classify(txn *models.Transaction) (*models.ClassificationResult, error) {
    // 1. Check active environment keys
    // 2. Spawn concurrent Go routines for Groq & Gemini
    // 3. Wait with a strict bounded context timeout
    // 4. Resolve the Best Response
}
```

### 3.1 Strict Timeout Management

Both LLMs run inside a `context.WithTimeout` bounded to **3 seconds**. If an LLM provider hangs or rate-limits, the connection is instantly aborted to prevent queue backpressure in the Go Worker pool.

### 3.2 Result Resolution Logic

The service resolves the multi-LLM outputs using the following deterministic strategy:
1.  **Dual Success:** If both LLMs return successfully, Layer 3 picks the response with the **higher reported confidence score**.
2.  **Partial Failure:** If one LLM fails (e.g., HTTP 429 from Groq), the system instantly returns the success of the other (e.g., Gemini).
3.  **Total Failure (Fallback):** If both LLMs fail (or time out), the system falls back to the deterministic `heuristicFallback` logic, which assigns a safe `soft_decline` prediction with a `0.60` confidence to ensure the transaction can be retried safely.

## 4. Concurrency Management & Queue Resilience

The Go worker (`worker.go`) runs a highly concurrent `BLPOP` consumer loop utilizing a **Semaphore pattern** (bounded at `50` concurrent workers). 

```go
sem := make(chan struct{}, 50)
sem <- struct{}{}
go func(j models.ClassificationJob) {
    defer func() { <-sem }()
    processJob(ctx, j)
}(job)
```

This ensures that a sudden influx of Webhooks will not exhaust connection pools, while allowing multi-LLM timeouts to execute independently without blocking the entire job queue.

## 5. Configuration

To enable the providers, inject the following environment variables into the `classification-service`:

*   `GROQ_API_KEY`: API Key retrieved from [console.groq.com](https://console.groq.com)
*   `GEMINI_API_KEY`: API Key retrieved from Google AI Studio.
