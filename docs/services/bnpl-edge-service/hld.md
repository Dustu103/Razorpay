# BNPL Edge Service (Engine 1) — High-Level Design (HLD)

**Version:** 1.0  
**Author:** Engineering Team  
**Status:** Approved  

---

## 1. Problem Statement
When a customer experiences a payment decline (e.g., insufficient funds) during checkout, they typically abandon their cart, resulting in lost revenue. However, immediately injecting a "Buy Now, Pay Later" (BNPL) offer into the checkout UI can save the sale. The core challenge is latency: delaying the checkout flow by even a few hundred milliseconds causes conversion rates to drop. We must predict BNPL conversion probability in real-time without violating strict checkout latency SLAs.

## 2. Solution Overview
The `bnpl-edge-service` (Engine 1 of the Dual-Engine BNPL System) is an ultra-fast Go microservice acting as a real-time proxy. It intercepts transaction decline events and queries the centralized Python Inference Service. To protect checkout conversion, it enforces a hard 50ms circuit breaker: if the ML backend cannot respond within 50ms, the edge service fails silently, allowing the standard decline screen to render.

## 3. High-Level Architecture

```mermaid
sequenceDiagram
    participant Checkout UI
    participant Edge Gateway (Go)
    participant ML Inference (Python)
    
    Checkout UI->>Edge Gateway (Go): POST /v1/checkout/fallback-offer
    
    rect rgb(200, 150, 255)
        Note over Edge Gateway (Go), ML Inference (Python): STRICT 50ms SLA WINDOW
        Edge Gateway (Go)->>ML Inference (Python): HTTP POST /predict/checkout-offer
        
        alt ML Answers in < 50ms
            ML Inference (Python)-->>Edge Gateway (Go): BNPL Conversion Prediction
            Edge Gateway (Go)-->>Checkout UI: show_bnpl_offer: true
        else ML Too Slow (> 50ms)
            Note over Edge Gateway (Go): Timeout Trips (Fail Silent)
            Edge Gateway (Go)-->>Checkout UI: Error 503 / Default Decline
        end
    end
```

## 4. Key Design Decisions

1. **Language Choice (Go + Fiber):** We chose Go for the Edge Gateway for its sub-millisecond overhead and highly efficient goroutine scheduling, ensuring the proxy itself adds virtually zero latency to the 50ms SLA.
2. **Fail-Silent Policy:** Timeouts in the critical checkout path are dictated by business SLAs, not by backend latency. If the ML model is too slow, we do not extend the timeout; we fail silently to preserve the user experience.
3. **Decoupled Machine Learning:** By keeping the Python Random Forest model in the `inference-service`, we can scale the Go Edge Gateway horizontally to handle massive checkout spikes without copying heavy Python ML dependencies across containers.
