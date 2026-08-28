# ADR-007: Use Declarative JSON Schema for Compliance Scanning Input

**Status:** Accepted  
**Date:** 2026-08-27  
**Deciders:** Engineering Team  

---

## Context

The business case called for an LLM that "reads a business's mandate/subscription flow" and identifies RBI dark pattern violations. The core unresolved question was: **how does the system get the UI data to analyze?**

Three approaches were evaluated:
1. **Autonomous web crawler** — Puppeteer/Playwright headless browser to automatically navigate and scrape the merchant's live UX flow.
2. **Screenshot-based vision analysis** — Merchant uploads screenshots; Gemini Vision API extracts text and layout.
3. **Declarative JSON schema** — Merchant provides a JSON representation of their screens (button labels, checkbox states, etc.) via API.

---

## Decision

**Use a Declarative JSON Schema as the input format for compliance scanning.**

---

## Rationale

| Criterion | Autonomous Crawler | Screenshot Vision | JSON Schema |
|-----------|--------------------|------------------|-------------|
| Implementation complexity | Very High (CAPTCHA, SPA, auth) | Medium (vision API + parsing) | **Low** |
| Reliability | Low (breaks on UI changes) | Medium (layout-sensitive) | **High** |
| API response time | 10–120s | 5–15s | **2–5s** |
| Works on mobile/native apps | ❌ | ✅ (if screenshots given) | ✅ |
| Supports A/B test variants | ❌ | ❌ | ✅ |
| Auditable / versioned input | ❌ | Partial | ✅ |
| Can be CI/CD integrated | ❌ | ❌ | ✅ |

**Key factors:**
- An autonomous crawler is a startup product in itself. CAPTCHA bypass, SPA navigation, and dynamic content rendering would consume more engineering effort than the entire rest of the feature.
- The JSON schema approach is actually **superior in auditability** — a merchant can version-control their UX flow JSON, run it on every deployment, and produce a compliance paper trail. A web scraper produces no reproducible audit artifact.
- The JSON schema can represent **any platform** (web, iOS, Android) — you simply describe the screen, not the technology. A web scraper is inherently web-only.

---

## Consequences

- **Positive:** ~2–5s API response time. Simple, testable, reliable.
- **Positive:** Merchants can integrate `POST /api/v1/scan-compliance` into their CI/CD pipeline as a compliance gate.
- **Positive:** The LLM reasoning quality is higher on structured JSON than on OCR-extracted screenshot text.
- **Negative:** Merchant must provide the JSON schema manually or via their own tooling. This is an integration cost.
- **Negative:** Cannot detect purely visual dark patterns (e.g. low-contrast "decline" button, small font terms). These require the vision approach.

---

## Revisit Trigger

When screenshot-based vision analysis is added as a second input mode (planned), this ADR will be superseded by a new one covering the hybrid JSON + Vision approach.
