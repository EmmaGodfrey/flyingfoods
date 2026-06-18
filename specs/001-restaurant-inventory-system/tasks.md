# Tasks: Flying Foods Restaurant & Inventory Management System

**Input**: Design documents from `/specs/001-restaurant-inventory-system/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api-contracts.md, research.md, quickstart.md

**Tests**: Included for critical paths per plan test strategy (ledger, approvals, ingestion dedupe, outbox, permissions) — style guide mandates happy/401/403/400 coverage per API test.

**Organization**: Phases 1-2 = setup + foundation (no story label). Phases 3-10 = user stories US1-US8 in priority order. Phase 11 = polish.

## Phase 1: Setup (monorepo restructure + scaffolding)

- [x] T001 Restructure monorepo into `backend/`, `frontend/`, `docs/`, and
  `specs/`; remove the superseded implementation and committed environments.
- [ ] T002 Init git repo on `main`, create `dev` branch, initial commit of restructured tree
- [ ] T003 Scaffold Django project in `backend/`: `config/settings/{base,dev,prod}.py` (decouple + dj-database-url), `config/{urls,asgi,wsgi,celery}.py`, `manage.py`, `pyproject.toml` with deps from plan.md, `backend/.env.example`
- [ ] T004 [P] Write root `docker-compose.yml` (postgres:16, redis:7, mailpit, backend, frontend) and `backend/Dockerfile` (python:3.12-slim + weasyprint system libs)
- [x] T005 [P] Write `.github/workflows/ci.yml`: backend pytest job
  (PostgreSQL + Redis services) and frontend build job.
- [ ] T006 [P] Configure pytest-django in `backend/pyproject.toml` and shared `backend/conftest.py` (api_client, role-user fixtures via factory_boy)

## Phase 2: Foundational (blocks all stories)

- [ ] T007 Create `apps/core` with `BaseModel` (UUID pk, timestamps, abstract) in `backend/apps/core/models.py`
- [ ] T008 Add response envelope + global exception handler (`{success, data|error}`, error codes per contracts) in `backend/apps/core/renderers.py` and `backend/apps/core/exceptions.py`; wire into DRF settings with PageNumberPagination default
- [ ] T009 Custom `User` model (email auth, 8-role choices) + manager in `backend/apps/users/models.py`; `AUTH_USER_MODEL`; migration
- [ ] T010 simplejwt setup: settings (15-min access, 7-day rotating refresh, blacklist), login view setting httpOnly refresh cookie, refresh/logout views in `backend/apps/users/views.py`, urls per contracts `/auth/*`
- [ ] T011 [P] Role permission classes (IsAdmin, IsManager, IsChef, IsWaiter, IsStorekeeper, IsReceivingOfficer, IsIssuer, role-matrix helper) in `backend/apps/users/permissions.py`
- [ ] T012 [P] Users CRUD endpoints (ADMIN only, deactivate-not-delete) in `backend/apps/users/{serializers,views,urls}.py`
- [ ] T013 [P] `apps/core` config models: `ReasonCode`, `ThresholdConfig`, `IntegrationSettings` (encrypted credential values) + ADMIN CRUD endpoints in `backend/apps/core/{models,serializers,views,urls}.py`
- [ ] T014 `AuditLog` model (append-only, no update/delete manager) + `audit_service.log()` in `backend/apps/core/{models,services}.py`
- [ ] T015 `Approval` engine: model (GenericFK, threshold_snapshot, state machine) + `approval_service.{submit,decide}` + Manager queue endpoints `/approvals/*` in `backend/apps/core/`
- [ ] T016 `OutboxRecord` + `IdempotencyKey` models in `backend/apps/core/models.py`; idempotency middleware/decorator honoring `Idempotency-Key` header in `backend/apps/core/idempotency.py`
- [ ] T017 [P] `apps/masterdata`: `Category`, `Location` (seed 3), `Product` (UoM trio + conversion factors, reorder_level, pastel_code), `Supplier` models + migrations in `backend/apps/masterdata/models.py`
- [ ] T018 [P] masterdata CRUD endpoints with django-filter (products: category/is_active/below_reorder; suppliers deactivate-not-delete) in `backend/apps/masterdata/{serializers,views,urls,filters}.py`
- [ ] T019 `apps/notifications`: `Notification` model, fan-out-by-role service, list/read endpoints in `backend/apps/notifications/`
- [ ] T020 `seed_demo` management command (locations, reason codes, thresholds, 8 demo users, sample products/suppliers/recipes) in `backend/apps/core/management/commands/seed_demo.py`
- [ ] T021 Channels setup: channels-redis layer in settings, auth middleware for WS, empty `kitchen`/`waiter` group consumers registered in `config/asgi.py`
- [ ] T022 Celery wiring: `config/celery.py`, beat schedule placeholder, redis broker config from env
- [ ] T023 [P] Foundation tests: role permission matrix (`backend/apps/users/tests/test_permissions.py`), approval engine state machine (`backend/apps/core/tests/test_approvals.py`), envelope shape (`backend/apps/core/tests/test_envelope.py`)
- [ ] T024 [P] Frontend transport rework: axios apiClient with access-token interceptor + silent-refresh-on-401 in `frontend/src/lib/apiClient.ts`; auth store (in-memory token) in `frontend/src/store/authStore.ts`; envelope unwrapping; login against new `/auth/login/`

**Checkpoint**: `docker compose up` + `pytest` green + frontend login works against Django.

## Phase 3: US1 — Sale → Kitchen → Service (P1) 🎯 MVP

- [ ] T025 [P] [US1] `apps/menu` minimal: `MenuItem` (pos_code), `RecipeVersion` (status, effective dates, immutable-when-published guard), `RecipeLine` models + migrations in `backend/apps/menu/models.py`
- [ ] T026 [P] [US1] `apps/inventory` ledger: `StockMovement` (append-only manager), `StockBalance` models + indexes per data-model.md in `backend/apps/inventory/models.py`
- [ ] T027 [US1] `post_movements()` choke point: transaction + `select_for_update` balance update, parent-document requirement, negative-stock guard with override hook, audit write, outbox write — `backend/apps/inventory/services.py`
- [ ] T028 [US1] `apps/pos_ingest`: `SaleEvent` (unique pos_sale_id), `ReplayLog` models; ingestion service (dedupe → order create → recipe resolve by effective date → deduction via post_movements → unknown-item flagging) in `backend/apps/pos_ingest/{models,services}.py`
- [ ] T029 [US1] POS endpoints: `POST /pos/sale-events/` (idempotent 200 on duplicate), list, `POST .../replay/` (audit logged) in `backend/apps/pos_ingest/{serializers,views,urls}.py`
- [ ] T030 [US1] `apps/kitchen`: `Order`, `OrderItem` (recipe_version snapshot), `OrderStatusEvent`, `OutOfStockFlag` models + status state machine service (READY blocked on pending extra-usage approval) in `backend/apps/kitchen/{models,services}.py`
- [ ] T031 [US1] Kitchen + waiter endpoints per contracts (`/kitchen/orders/*`, `/waiter/orders/*`, out-of-stock, extra-usage routing to wastage entry + approval) in `backend/apps/kitchen/{serializers,views,urls}.py`
- [ ] T032 [US1] Channels broadcast: order.created / order.status events to `kitchen` + `waiter` groups from kitchen services; consumer auth by role in `backend/apps/kitchen/consumers.py`
- [ ] T033 [US1] Insufficient-stock flagging + Storekeeper notification on ingestion in `backend/apps/pos_ingest/services.py` (uses notifications service)
- [ ] T034 [P] [US1] Backend tests: ingestion dedupe/replay (`pos_ingest/tests/`), ledger invariants + choke point (`inventory/tests/test_services.py`), order state machine + endpoints happy/401/403/400 (`kitchen/tests/test_views.py`)
- [ ] T035 [P] [US1] Frontend Kitchen Display feature: order cards (age color, items, modifiers), Start/Ready two-tap actions, extra-usage dialog, out-of-stock toggle, WS-driven React Query invalidation in `frontend/src/features/kitchen/`
- [ ] T036 [P] [US1] Frontend Waiter view: Ready list oldest-first with time-since-ready, Served/Return actions, offline action queue (zustand persist + idempotency keys) in `frontend/src/features/waiter/`
- [ ] T037 [US1] POS simulator script for demos/tests in `backend/scripts/pos_simulator.py`

**Checkpoint**: quickstart V1 passes — sale lands on display < 5 s, stock deducts, dedupe holds, full lifecycle walks.

## Phase 4: US2 — Procurement (P2)

- [ ] T038 [P] [US2] `apps/procurement` models: `PurchaseBudget`+lines, `PurchaseOrder`+lines (po_number sequence, fulfilled_qty), `POSendLog`, `GRN`+lines, `SupplierInvoice`, `InvoiceMatch` in `backend/apps/procurement/models.py`
- [ ] T039 [US2] Budget services: submit → Approval engine, Manager decide, Receiving Officer notification in `backend/apps/procurement/services.py`
- [ ] T040 [US2] PO services: create against approved budget (multi-supplier split), PDF build (weasyprint template `backend/apps/procurement/templates/po.html`), email send via Django mail + `POSendLog`, no-email → MANUAL_CONTACT_REQUIRED in `backend/apps/procurement/services.py`
- [ ] T041 [US2] GRN services: partial receipt with running fulfilled_qty, posting via `post_movements()` (unit costs captured), Budget vs Actual update in `backend/apps/procurement/services.py`
- [ ] T042 [US2] 3-way match service: PO↔GRN↔Invoice compare, discrepancy flagging, resolve/dispute/escalate transitions in `backend/apps/procurement/services.py`
- [ ] T043 [US2] Procurement endpoints per contracts (`/budgets/*`, `/purchase-orders/*`, GRNs, invoices, matches, supplier history) in `backend/apps/procurement/{serializers,views,urls}.py`
- [ ] T044 [P] [US2] Backend tests: budget approval flow, PO email + send log (locmem backend), partial GRN math, 3-way mismatch flagging in `backend/apps/procurement/tests/`
- [ ] T045 [P] [US2] Frontend procurement feature: budget form + approval status, Manager approval queue UI, PO builder with supplier split, GRN entry, invoice match screen in `frontend/src/features/procurement/`

**Checkpoint**: quickstart V2 — mailpit shows PO PDF; stock and Budget vs Actual move.

## Phase 5: US3 — Issuing & Transfers (P3)

- [ ] T046 [P] [US3] `IssueNote`+lines, `Transfer`+lines, `StockTake`+lines models in `backend/apps/inventory/models.py`
- [ ] T047 [US3] Issue services: daily Stores→Kitchen, Tue/Thu Stores→Unit with off-schedule reason (warn-not-block), posting via choke point in `backend/apps/inventory/services.py`
- [ ] T048 [US3] Transfer services: Kitchen↔Unit both directions, value-threshold → Approval engine, post on approve in `backend/apps/inventory/services.py`
- [ ] T049 [US3] Negative-stock override path: 409 INSUFFICIENT_STOCK → override request → Manager Approval → OVERRIDE_ADJ posting in `backend/apps/inventory/services.py`
- [ ] T050 [US3] Inventory endpoints per contracts (`/stock/balances/`, `/stock/movements/`, `/issues/*`, `/transfers/*`) in `backend/apps/inventory/{serializers,views,urls,filters}.py`
- [ ] T051 [P] [US3] Backend tests: Tue/Thu warning, threshold approval routing, negative-stock block + override audit in `backend/apps/inventory/tests/`
- [ ] T052 [P] [US3] Frontend inventory feature: stock-on-hand by location, issue note form, transfer form with approval status badge in `frontend/src/features/inventory/`

## Phase 6: US4 — Wastage & Stock-Take (P4)

- [ ] T053 [P] [US4] `apps/wastage`: `WastageEntry` model (3 types, value computation from latest GRN cost) in `backend/apps/wastage/models.py`
- [ ] T054 [US4] Wastage services: threshold routing, posting via choke point, order linkage for extra usage in `backend/apps/wastage/services.py` (kitchen extra-usage from T031 delegates here)
- [ ] T055 [US4] Stock-take services: open (freeze system qty), submit counts, variance compute, threshold-route, post adjustment in `backend/apps/inventory/services.py`
- [ ] T056 [US4] Wastage + stock-take endpoints per contracts in `backend/apps/wastage/{serializers,views,urls}.py` and `backend/apps/inventory/views.py`
- [ ] T057 [P] [US4] Backend tests: threshold approve/below-post, stock-take variance math vs frozen baseline in `backend/apps/wastage/tests/` + `backend/apps/inventory/tests/test_stocktake.py`
- [ ] T058 [P] [US4] Frontend wastage feature: log dialog (type/reason/qty), stock-take count sheet with variance preview in `frontend/src/features/wastage/`

## Phase 7: US5 — Menu & Recipe Versioning full (P5)

- [ ] T059 [US5] Versioning services: edit-creates-next-version, Draft→Review→Published transitions, effective-date resolution, retire-on-supersede, delete → 409 with history in `backend/apps/menu/services.py`
- [ ] T060 [US5] Menu endpoints per contracts (`/menu-items/*`, `/recipe-versions/*` workflow actions) + optional schedule JSON in `backend/apps/menu/{serializers,views,urls}.py`
- [ ] T061 [P] [US5] Backend tests: historical order keeps v1 after v2 publish (SC-010), published immutability, deletion guard in `backend/apps/menu/tests/`
- [ ] T062 [P] [US5] Frontend menu feature: item list, version timeline, recipe editor (lines + UoM), publish workflow with effective date in `frontend/src/features/menu/`

## Phase 8: US6 — Pastel Sync (P6)

- [ ] T063 [P] [US6] `apps/pastel`: `PastelSyncLog`, `ReconciliationRun`/`Line` models + dev stub adapter (HTTP, `PASTEL_STUB_FAIL` switch) in `backend/apps/pastel/{models,adapter,stub}.py`
- [ ] T064 [US6] Outbox drain: Celery tasks per mode (real-time immediate, daily batch beat job, event-only filter), `retry_backoff` exponential, attempt logging, ABANDONED after max in `backend/apps/pastel/tasks.py`
- [ ] T065 [US6] Pastel endpoints: sync log list, manual resend, reconciliation run + report per contracts in `backend/apps/pastel/{serializers,views,urls}.py`
- [ ] T066 [US6] Daily reconciliation Celery beat task comparing balances vs stub/Pastel in `backend/apps/pastel/tasks.py`
- [ ] T067 [P] [US6] Backend tests: outbox atomicity (movement+outbox same txn), zero-loss/zero-dup drain after simulated outage (SC-008) in `backend/apps/pastel/tests/`
- [ ] T068 [P] [US6] Frontend integration-health dashboard (sync failures, resend button, recon results) in `frontend/src/features/admin/`

## Phase 9: US7 — Reports (P7)

- [ ] T069 [P] [US7] Report selectors (one per report: stock-on-hand, budget-vs-actual w/ drill-down refs, PO/GRN registers, issues-by-destination, wastage, service-time, movers, leakage, recipe-costing, reorder-suggestions) in `backend/apps/reports/selectors.py`
- [ ] T070 [US7] Export service: `?format=json|pdf|xlsx` — weasyprint print template + openpyxl writer, single dispatch in `backend/apps/reports/{services,templates/}`
- [ ] T071 [US7] Report endpoints + Pastel recon passthrough per contracts in `backend/apps/reports/{views,urls}.py`
- [ ] T072 [P] [US7] Backend tests: seeded dataset vs expected totals fixture (SC-007) in `backend/apps/reports/tests/` incl. `fixtures/expected_totals.md`
- [ ] T073 [P] [US7] Frontend reports feature: report browser, filters, export buttons, Manager dashboard (wastage today, pending approvals, low stock, sync health) in `frontend/src/features/reports/`

## Phase 10: US8 — Admin & Master Data UI (P8)

- [ ] T074 [P] [US8] Frontend admin feature: users CRUD, product master with UoM conversions, supplier master, thresholds + reason codes, integration settings in `frontend/src/features/admin/`
- [ ] T075 [US8] UoM conversion enforcement in GRN (purchase→stock) and recipe deduction (recipe→stock) paths + tests in `backend/apps/inventory/services.py`, `backend/apps/procurement/services.py`
- [ ] T076 [P] [US8] Role-matrix integration test sweep across all endpoint groups (SC-009) in `backend/apps/users/tests/test_role_matrix.py`

## Phase 11: Polish & Cross-Cutting

- [ ] T077 [P] Notifications surfacing in frontend shell (bell, unread count, deep links) in `frontend/src/features/notifications/`
- [ ] T078 [P] Localisation settings (currency, date format, timezone) applied in exports + frontend formatting in `backend/apps/core/` + `frontend/src/lib/format.ts`
- [ ] T079 [P] Frontend tests (Vitest+RTL+MSW) for kitchen, waiter, procurement critical flows in `frontend/src/features/*/**.test.tsx`
- [ ] T080 Performance pass: `select_related`/`only` audit on hot selectors, index verification with EXPLAIN on ledger queries, 5-second ingestion timing test
- [ ] T081 [P] Frontend Dockerfile + production compose overrides (`docker-compose.prod.yml`)
- [ ] T082 [P] Update `docs/` team documentation + `backend/.env.example`/`frontend/.env.example` final sweep; quickstart V1-V8 full walkthrough
- [ ] T083 Run full quickstart validation (V1-V8) and fix fallout; tag `v0.1.0` on `main`

## Dependencies

```text
Phase 1 → Phase 2 → US1 (P3) ─┬→ US2 (P4) ──→ US7 reports needing GRN costs
                              ├→ US3 (P5) ─┬→ US4 (P6) → US7 (P9)
                              ├→ US5 (P7)  │
                              └→ US6 (P8) ←┴ (outbox already written by choke point from US1)
US8 (P10) UI depends on Phase 2 APIs; T075 depends on US2+US1. Phase 11 last.
```

- US1 is the only story blocking others (it creates menu-minimal + ledger + choke point).
- US2, US3, US5, US6 are mutually independent after US1 — parallelizable across developers.
- US4 needs US3 (stock-take lives on inventory) and US1 (extra usage links orders).

## Parallel example (team of 3 after US1 checkpoint)

```text
Dev A: T038-T045 (US2 procurement)
Dev B: T046-T052 (US3 issuing) then T053-T058 (US4 wastage)
Dev C: T059-T062 (US5 versioning) then T063-T068 (US6 pastel)
```

## Implementation strategy

MVP = Phases 1-3 (T001-T037): restructure, foundation, full sale→kitchen→service flow with real deductions. Demo-able to stakeholders and already replaces paper tickets. Then increments per story checkpoint; each checkpoint ends with its quickstart scenario green and a conventional commit on `dev`.

**Total: 83 tasks** — Setup 6, Foundation 18, US1 13, US2 8, US3 7, US4 6, US5 4, US6 6, US7 5, US8 3, Polish 7.
