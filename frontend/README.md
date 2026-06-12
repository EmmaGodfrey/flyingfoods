# ERP Web - Inventory, POS, Procurement

Frontend inventory, POS, procurement, and global search interface.

## Included

- Login flow against backend `/auth/login` and token refresh support.
- Products list with search and pagination.
- Add/edit product modal with inline validation.
- Stock movement history with movement type and date-range filters.
- Receive stock form that creates movements and refreshes stock totals.
- POS product grid and basket checkout flow.
- Receipt panel with print action for latest sale.
- Daily sales summary panel with polling.
- Sale reversal actions from receipt panel (void and refund).
- POS pricing inputs for tax, discount, and split tender checkout.
- Procurement tab for purchase order create/list/submit/approve flow.
- Goods received note (GRN) form to receive approved PO quantities.
- Procurement orders and spend report tables.
- Suppliers management panel with create/edit/delete and branch-scoped search.
- Global branch-scoped search in header for products, suppliers, and invoices with fuzzy/highlight backend support.

## Run

1. Install dependencies:

   npm install

2. Start dev server:

   npm run dev

3. Optional API base URL override:

   Set `VITE_API_BASE_URL` (default: `http://localhost:8000`).

4. Build:

   npm run build

## Notes

- UI follows `erp/docs/05_UI_DESIGN_SYSTEM.md` and icon scale rules in `erp/docs/ui/ICON_SCALE.md`.
- This app expects backend inventory, sales, procurement, and search endpoints to be available, including `/inventory/movements`, `/sales`, `/sales/{id}/receipt`, `/sales/summary/daily`, `/procurement/*`, and `/search`.
- For fuzzy/highlight search, Elasticsearch should be running at backend `elasticsearch_url` (default: `http://localhost:9200`).

## What Is Not There Yet

- Payment gateway UI/integration is not available.
- Detail-page navigation from search results is displayed but not fully routed in this single-page shell.
