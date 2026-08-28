# Frontend — Low-Level Design (LLD)
# Feature 1 — Classifier Inspector

**Framework:** Next.js 14 (App Router, TypeScript)  
**Port:** 3000  
**Role:** Read-only inspector for payment failure classifications

---

## 1. Screen Inventory (TDD §6.1)

| Screen | Route | Description |
|--------|-------|-------------|
| Transaction List | `/` | Paginated table of recent failures — cause, confidence, layer, action |
| Transaction Detail | `/classifications/[id]` | Full payload, raw reasoning, layer badge |

---

## 2. Component Tree

```
app/
├── layout.tsx                     # Root layout: font, global nav header
├── page.tsx                       # Transaction List page
└── classifications/
    └── [id]/
        └── page.tsx               # Transaction Detail page

components/
├── TransactionTable.tsx           # Sortable/filterable table
├── ClassificationRow.tsx          # Single row in the table
├── LayerBadge.tsx                 # "Layer 1 / Rule" vs "Layer 2 / Model" badge
├── CauseBadge.tsx                 # Colour-coded cause pill
├── ConfidenceBar.tsx              # Visual 0–100% confidence bar
├── FilterBar.tsx                  # Cause + layer filter controls
├── DetailPanel.tsx                # Full classification detail view
└── ReasoningBlock.tsx             # Renders reasoning as styled prose

app/api/
└── classifications/
    ├── route.ts                   # BFF: GET → audit service list
    └── [id]/
        └── route.ts               # BFF: GET → audit service detail
```

---

## 3. Data Flow

```
User loads /
  → page.tsx calls /api/classifications (BFF)
    → BFF proxies → http://audit-service:3003/api/v1/classifications
      → Returns ClassificationView[]
  → TransactionTable renders rows
  → User clicks row → navigate to /classifications/<id>

User loads /classifications/<id>
  → page.tsx calls /api/classifications/<id> (BFF)
    → BFF proxies → http://audit-service:3003/api/v1/classifications/<id>
      → Returns single ClassificationView
  → DetailPanel + LayerBadge + ReasoningBlock render
```

---

## 4. Key Component Specs

### `LayerBadge`
```tsx
type Props = { layer: 1 | 2; modelVersion: string | null }

// Layer 1 → "⚡ Rule · Deterministic" (green badge, no model name)
// Layer 2 → "🤖 Model · stub-v1.0-heuristic" (blue badge, shows model_version)
```

### `CauseBadge`
```tsx
type Props = { cause: string }

// Colour map:
// notification_compliance_block → amber
// soft_decline → blue
// hard_decline → red
// gateway_fault → orange
// fraud_filter_block → purple
```

### `ConfidenceBar`
```tsx
type Props = { confidence: number }  // 0.0 – 1.0

// Green bar when > 0.5, yellow when 0.25–0.5, red when < 0.25
// Special: confidence === 0 → "Manual Review Required" warning
```

### `FilterBar` (list page)
```tsx
// Cause dropdown: All | soft_decline | hard_decline | gateway_fault | fraud_filter_block | notification_compliance_block
// Layer radio: All | Layer 1 | Layer 2
// State lifted to page.tsx, triggers re-fetch via URL query params
```

---

## 5. BFF API Routes

| Route | Method | Proxies To |
|-------|--------|-----------|
| `/api/classifications` | GET | `audit-service:3003/api/v1/classifications` |
| `/api/classifications/[id]` | GET | `audit-service:3003/api/v1/classifications/:id` |

Query params `cause`, `layer`, `limit`, `offset` are passed through as-is.

---

## 6. Environment Variables

| Variable | Description |
|----------|-------------|
| `AUDIT_SERVICE_URL` | Internal URL of audit service (`http://audit-service:3003`) |

---

## 7. Design Principles

- **No write operations** — frontend is fully read-only
- **No external state management** (Redux/Zustand) — audit service returns everything needed per page
- **Server components by default** — data fetched on server for SEO and performance
- **Client components only where needed** — FilterBar (interactive) is client; table rows are server
