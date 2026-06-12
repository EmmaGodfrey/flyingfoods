# Flying Foods ERP — Team Guide

**Audience**: developers joining the project. Read this first, then the spec artifacts it links to.
**Last updated**: 2026-06-12

## What we are building

A restaurant and inventory management system for Flying Foods (dine-in restaurant + in-flight catering unit). The existing POS keeps handling payments and receipts. Our system takes over everything that happens after the receipt prints:

- The POS reports a sale. Within 5 seconds the order shows on the Kitchen Display and the recipe's ingredients leave stock automatically.
- The Chef works the order (Start, Ready); the Waiter delivers and marks it Served. Each step is timestamped.
- Stock lives at three locations: Restaurant Stores (central), Restaurant Kitchen, and the Unit (in-flight catering). Issues and transfers move stock between them.
- Procurement runs Budget → Manager approval → Purchase Order (PDF emailed to the supplier) → Goods Received Note → 3-way match against the invoice.
- Wastage, breakage, and stock-take variances get logged with reason codes. Big amounts need Manager approval.
- Every stock movement mirrors to Pastel, the accounting system, so finance stops re-typing.

The business goal is anti-leakage: every gram of stock traceable from purchase to plate, and a report that shows the gap between what recipes say we used and what stock-takes say we actually used.

The full requirements live in `docs/Restaurant_Inventory_BRD.pdf` (BRD v2.0). Requirement IDs from that document (FR-KD-01, FR-PR-05, etc.) appear throughout our spec for traceability.

## Why a rebuild

The repo contained a FastAPI + SQLAlchemy ERP (~4.7k lines) covering generic inventory and procurement. A gap analysis against the BRD scored it at 15-20% coverage: no kitchen workflow, no recipes, no multi-location stock, no budgets, no Pastel sync. Since 80% had to be built new and the target stack is Django, we decided (2026-06-12) to build fresh in Django + DRF and keep the old code in `legacy/` as a read-only reference. The React/Vite frontend survives and gets extended.

## Stack

| Layer | Choice |
|---|---|
| Backend | Django 5, Django REST Framework, Python 3.12 |
| Auth | djangorestframework-simplejwt (15-min access in memory, 7-day rotating refresh in httpOnly cookie) |
| Database | PostgreSQL 16, UUID primary keys everywhere |
| Async work | Celery + Redis (Pastel sync, batch jobs, retries) |
| Real-time | Django Channels + Redis (kitchen and waiter screens) |
| PDF / Excel | weasyprint / openpyxl |
| Frontend | React 18 + Vite, TypeScript, React Query (server state), Zustand (client state) |
| Dev infra | docker-compose: postgres, redis, mailpit (catch outgoing PO emails) |
| Tests | pytest-django + factory_boy (backend), Vitest + RTL + MSW (frontend) |

## Repository map

```
backend/    Django project. config/ holds settings; apps/ holds one app per domain.
frontend/   React SPA. One folder per feature under src/features/.
legacy/     The old FastAPI ERP. Reference only. Never import from it. CI ignores it.
specs/      Spec-kit artifacts: the contract for what we build (see below).
docs/       This guide, the BRD, decision records.
```

Backend apps and what owns what:

| App | Owns |
|---|---|
| `core` | BaseModel (UUID + timestamps), Approval engine, outbox, audit log, reason codes, thresholds, idempotency, the `{success, data\|error}` response envelope |
| `users` | Custom User (email login), the 8 roles, permission classes |
| `masterdata` | Products (with unit-of-measure conversions), categories, suppliers, locations |
| `menu` | Menu items, versioned recipes, Draft → Review → Published workflow |
| `pos_ingest` | Raw sale events from the POS, dedupe, replay |
| `kitchen` | Orders, status lifecycle, extra-usage logging, WebSocket broadcast |
| `inventory` | The stock ledger, issue notes, transfers, stock-takes |
| `procurement` | Budgets, POs (PDF + email), GRNs, 3-way invoice match |
| `wastage` | Breakage, spoilage, extra usage entries |
| `pastel` | Accounting sync adapter, retry queue, reconciliation |
| `notifications` | In-app notifications |
| `reports` | All reports plus PDF/Excel export |

Inside every app: `models.py`, `serializers.py`, `views.py` (thin), `services.py` (all writes), `selectors.py` (all reads), `urls.py`, `tests/`.

## The four ideas that hold the system together

Understand these and the rest of the codebase reads itself.

**1. The stock ledger is append-only.** `inventory.StockMovement` rows never change. On-hand quantity is the sum of movements, cached in `StockBalance`. To undo a movement you post a contra-movement. This is what makes leakage traceable: any balance, at any time, decomposes into documents and users.

