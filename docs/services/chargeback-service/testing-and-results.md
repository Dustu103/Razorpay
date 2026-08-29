# Chargeback Service – Testing & Results

**Version:** 1.0  
**Status:** MVP Validation Phase  

---

## 1. Test Harness Overview

The `chargeback-service` is validated using a predefined 15-scenario E2E test suite located at `tests/e2e/chargeback-service/test_chargeback.py`. The suite validates the Multi-LLM Ensemble's ability to accurately predict win probabilities and route disputes based on complex combinations of reason codes (Visa, Mastercard, RuPay), evidence artifacts, and deadline proximity.

To run the tests locally against the Docker container:
```bash
docker run --rm --network razorpay_default \
  -e API_URL="http://chargeback-service:3005/api/v1/analyze-dispute" \
  -v "${PWD}/tests/e2e:/scripts" \
  razorpay-chargeback-service:latest \
  bash -c "pip install requests -q && python /scripts/chargeback-service/test_chargeback.py"
```

---

## 2. Live Test Results

The Multi-LLM Ensemble (Groq + Gemini) was evaluated on 15 complex E2E dispute scenarios.

*   **Sample Size:** 15 Predefined Hard Scenarios
*   **Accuracy Achieved:** **80.00% (12/15 passed)**
*   **Analysis:** The service correctly routed and predicted the outcome for 12 complex cases (including Visa 10.4 CE 3.0, RuPay 1065 near deadline, and MC 4853). 

### Identified Failure Cases (The remaining 20%):
The 3 failed scenarios were primarily caused by edge cases involving Extreme High Value disputes (e.g., ₹1,50,000+). 
- **Expected Action:** `auto_submit` or `one_tap_approval` (due to strong evidence).
- **Ensemble Action:** Recommended manual `review`. 
- **Root Cause:** The LLM prompt engineering naturally biases towards human scrutiny when the financial risk is exceptionally high, which clashed with the rigid test expectations. 

---

## 3. Optimization Path for >95% Accuracy

To elevate the Chargeback service's accuracy from 80% to >95% on the test suite:
1. **Refine Prompt Engineering:** Add explicit prompt guidelines to the LLM that instruct it to favor `auto_submit` if evidence is hermetically strong (e.g., CE 3.0 qualified with 3DS/AVS/CVV), regardless of the transaction value.
2. **Context Bridge Calibration:** Ensure the rule engine strictly overrides the LLM's caution when the `merchant_current_dispute_ratio` is extremely low (e.g., `< 0.002`).
