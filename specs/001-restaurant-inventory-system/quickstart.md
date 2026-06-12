# Quickstart & Validation Guide

How to run the system locally and prove each spec user story end-to-end. Contracts: [contracts/api-contracts.md](contracts/api-contracts.md) · Data model: [data-model.md](data-model.md).

## Prerequisites

- Docker Desktop (postgres, redis, mailpit)
- Python 3.12, Node 20

## Setup

```bash
# infrastructure
docker compose up -d postgres redis mailpit

# backend
cd backend
cp .env.example .env
pip install -e .[dev]
python manage.py migrate
python manage.py seed_demo          # locations, roles, demo users, products, recipes
python manage.py runserver          # http://localhost:8000

# celery (separate terminals)
celery -A config worker -l info
celery -A config beat -l info

# frontend
cd frontend
cp .env.example .env.local
npm ci && npm run dev               # http://localhost:5173
```

Demo logins (seeded, one per role): `chef@ff.local`, `waiter@ff.local`, `storekeeper@ff.local`, `receiving@ff.local`, `unitissuer@ff.local`, `restissuer@ff.local`, `manager@ff.local`, `admin@ff.local` — password from `seed_demo` output.

## Validation scenarios

### V1 — Sale → Kitchen → Service (US1, SC-001/002/003)

```bash
curl -X POST localhost:8000/api/pos/sale-events/ -H "Authorization: Bearer $POS_TOKEN" \
  -d '{"pos_sale_id":"POS-1001","sold_at":"...","cashier":"till-1","lines":[{"pos_code":"BURGER","qty":2}],"totals":{"gross":"24.00"}}'
```

Expect: order on Kitchen Display (chef login) within 5 s; `GET /api/stock/movements/?document_type=order` shows SALE_DEDUCTION rows; re-POST same `pos_sale_id` → 200, no second order. Walk Start → Ready (chef) → Served (waiter); `GET /api/reports/service-time/` shows the durations.

### V2 — Procurement cycle (US2, SC-004)

Manager approves a submitted budget → Receiving Officer creates PO → `POST /purchase-orders/{id}/send/` → open mailpit (http://localhost:8025) and verify PO PDF email → post partial GRN then final GRN → enter invoice with a price discrepancy → verify `INVOICE` match flags it. Check stock increased and `GET /api/reports/budget-vs-actual/` reflects actuals.

### V3 — Issuing, transfers, negative stock (US3)

Post a daily issue Stores→Kitchen; attempt a Unit issue on a non-Tue/Thu without reason (expect 400 `OFF_SCHEDULE_REASON_REQUIRED`), retry with reason (posts). Create a Kitchen↔Unit transfer above threshold → appears in Manager `/approvals/` queue → approve → posts. Attempt an issue exceeding on-hand → 409 `INSUFFICIENT_STOCK`; request override → Manager approves → posts with OVERRIDE_ADJ audit.

### V4 — Wastage & stock-take (US4)

Log spoilage below threshold (posts immediately) and above (pending approval). Open a stock-take, submit counts with a known variance, post → variance appears in `/reports/wastage/` and `/reports/leakage/`.

### V5 — Recipe versioning (US5, SC-010)

Publish recipe v2 with changed quantities effective today; ingest a new sale; verify old orders still report v1 quantities (`/reports/recipe-costing/` and order detail show version snapshots). Attempt DELETE on the menu item → 409 `MENU_ITEM_HAS_HISTORY`.

### V6 — Pastel outbox resilience (US6, SC-008)

Point Pastel adapter at the dev stub with failure mode on (`PASTEL_STUB_FAIL=1`); post movements; watch `/pastel/sync-log/` accumulate FAILED attempts with backoff; clear failure mode; verify all PENDING drain with zero loss/duplicates; run reconciliation → no divergence.

### V7 — Reports & exports (US7, SC-007)

Run every report endpoint with `?format=pdf` and `?format=xlsx`; verify totals against the seeded dataset sheet in `backend/apps/reports/tests/fixtures/expected_totals.md`.

### V8 — Role matrix (US8, SC-009)

`pytest backend/apps -k permission` runs the role-by-role matrix: each role exercises every permitted endpoint (2xx) and a sample of forbidden ones (403).

## Test commands

```bash
cd backend && pytest                 # full backend suite
cd frontend && npm test              # vitest
cd frontend && npm run build         # bundle check
```

## CI

`.github/workflows/ci.yml` runs backend pytest (postgres+redis services) and frontend test+build on every push to `dev`/`main`. `legacy/` is excluded from both jobs.
