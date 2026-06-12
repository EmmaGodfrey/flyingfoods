# Implementation Plan: Flying Foods Restaurant & Inventory Management System

**Branch**: `001-restaurant-inventory-system` | **Date**: 2026-06-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-restaurant-inventory-system/spec.md`

## Summary

Rebuild the existing FastAPI ERP as a fresh Django + DRF backend satisfying the Flying Foods BRD v2.0: POS sale ingestion → Kitchen Display with recipe-driven stock deduction → Waiter service; three-location inventory on an append-only stock ledger; Budget → PO (PDF + email) → GRN → 3-way match procurement; wastage/stock-take with threshold approvals; versioned menus/recipes; Pastel sync via transactional outbox; full reporting with PDF/Excel export. The existing React/Vite frontend is kept and extended. Old FastAPI code becomes read-only reference in `legacy/`.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5 (frontend)

**Primary Dependencies**: Django 5.x, djangorestframework, djangorestframework-simplejwt (+ token_blacklist), django-filter, django-redis, celery[redis], channels + channels-redis, weasyprint (PO/report PDFs), openpyxl (Excel export), python-decouple, dj-database-url, pytest-django, factory_boy. Frontend: React 18 + Vite, @tanstack/react-query, zustand, react-router-dom, sonner.

**Storage**: PostgreSQL 16 (primary), Redis 7 (cache, Celery broker, Channels layer, JWT blocklist)

**Testing**: pytest-django + factory_boy + DRF APIClient (backend); Vitest + React Testing Library + MSW (frontend)

**Target Platform**: Linux server (Docker), clients on LAN — desktop browsers + tablets (kitchen/waiter/stores)

**Project Type**: Web application — Django REST backend + React SPA frontend, monorepo

**Performance Goals**: POS sale → kitchen ticket visible < 5 s end-to-end (p95); list endpoints paginated, < 100 ms typical query budget; reports paginate server-side

**Constraints**: Kitchen/waiter/stores screens usable during short internet outages (LAN-local server + client-side action queue); two-tap critical actions on tablets; 99% availability during operating hours; idempotent ingestion/posting/sync/email; append-only audit with before/after values

**Scale/Scope**: Restaurant-scale — hundreds of orders/day, low-thousands of products, < 50 concurrent users, 3 stock locations, 8 roles, 12 Django apps, ~10 reports

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is the unmodified template (no project principles ratified yet). No gates to evaluate. Governing conventions instead come from the project style guide (`c:\Users\user\Downloads\CLAUDE.md`): explicit + fully typed code, services-not-fat-views, UUID PKs, consistent `{success, data|error}` response shape, pagination everywhere, pytest-django/factory_boy testing, conventional commits. The plan below conforms to all of these. **PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/001-restaurant-inventory-system/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API surface)
│   └── api-contracts.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
erp_v2/
├── backend/                          # NEW Django project
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py               # shared settings, decouple-driven
│   │   │   ├── dev.py
│   │   │   └── prod.py
│   │   ├── urls.py
│   │   ├── asgi.py                   # Channels entrypoint
│   │   ├── wsgi.py
│   │   └── celery.py
│   ├── apps/
│   │   ├── core/                     # BaseModel (UUID pk + timestamps), Approval engine,
│   │   │   │                         # OutboxRecord, ReasonCode, ThresholdConfig,
│   │   │   │                         # AuditLog + audit service, IdempotencyKey,
│   │   │   │                         # response envelope renderer + exception handler
│   │   ├── users/                    # custom User (email auth), Role enum, permission classes
│   │   ├── masterdata/               # Product (+UoM conversions), Category, Supplier, Location
│   │   ├── menu/                     # MenuItem, RecipeVersion, RecipeLine, publish workflow
│   │   ├── pos_ingest/               # SaleEvent raw store, dedupe, replay admin, pull poller
│   │   ├── kitchen/                  # Order, OrderItem, OrderStatusEvent, extra usage,
│   │   │   │                         # Channels consumers (kitchen + waiter groups)
│   │   ├── inventory/                # StockMovement ledger, StockBalance cache,
│   │   │   │                         # post_movements() choke point, IssueNote, Transfer, StockTake
│   │   ├── procurement/              # PurchaseBudget, PurchaseOrder, GRN, InvoiceMatch,
│   │   │   │                         # PO PDF builder, supplier email sender
│   │   ├── wastage/                  # WastageEntry (extra-usage/breakage/spoilage)
│   │   ├── pastel/                   # sync adapter, PastelSyncLog, Celery retry/batch tasks,
│   │   │   │                         # reconciliation
│   │   ├── notifications/            # in-app Notification model + fan-out service
│   │   └── reports/                  # selectors per report, PDF/Excel exporters
│   │   # every app: models.py, serializers.py, views.py, services.py (writes),
│   │   # selectors.py (reads), urls.py, admin.py, tests/{test_views,test_services,factories}.py
│   ├── manage.py
│   ├── pyproject.toml
│   ├── .env.example
│   └── Dockerfile
├── frontend/                         # MOVED from erp/erp-web, then extended
│   ├── src/
│   │   ├── features/                 # auth, kitchen, waiter, inventory, procurement,
│   │   │   │                         # wastage, menu, reports, admin
│   │   │   └── <feature>/{components,hooks,api.ts,types.ts,index.ts}
│   │   ├── components/               # shared primitives
│   │   ├── lib/                      # apiClient (axios + JWT interceptors), queryClient, ws client
│   │   ├── store/                    # zustand stores (auth, ui)
│   │   └── ...existing pages/router until migrated into features/
│   ├── .env.example
│   └── Dockerfile
├── legacy/                           # OLD erp/ FastAPI code — reference only, excluded from CI
├── specs/                            # spec-kit artifacts
├── docs/                             # team documentation, ADRs, BRD
├── docker-compose.yml                # postgres, redis, mailpit, backend, frontend
└── .github/workflows/ci.yml         # backend pytest + frontend build/test
```

