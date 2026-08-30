# Razorpay AI Buildathon 2026: The Revenue Recovery Ecosystem

Welcome to the ultimate Revenue Recovery Ecosystem built for the Razorpay AI Buildathon.

Instead of a single feature, we built a comprehensive, legally compliant **3-Pillar Architecture** designed to stop revenue leaks across the entire payment lifecycle.

## 🏗️ The 3 Pillars

### Pillar A: Chargeback Pre-emption (Prevent)
A production-grade automated triage pipeline for disputes.
*   **VAMP Protection:** Deflects unwinnable cases to protect the merchant's Visa Acquirer Monitoring Program (VAMP) ratio from exceeding the 1.5% limit.
*   **Multi-LLM Rebuttals:** Uses Groq (fast/cheap) and Gemini (complex/heavy) to generate perfect, network-compliant representment drafts.

### Pillar B: Root-Cause Diagnostics (Diagnose)
An intelligent payment failure diagnostics engine.
*   **Deterministic + ML:** Analyzes bank response codes, AVS mismatches, and temporal features to diagnose exactly why a transaction failed.
*   **False Decline Engine:** Identifies when strict fraud filters have blocked a genuine customer, routing them for immediate retry.

### Pillar C: Dual-Engine BNPL Recovery (Recover)
A DPDP Act & RBI compliant recovery system.
*   **Engine 1 (Edge Checkout):** Ultra-low latency Go proxy providing real-time BNPL checkout fallback offers under a strict 50ms circuit breaker.
*   **Engine 2 (Asynchronous Recovery):** Background Go worker orchestrating multi-channel recovery, strictly obeying the DPDP Act (Right to Erasure) and RBI Dunning guidelines (8 AM - 7 PM IST, max 3 contacts/day).

---

## 📚 Documentation
Dive into the technical depth of our architecture in the `docs/` folder:
*   **[System Architecture (HLD)](./docs/architecture/hld.md)**
*   **[Chargeback Service (LLD)](./docs/services/chargeback-service/lld.md)**
*   **[BNPL Edge Service (Circuit Breaker ADR)](./docs/services/bnpl-edge-service/decisions/001-fail-silent-sla.md)**

## 🚀 Getting Started
```bash
docker-compose up -d --build
```
*Note: A Groq API key is recommended but optional. The system will gracefully fall back to heuristics without it.*
