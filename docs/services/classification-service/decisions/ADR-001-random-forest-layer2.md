# ADR-001: Use Random Forest for Layer 2 Classification

**Status:** Accepted  
**Date:** 2026-08-01  
**Deciders:** Engineering Team  

---

## Context

Layer 2 needs to classify payment failures into 5 root-cause categories using tabular features (status codes, response codes, bank identifiers, retry counts). The dataset is synthetically generated and inherently class-imbalanced (fraud events are rare relative to soft declines).

We evaluated the following candidate model families:
1. Logistic Regression
2. Random Forest
3. XGBoost / Gradient Boosting
4. Fine-tuned Neural Network (e.g. tabular MLP)
5. LLM-only (no ML layer)

---

## Decision

**Use a Random Forest Classifier (scikit-learn) as the Layer 2 model.**

---

## Rationale

| Criterion | Logistic Regression | Random Forest | XGBoost | Neural Net |
|-----------|--------------------|--------------:|---------|------------|
| Accuracy (validation) | ~78% | **96.05%** | ~94% | ~91% |
| Training time | <1s | ~3s | ~8s | ~10 min |
| Inference latency (p99) | <1ms | ~2ms | ~3ms | ~15ms |
| Handles class imbalance (SMOTE) | Poor | **Excellent** | Good | Moderate |
| Interpretability | High | Medium | Low | None |
| Deployment complexity | trivial | trivial | moderate | high |

**Key factors:**
- Random Forest with SMOTE-balanced training data achieved 96.05% validation accuracy — 2% better than XGBoost at a fraction of the infrastructure complexity.
- No GPU required. The `.pkl` model is ~2MB and loads in milliseconds inside the Python FastAPI container.
- Feature importances are natively interpretable, useful for debugging misclassifications.

---

## Consequences

- **Positive:** Extremely low inference latency (~2ms), zero GPU cost, simple deployment as a pickled artifact.
- **Positive:** SMOTE balancing resolves the class-imbalance problem cleanly.
- **Negative:** The model is static. It will drift if Razorpay's gateway partners change their error code semantics. A retraining pipeline is required.
- **Negative:** Cannot learn from free-form text reasoning — this is why Layer 3 (LLM) exists.

---

## Revisit Trigger

If live accuracy drops below 85% after a major gateway partner onboarding, trigger retraining and evaluate XGBoost as a replacement.
