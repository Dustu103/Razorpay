# ADR-001: Causal Net-EV Decisioning vs Naive Abandoned Cart Blasting

## Status
Accepted

## Context
Commercial e-commerce drop-off tools (e.g. standard Shopify/WooCommerce recovery bots) employ a naive rule: whenever a checkout is abandoned, send an automated WhatsApp message offering a discount.

In high-volume payment processing across the Indian retail ecosystem, this naive strategy causes significant financial harm:
1. **Cannibalization of Organic Purchases**: Many shoppers return organically ($P_0 > 0.40$). Offering a 10% discount and paying ₹0.80 for WhatsApp actively destroys merchant gross margin.
2. **Reverse Logistics (RTO) Amplification**: In COD-heavy segments (fashion/apparel), aggressive recovery messages often spur impulsive re-orders that get refused at delivery, inflicting severe ₹250–₹280 reverse-logistics freight losses.
3. **Channel Cost Inefficiency**: WhatsApp messages cost ₹0.80 vs SMS (₹0.20) and Email (₹0.05). For lower-ticket orders (₹250–₹500), messaging costs exceed the entire incremental margin.

## Decision
We decouple detection from intervention and enforce a **Dual Causal Machine Learning Architecture**:
1. **Inference Separation**: `dropoff-service` detects expired sessions and provides telemetry, while `inference-service` predicts conditional counterfactual recovery probabilities ($P_a$) and action-specific return-to-origin risks ($r_a$).
2. **Exact Causal Net-EV Engine**: Interventions are evaluated against the true general causal profit formula:
   $$\Delta\Pi_a = P_a[(1 - r_a)(CM - D_a) - r_a K_{RTO}] - P_0[(1 - r_0)CM - r_0 K_{RTO}] - K_a$$
3. **Mandatory Liveness & Suppression Guards**: If the maximum $\Delta\Pi_a \le 0$, the engine explicitly commands `NO_ACTION` to preserve merchant margins.

## Consequences
- **Positive**: Eliminates wasted messaging CAC and prevents thousands of rupees in RTO losses on COD orders. Captures ~88% of theoretical oracle profit.
- **Trade-off**: Requires running dual LightGBM models (`causal_s_model.pkl` and `causal_rto_model.pkl`) via HTTP on checkout expiration. Sub-15ms inference latency maintained.
