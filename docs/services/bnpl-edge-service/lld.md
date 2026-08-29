# BNPL Edge Service (Engine 1) — Low-Level Design (LLD)

**Version:** 1.0  
**Framework:** Go (Fiber)  
**Port:** 8003

---

## 1. Directory Structure

```text
backend/bnpl-edge-service/
├── main.go            # Fiber application, routing, and timeout middleware
├── go.mod             # Go module definition
├── go.sum             # Go dependencies checksums
└── Dockerfile         # Lightweight Alpine build
```

## 2. API Endpoints

### `POST /v1/checkout/fallback-offer`
The primary edge endpoint called by the checkout UI/gateway when a transaction is declined.

**Request Schema:**
```json
{
    "amount": 6000.0,
    "decline_reason_encoded": 0,
    "tenure_months": 36
}
```
*Note: `decline_reason_encoded` maps reasons to integers (e.g., 0 = Insufficient Funds, 3 = Technical Decline).*

**Response Schema:**
```json
{
    "show_bnpl_offer": true,
    "conversion_probability": 0.95
}
```

## 3. Internal Components

### 3.1 Strict Latency Circuit Breaker (`main.go`)
The service implements a customized `http.Client` with a strict `50ms` timeout. 

```go
client := &http.Client{
    Timeout: 50 * time.Millisecond,
}
```
*   **Logic:** When forwarding the payload to the `inference-service` (Port 8000), the HTTP client will abort the TCP connection exactly at 50ms.
*   **Error Handling:** If a `context deadline exceeded` or timeout error occurs, the Go service catches it and returns a `503 Service Unavailable` or a default fallback response (`show_bnpl_offer: false`), ensuring the frontend is never left hanging.

### 3.2 Downstream ML Integration
The Go service synchronously posts the payload to the Python Inference Gateway:
*   **Target:** `http://inference-service:8000/predict/checkout-offer`
*   **Model:** `feature_e_edge.joblib` (Random Forest Classifier optimized for speed).
*   The Go service acts purely as a passthrough proxy; it performs no feature engineering or business logic of its own, delegating all intelligence to the Python tier.
