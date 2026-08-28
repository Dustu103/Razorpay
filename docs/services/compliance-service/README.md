# Compliance Service — Documentation Index

> All technical documentation for the `compliance-service` (Feature 2) lives here.

## Documents

| File | Description |
|------|-------------|
| [architecture.md](./architecture.md) | JSON-based LLM UI scanning, Prompt logic, and RBI Rule mapping |

## Service Overview

The `compliance-service` is a standalone Python FastAPI microservice that analyzes JSON representations of a business's mandate/subscription UX flow. It uses an LLM (Groq/Gemini) acting as a compliance auditor to detect violations of the February 2026 RBI Guidelines regarding Dark Patterns.

For system-wide context, see the [High-Level Design](../architecture/hld.md).
