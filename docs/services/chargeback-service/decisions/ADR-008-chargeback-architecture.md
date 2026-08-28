# ADR-008: 5-Model ML Ensemble & Cost-Aware LLM Routing for Chargeback Pre-emption

## Context
Payment chargebacks arrive with long reporting delays (30-120 days), creating a sparse label space. Merchants require an automated triage mechanism to represent cases with high win rates and deflect (refund) unwinnable ones to stay within the card network's VAMP (Visa/MC) thresholds.

## Design Decisions

### 1. 5-Model Ensemble vs. Single Tree Model
- **Decision:** Implement a 5-model ensemble (`Logistic Regression`, `Random Forest`, `Gradient Boosting`, `XGBoost`, `LightGBM`) rather than relying solely on XGBoost or Random Forest.
- **Rationale:** Disagreement between model structures (e.g. tree-based vs linear) represents epistemic uncertainty. Standard deviation of probabilities acts as a calibrated threshold. If the standard deviation exceeds the validation-calibrated threshold, it is routed to human review, preventing automated errors on borderline cases.

### 2. Single "Explainer" for SHAP Value Extraction
- **Decision:** Choose the highest AUC model (Gradient Boosting) as the single explainer. Extract SHAP feature importance only from this model.
- **Rationale:** SHAP values cannot be averaged across disparate tree architectures (e.g. Random Forest splits are different from XGBoost boosted trees). Averaging them corrupts feature attribution.

### 3. Cost-Aware LLM Routing
- **Decision:** Route low-value (< ₹5,000) or high-confidence disputes to a single cost-effective model (Groq). Route high-value (>= ₹5,000) or high-variance disputes to a parallel ensemble (Groq + Gemini) with automated text scoring.
- **Rationale:** Balances API costs with representment quality. High-value representments justify parallel generation and custom selection.

## Implications
- System requires all 5 models to be saved into a single pickle file (`all_models.pkl`).
- Docker images must install `libgomp1` to support OpenMP requirements of LightGBM.
