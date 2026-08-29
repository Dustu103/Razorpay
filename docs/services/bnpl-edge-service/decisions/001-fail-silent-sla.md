# ADR 001: Strict 50ms Fail-Silent Circuit Breaker

**Date:** 2026-08-30  
**Status:** Accepted  

## Context
When a user experiences a payment decline at checkout, they are statistically highly likely to abandon their cart. To recover this revenue, we want to inject a dynamic BNPL offer directly into the UI upon a decline event. However, querying the Python ML backend (Random Forest) for a personalized conversion probability takes time.

If the ML query takes 500ms, the user sits staring at a spinning loading wheel on the checkout page for half a second. According to e-commerce latency studies, every 100ms of delay in the checkout path drops conversion by 1-3%. A 500ms delay to fetch a fallback offer might actually cause more cart abandonment than the baseline decline rate itself.

## Decision
We will enforce a hard, uncompromising **50ms HTTP timeout** on the Go Edge Service when querying the Python ML Gateway. 

If the ML Gateway takes 51ms to respond, the Go client will terminate the connection (`context deadline exceeded`) and **fail silently**. The Edge Service will immediately return `show_bnpl_offer: false` to the frontend, allowing the standard decline UI to render instantly.

## Consequences

**Positive:**
*   Checkout conversion rates are strictly protected from backend ML latency spikes.
*   The Go proxy will never bottleneck or exhaust connection pools waiting for slow Python workers.
*   Provides clear, hard SLA targets for the Data Science team (models must execute in < 40ms to account for 10ms of network jitter).

**Negative:**
*   During extreme traffic spikes (like Diwali sales) where the ML inference gateway slows down, the BNPL fallback offers will entirely drop to 0% injection rate. 
*   We prioritize the speed of the primary transaction flow over the recovery rate of the fallback flow.
