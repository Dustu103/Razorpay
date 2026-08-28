# ADR-006: Use Next.js SSR App Router for the Dashboard

**Status:** Accepted  
**Date:** 2026-08-15  
**Deciders:** Engineering Team  

---

## Context

The dashboard needs to display real-time classified transactions from the Audit Service API. It also needs to provide engineers a way to inject test webhooks into the backend for E2E validation. Options considered:

1. Pure React SPA (Vite/CRA) + client-side fetch
2. Next.js App Router (SSR + Server Components + Server Actions)
3. Remix
4. A standalone tool like Retool / internal admin UI

---

## Decision

**Use Next.js 15 (App Router) with React Server Components for SSR and Server Actions for backend mutations.**

---

## Rationale

| Criterion | React SPA | Next.js App Router | Remix | Retool |
|-----------|:---------:|:------------------:|:-----:|:------:|
| SSR (no loading flash) | ❌ | ✅ | ✅ | ✅ |
| Server Actions (no API route needed) | ❌ | ✅ | ✅ | ❌ |
| CORS bypass for Docker-internal services | ❌ | ✅ | ✅ | ❌ |
| TypeScript native | ✅ | ✅ | ✅ | ❌ |
| Custom UI flexibility | Full | Full | Full | Limited |
| Zero separate backend for mutations | ❌ | ✅ | ✅ | N/A |

**Key factors:**
- **Server Components** allow direct data fetching from the Audit Service on the server, eliminating loading states and CORS issues that a pure SPA would require an additional BFF (Backend-for-Frontend) to solve.
- **Server Actions** are the critical feature: the `simulateWebhook()` action runs server-side, can reach `http://ingestion-service:3001` inside the Docker network, and calls `revalidatePath('/')` to trigger a cache bust — all without writing a separate API route.
- **Retool** was ruled out because it provides limited control over the UI and has no concept of strongly-typed TypeScript models, making it unsuitable for a production-quality engineering tool.

---

## Consequences

- **Positive:** The Simulator Panel in the browser can reach Docker-internal services with zero CORS configuration.
- **Positive:** Dashboard data is always fresh at page load (SSR) without a loading spinner.
- **Positive:** `revalidatePath('/')` means the table auto-refreshes after a test injection without a full page reload.
- **Negative:** Next.js App Router adds complexity vs a simple SPA — developers must understand the Server/Client Component boundary.
- **Negative:** The `INGESTION_SERVICE_URL` and `AUDIT_SERVICE_URL` env vars must be set correctly in `docker-compose.yml` for Server Actions to reach the correct internal Docker hostname.