**2. One choke point writes stock.** `inventory.services.post_movements()` is the only code allowed to create ledger rows. Every caller (sale deduction, GRN, issue, transfer, wastage, stock-take) passes a parent document. The choke point enforces the negative-stock guard, writes the audit entry, and creates the Pastel outbox record in the same database transaction. If you find yourself writing stock anywhere else, stop.

**3. Approvals are one engine, not four.** Budgets, large wastage, large transfers, and negative-stock overrides all create a `core.Approval` row pointing at their document. Threshold values get snapshotted at submission, so changing a threshold never affects items already in the queue. Managers work one queue.

**4. Integrations go through the outbox.** A stock movement and its outbound Pastel record commit together or not at all. Celery drains the outbox with exponential backoff and logs every attempt. A crashed worker or a Pastel outage delays sync; it never loses a movement. The same idempotency discipline covers POS ingestion (unique sale ID), GRN posting, and PO emails.

One more rule with teeth: recipes are versioned, and an order permanently references the recipe version that was active when it was placed. Historical reports stay correct after every menu change. Published versions are immutable; edits create the next version.

## Where the truth lives

The spec artifacts under `specs/001-restaurant-inventory-system/` are the working contract. When code and spec disagree, fix one of them in the same PR.

| File | Read it when |
|---|---|
| `spec.md` | You want to know what a feature must do (user stories, acceptance scenarios, BRD cross-references) |
| `plan.md` | You want the architecture decisions and phase order |
| `data-model.md` | You are touching models (fields, state machines, invariants, indexes) |
| `contracts/api-contracts.md` | You are adding or consuming an endpoint (paths, roles, error codes) |
| `quickstart.md` | You want to run the system and prove a story works end to end |
| `tasks.md` | You want to know what to pick up next (83 tasks, dependency-ordered) |
| `research.md` | You want to know why we chose X over Y |

## Working agreements

- **Spec-driven**: features flow spec → plan → tasks → implement. Use the `/speckit-*` commands rather than editing artifacts ad hoc.
- **Git**: `main` stays deployable; work happens on `dev` and short-lived `feature/xxx` branches. Conventional commits (`feat:`, `fix:`, `test:` ...), one change per commit.
- **Code style**: the project style guide (CLAUDE.md) is binding. Highlights: full type hints and docstrings on every Python function, services not fat views, `select_related`/`only()` on hot queries, pagination on every list endpoint, no `any` in TypeScript, React Query for all server data.
- **Tests**: every API endpoint test covers happy path, 401, 403, and 400. Critical logic (ledger, approvals, dedupe, outbox) gets service-level tests. Frontend tests target behavior through RTL + MSW, never component internals.
- **Responses**: every endpoint returns `{"success": true, "data": ...}` or `{"success": false, "error": {"code", "message"}}`. Clients can rely on this without exception.

## Running it

Short version (full version with validation scenarios: `specs/001-restaurant-inventory-system/quickstart.md`):

```bash
docker compose up -d postgres redis mailpit
cd backend && pip install -e .[dev] && python manage.py migrate && python manage.py seed_demo && python manage.py runserver
cd frontend && npm ci && npm run dev
```

`seed_demo` creates one login per role (`chef@ff.local`, `manager@ff.local`, ...). Mailpit at http://localhost:8025 shows outgoing PO emails.

## Delivery phases

1. **Foundation** (auth, roles, master data, response envelope, approval engine, outbox shells)
2. **Sale → Kitchen → Service** — the MVP; replaces paper tickets
3. **Procurement** (budgets through 3-way match)
4. **Issuing, transfers, wastage, stock-take**
5. **Full recipe versioning workflow**
6. **Pastel sync**
7. **Reports, exports, dashboards, polish**

After phase 2 ships, phases 3, 5, and 6 have no dependencies on each other, so three people can run in parallel. `tasks.md` marks the parallel-safe tasks with `[P]`.

## Glossary (the short list)

- **GRN** — Goods Received Note; what we record when a supplier delivery arrives, line by line, against a PO.
- **3-way match** — PO vs GRN vs supplier invoice; mismatches block payment approval.
- **Issue Note** — internal stock movement from Stores to Kitchen (daily) or to the Unit (Tuesdays and Thursdays).
- **Outbox** — table of pending outbound Pastel records, written transactionally with the stock movement.
- **Leakage report** — theoretical consumption (recipes × sales) vs actual consumption (stock-take adjusted); the gap is what the business wants to see shrink.
- **Pastel** — the company's accounting package. We push stock movements to it; we never replace it.

The BRD's own glossary (page 33) covers the rest.
