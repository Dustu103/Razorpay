# Inference Service Flow Diagrams

The Inference Service acts as the centralized Machine Learning Gateway for the Razorpay Enterprise backend. It exposes multiple REST endpoints designed to be called asynchronously by high-throughput worker orchestrators (like the Classification Service).

## 1. Mixture of Experts Orchestration

This diagram illustrates how the `classification-service` leverages the `inference-service` to resolve root-cause classifications, including fallback mechanisms to `False Decline`, `Retry Routing`, and `Dunning Optimization`.

```mermaid
sequenceDiagram
    participant Worker as Go Worker (Classification)
    participant Layer1 as Deterministic (Layer 1)
    participant API as Inference Gateway
    participant PaymentML as Payment XGBoost
    participant Ensemble as Dispute Ensemble
    participant FalseDeclineML as False Decline RF
    participant RetryML as Retry Routing RF
    participant DunningML as Dunning RF
    
    Note over Worker: New Transaction Processing
    Worker->>Layer1: Check Hard Decline Rules
    
    alt Match found
        Layer1-->>Worker: Return (e.g., ActionDoNotRetry)
    else No match
        Worker->>API: POST /predict/payment
        par ML Inference
            API->>PaymentML: Predict Layer 2 Probability
            PaymentML-->>API: Fraud Score
        and LLM Inference
            Worker->>Ensemble: Predict Layer 3 Win Rate (LLM)
        end
        API-->>Worker: Layer 2 Confidence & Cause
        
        Note over Worker: Ensemble Agreement check
        
        alt fraud_filter_block
            Worker->>API: POST /predict/false-decline
            API->>FalseDeclineML: Analyze Risk Profile
            FalseDeclineML-->>API: 0.95 Likelihood
            API-->>Worker: ActionReverifyReverse
        else soft_decline
            Worker->>API: POST /predict/retry
            API->>RetryML: Check Retry Viability
            RetryML-->>API: 0.20 Probability
            Note over Worker: Low Retry Prob, fallback to Dunning
            Worker->>API: POST /predict/dunning
            API->>DunningML: Best Comm Channel?
            DunningML-->>API: "sms"
            API-->>Worker: trigger_dunning_sms
        end
    end
    
    Worker->>Database: Persist Final Classification
```

## 2. In-Memory Model Management

All models are built via offline training scripts and deployed as `.joblib` or `.pkl` artifacts. The FastAPI application strictly loads these into memory **once** on container startup to prevent disk I/O bottlenecks.

```mermaid
flowchart TD
    subgraph Container Startup
        A[FastAPI App Boots] --> B{Check /models/ml/}
        B --> C[Load layer2_payment_failure_model.pkl]
        B --> D[Load feature_b.joblib]
        B --> E[Load feature_c.joblib]
        B --> F[Load feature_d.joblib]
        C --> G[Global Memory Allocation]
        D --> G
        E --> G
        F --> G
    end
    
    subgraph Active Inference
        H[POST Request] --> I{Endpoint Router}
        I -->|/predict/payment| J[XGBoost Prediction]
        I -->|/predict/false-decline| K[Feature D Prediction]
        I -->|/predict/retry| L[Feature B Prediction]
        I -->|/predict/dunning| M[Feature C Prediction]
        
        G --> J
        G --> K
        G --> L
        G --> M
    end
```
