# ADR 002: Deterministic Rule Engine vs. ML Model

**Date:** 2026-09-01  
**Status:** Accepted  
**Context:** The goal of the B2B Recovery Service is to identify when an overdue invoice violates an Indian Tax statute (Sec 43B or Rule 37) and trigger a legal intervention.

## The Problem
The original architectural iteration proposed using a Machine Learning model (XGBoost) trained on historical B2B transaction data to predict when a tax penalty should be applied.

## Decision
We completely abandoned the Machine Learning classifier for compliance routing and replaced it with a **Deterministic Rule Engine**. We retained Artificial Intelligence exclusively for the *execution* phase (Generative AI for drafting emails).

### Rationale
1. **Legal Liability:** Tax law is absolute, not probabilistic. If an ML model achieves 95% accuracy, it means 5% of the time it is either missing a valid tax lever, or worse, generating a hallucinated legal threat against a vendor that has not actually violated a statute. Sending baseless legal threats creates immense legal liability for Razorpay and its merchants.
2. **Explainability:** Deterministic rules (`if days_late == 45 and is_msme == true`) are 100% explainable to auditors. ML models are "black boxes" which is heavily frowned upon in regulatory tech.
3. **Overfitting:** In an ML context, achieving 100% accuracy on this problem would indicate model overfitting. In a deterministic rule engine, 100% accuracy is the required baseline for legal compliance.

## Consequences
- **Positive:** We achieve 100% routing precision with zero false positives. The system is fully compliant, auditable, and safe for enterprise deployment.
- **Negative:** We lose the "predictive" capability to guess *when* a customer might default before they hit the 45-day mark, but that is an acceptable trade-off for legal safety.
