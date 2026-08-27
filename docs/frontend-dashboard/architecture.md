# Frontend Classification Inspector & Simulator

> **Scope:** `frontend/`

The frontend application serves as a real-time observability dashboard and testing harness for the Razorpay Root-Cause Classification pipeline. It is built using **Next.js 15 (App Router)** and **React 19**.

## 1. Core Architecture

The frontend adheres to a strict Server-Side Rendering (SSR) approach with minimal Client Components to ensure rapid load times and robust SEO out-of-the-box. 

### Data Fetching
*   All dashboard data is fetched natively on the server (`app/page.tsx`) by querying the **Audit Service API**.
*   It utilizes Next.js's native `fetch` caching mechanism with a short `revalidate` interval (5 seconds), providing near real-time updates while protecting the backend from polling storms.

### Component Structure
*   **Server Components:** `page.tsx`, `classifications/[id]/page.tsx`
*   **Client Components:** 
    *   `FilterBar.tsx`: Manages URL-based state (`?cause=soft_decline&layer=3`) pushing routes natively so that filter states are inherently linkable and shareable.
    *   `SimulatorPanel.tsx`: Interactive webhook injection form.

## 2. Real-Time Webhook Simulator

To facilitate end-to-end testing of the Mixture-of-Experts (MoE) classification layers without needing external API tools (like Postman), a built-in **Simulator Panel** was developed.

### 2.1 The Problem
The browser cannot safely `POST` directly to the internal Docker network (`ingestion-service:3001`) due to CORS and network isolation policies. 

### 2.2 The Solution: Server Actions
The simulator leverages **Next.js Server Actions** (`app/actions.ts`). 
1. The user clicks a simulator preset (e.g. "Simulate Fraud Block") in the Client Component.
2. The payload is passed to the `simulateWebhook()` Server Action.
3. The Node.js server securely `POST`s the webhook to the internal Ingestion Service.
4. The backend processes the transaction through the entire Multi-LLM pipeline.
5. The Server Action intentionally pauses for `1500ms` and triggers `revalidatePath('/')`.
6. The frontend's cache is dropped, the UI automatically refreshes, and the newly classified transaction appears instantly at the top of the dashboard.

## 3. The 4-Layer Unified UI

The UI categorizes the complex backend decision matrix into a clean, 4-tier visual hierarchy using distinct badge coloring and lucide-react iconography:

1.  **Layer 1 (Deterministic Rule):** Green `<Zap />` 
2.  **Layer 2 (Fine-Tuned Model):** Blue `<Bot />`
3.  **Layer 3 (General LLM):** Pink `<BrainCircuit />`
4.  **Layer 4 (Ensemble AI):** Purple `<Network />`

When viewing a detailed Layer 4 classification, the UI dynamically inserts an "Ensemble Resolved" badge, highlighting that the rationale text is a merged output of both high-speed ML and deterministic LLM reasoning.
