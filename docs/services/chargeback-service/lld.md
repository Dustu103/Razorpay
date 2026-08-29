# Chargeback Service — Low-Level Design (LLD)

**Version:** 1.0  
**Framework:** FastAPI (Python 3.11)  
**Port:** 3005

---

## 1. Directory Structure

```text
backend/chargeback-service/
├── app/
│   ├── main.py            # FastAPI application and endpoint routing
│   ├── models/            # Pydantic schemas (Request/Response)
│   ├── services/          
│   │   ├── rules.py       # Layer 1: VAMP and deterministic rules
│   │   ├── ml_client.py   # Layer 2: HTTP client for inference-service
│   │   ├── llm_router.py  # Layer 3: Groq/Gemini Multi-LLM logic
│   │   └── scrubber.py    # Layer 4: Hallucination Guard Regex
│   └── database/          # PostgreSQL SQLAlchemy models & sessions
├── requirements.txt
└── Dockerfile
```

## 2. API Endpoints

### `POST /analyze-dispute`
The primary ingestion endpoint for webhooks.

**Request Schema (`DisputeRequest`):**
```json
{
  "dispute_id": "disp_8d9a2b",
  "amount": 12500.50,
  "currency": "INR",
  "reason_code": "Visa 10.4",
  "customer_history": {
    "prior_disputes": 2,
    "account_age_days": 450
  },
  "evidence": {
    "has_avs_match": true,
    "has_cvv_match": true,
    "has_delivery_proof": false
  }
}
```

**Response Schema (`DisputeAnalysisResponse`):**
```json
{
  "dispute_id": "disp_8d9a2b",
  "win_probability": 0.82,
  "recommended_action": "FIGHT",
  "draft_rebuttal": "Dear Issuer, we are writing to represent...",
  "flagged_for_manual_review": false
}
```

## 3. Internal Components

### 3.1 VAMP Protection Module (`rules.py`)
This module queries Redis for the merchant's current rolling 30-day dispute ratio.
*   **Logic:** `if (total_disputes / total_transactions) > 0.014:`
*   **Action:** Returns an instant `DEFLECT` recommendation, bypassing ML and LLM steps to save inference costs and protect the merchant.

### 3.2 Context Bridge (`llm_router.py`)
To prevent the LLM from hallucinating, we use SHAP (SHapley Additive exPlanations) values returned from the ML Gateway. 
The Context Bridge injects these explicitly into the System Prompt:
```python
system_prompt = f"""
You are a legal dispute resolution expert.
You must construct a rebuttal for reason code {request.reason_code}.
The Machine Learning engine identified these critical evidence features:
1. {shap_feature_1}
2. {shap_feature_2}
Base your entire argument strictly around these points.
"""
```

### 3.3 The Scrubber (`scrubber.py`)
A compiled set of regular expressions designed to catch and redact common LLM errors before the letter is saved to the database.
*   `re.sub(r'\[Insert.*?\]', '', text)` -> Removes hallucinated placeholders
*   `re.sub(r'(?i)(machine learning|win probability|xgboost)', '', text)` -> Prevents internal metrics from leaking to external banks.