**Structure Decision**: Web-application monorepo (`backend/` + `frontend/`), Django apps mapped one-to-one to BRD modules. The old tree at `erp/` is relocated to `legacy/` in the restructure task; nothing imports from it.

## Architecture Decisions (binding for tasks)

1. **Append-only stock ledger** — `inventory.StockMovement` rows are immutable; every row carries `(product, location, qty_delta, document_type, document_id, posted_by, posted_at)`. `StockBalance` is a per-(product, location) cache updated in the same transaction, guarded by `select_for_update()`. Reversals are new contra-movements, never edits.
2. **Single posting choke point** — only `inventory.services.post_movements(document, lines)` writes ledger rows. It enforces negative-stock guard (with Manager-override path), writes audit entries, creates outbox records atomically, and is idempotent per `(document_type, document_id)`.
3. **Transactional outbox for Pastel** — `core.OutboxRecord` written in the same DB transaction as the movement. Celery beat drains per configured mode (real-time = immediate task, daily batch = end-of-day task, event-only = filtered). Exponential backoff via Celery retry policy; every attempt logged in `pastel.PastelSyncLog`.
4. **Generic Approval engine** — `core.Approval` with GenericForeignKey to subject document + `ThresholdConfig` lookup at submission time (threshold snapshot stored on the approval). Used by budgets, wastage, transfers, negative-stock overrides. State machine: PENDING → APPROVED | REJECTED | INVESTIGATION.
5. **Recipe version snapshot on order lines** — `OrderItem.recipe_version` FK set at ingestion from the version effective on the order date; reports always join through the snapshot, never "current".
6. **Real-time via Channels** — groups `kitchen` and `waiter`; order create/status events broadcast JSON deltas. REST remains source of truth; sockets are notification-only (clients refetch via React Query invalidation).
7. **Idempotency** — POS ingestion keyed on `pos_sale_id` (unique constraint); GRN/issue/transfer/wastage posting keyed on client-supplied `Idempotency-Key` header persisted in `core.IdempotencyKey`; PO email send guarded by send-log existence; Pastel sync keyed on outbox record id.
8. **Response envelope** — DRF custom renderer + exception handler produce `{"success": true, "data": ...}` / `{"success": false, "error": {"code", "message"}}` globally; HTTP codes per style guide.
9. **JWT** — simplejwt, 15-min access / 7-day rotating refresh with blacklist-after-rotation; refresh delivered as httpOnly cookie by login view; access token held in Zustand memory only.
10. **Offline tolerance (frontend)** — kitchen/waiter status mutations queue in a Zustand-persisted (localStorage) action queue with idempotency keys; flushed on reconnect; server LAN-local so POS→kitchen path does not cross the internet.
11. **PDF/Excel** — weasyprint renders HTML templates (PO document, report prints); openpyxl streams Excel; both behind `reports.services.export()` with one code path per report.
12. **Audit** — `core.AuditLog` append-only, written by the posting choke point and by a model-save signal allowlist for master data; captures user, action, before/after JSON.

## Phased Delivery (maps to spec user-story priorities)

| Phase | Contents | Spec stories |
|---|---|---|
| 0 Restructure | monorepo move (`legacy/`, `frontend/`), docker-compose, CI skeleton | — |
| 1 Foundation | config, core app (envelope, BaseModel, audit, thresholds, reason codes, approvals, outbox shells), users + JWT + permissions, masterdata + UoM, locations, seed command | US8 |
| 2 Kitchen flow | menu/recipes (minimal publish), pos_ingest, inventory ledger + post_movements, kitchen orders + Channels, waiter view | US1 |
| 3 Procurement | budgets + approvals, PO + PDF + email (mailpit), GRN + partials, invoice 3-way match | US2 |
| 4 Issuing & wastage | issue notes, transfers, stock-take, wastage entries, negative-stock override | US3, US4 |
| 5 Menu versioning full | Draft→Review→Published, effective dating, scheduling | US5 |
| 6 Pastel | adapter, sync modes, retry, recon report | US6 |
| 7 Reports & polish | all reports + exports, notifications surfacing, integration health dashboard, frontend features complete | US7 |

## Complexity Tracking

No constitution violations to justify (constitution not yet ratified). Two deliberate complexity adds, both pre-approved by the user: generic Approval engine (vs four bespoke flows — less total code) and transactional outbox (vs fire-and-forget sync — required by SC-008 zero-loss guarantee).
