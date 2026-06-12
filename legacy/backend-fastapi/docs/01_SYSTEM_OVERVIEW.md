# ERP Backend Documentation - System Overview

## 1. Purpose
This document explains what has been built in the ERP backend so far, how each major part works, and how the parts connect.

Current implementation is a modular monolith backend built with FastAPI, SQLAlchemy async, PostgreSQL, Redis, and RabbitMQ-ready infrastructure.

## 2. Milestone Status

### Week 1 (Foundation) - Complete
- FastAPI app skeleton.
- Docker Compose local stack.
- Async DB session setup.
- Alembic migration baseline.
- Health endpoint and smoke test.

### Week 2 (Auth + RBAC + Branch Isolation Primitives) - Complete
- User and Branch models.
- JWT login and refresh endpoints.
- Password hashing.
- Redis-backed refresh token tracking.
- Role guard dependency.
- Branch extraction dependency.

### Week 3 (Core Inventory Schema) - Complete
- Category, Unit, Supplier, Product models.
- StockMovement event ledger model.
- Bill of Materials model.
- Branch-based indexing and constraints.
- Seed helper for baseline branch data.

### Week 4 (Inventory API) - Complete
- Product CRUD endpoints.
- Stock movement append-only endpoint.
- Computed stock endpoint (SUM over movements).
- Low-stock endpoint.
- Redis cache-aside for branch stock snapshot.

### Week 5 (Immutable Audit + Auto-Logging Hooks + Audit API + Event Bus) - Complete
- Immutable audit table migration added with append-only protections.
- Audit model, schemas, service, and query API are wired.
- In-process event bus is registered at app startup.
- Inventory write paths publish inventory.write.v1 events.
- Audit write and cache invalidation are handled via subscribed event handlers.

### Procurement Module (Roadmap Week 6) - Complete
- Added purchase order, purchase order line item, goods received note, and goods received note line item models.
- Added procurement router with draft, submit, approve, GRN receipt, and report endpoints.
- GRN flow appends stock receipt movements and preserves inventory audit/cache side effects through inventory.write.v1.
- Added procurement workflow integration tests and procurement migration.

### Week 6 (Integration Hardening) - Complete
- Added integration test coverage for write-to-audit persistence.
- Added branch-scope denial coverage for audit queries.
- Added deterministic audit pagination/ordering coverage.

### Week 7 (Operational Observability Hardening) - Complete
- Added shared observability helpers for structured logs and in-process metrics.
- Added event publish/handler counters and latency histograms.
- Added audit query throughput/denial counters and query latency histogram.
- Added observability regression tests.

### Week 8 (Production Observability Export + Alerts + Dashboards) - Complete
- Added Prometheus exporter adapter over in-process metrics/histograms.
- Added /metrics endpoint and monitoring backend wiring (Prometheus/Loki/Grafana/Alertmanager assets).
- Added alert rules for repeated handler failures and audit query degradation.
- Added exporter correctness/non-disruptive tests.

### Week 9 (Inventory Frontend UI) - Complete
- Added `erp-web` React + Vite inventory UI app aligned to the blue/white design system.
- Implemented products list with search + pagination and status badges using computed stock.
- Implemented add/edit product modal with inline validation.
- Implemented stock movement history page with type/date filters.
- Implemented receive stock form flow that triggers movement creation and live stock refresh.
- Added backend contract endpoint `GET /inventory/movements` for movement history queries.

### Week 10 (POS Backend/API + UI Flow) - Complete
- Added sales domain tables and migration (`sales`, `sale_line_items`).
- Added transactional sales service with branch-scoped product resolution and BOM-aware stock validation.
- Added endpoints:
	- `POST /sales`
	- `GET /sales/{id}/receipt`
	- `GET /sales/summary/daily`
- Sales writes publish `inventory.write.v1` (`sale.create`) so existing immutable audit append and stock cache invalidation handlers remain intact.
- Added POS frontend flow in `erp-web`: product grid, basket/checkout, receipt panel/print action, and daily summary polling.

### Week 11 (POS Reversal Flows) - Complete
- Added sale void workflow endpoint: `POST /sales/{id}/void`.
- Added branch-scoped void validation and duplicate-void protection.
- Void operation reverses prior sale stock movements and preserves immutable audit/event/cache behavior.
- Added week 11 test coverage for void happy path, branch denial, and duplicate-void rejection.
- Added sale refund workflow endpoint: `POST /sales/{id}/refund`.
- Added refund status guards (duplicate refund rejection and disallow refund from non-completed status).
- Refund operation reverses prior sale stock movements and preserves immutable audit/event/cache behavior.
- Added week 11 test coverage for refund happy path, branch denial, duplicate refund rejection, and refund-after-void rejection.
- Added POS UI receipt actions for void/refund so reversal flows are accessible from frontend.

### Week 12 (POS Pricing and Split-Tender Contracts) - Complete
- Added tax and discount inputs to sale contract and receipt output.
- Added split-tender payment contract validation with exact-total checks.
- Added backend coverage for pricing/tender validation paths.
- Added POS UI support for tax, discount, and split tender checkout fields.

### Week 13 (Payment Provider Contract Skeleton) - Complete
- Added simulated payment-provider abstraction for digital tenders.
- Added sale payment intent and reconciliation contract endpoints.
- Added branch-scoped checks for payment endpoints.
- Added backend coverage for payment intent/reconcile contracts and side-effect guardrails.

### Week 14 (Reconciliation Operations Hardening) - Complete
- Added async reconciliation workflow endpoints (enqueue + status polling).
- Added reconciliation job status lifecycle (queued/running/succeeded/failed).
- Added failure-reason labeling for async reconciliation metrics (including reference mismatch).
- Added Prometheus alert rules for async reconciliation failures and queue lag.
- Added POS UI async reconciliation flow with job polling and status rendering.

### Week 15 (Durable Async Jobs Foundation) - Complete
- Added Celery app wiring with RabbitMQ broker + Redis result backend support.
- Added sales reconciliation Celery task and worker execution path.
- Replaced in-process async reconciliation execution with Celery task dispatch.
- Added metadata persistence for reconciliation jobs so status polling remains branch-safe.
- Added Week 15 tests for task success/failure behavior.

### Week 16 (Reporting Module) - Complete
- Added branch-scoped sales report endpoint with JSON line items and totals.
- Added sales CSV export endpoint.
- Added inventory valuation report endpoint.
- Added inventory movement report endpoint with filters and pagination.
- Added procurement spend report endpoint and async report task polling contracts.
- Added Week 16 report contract tests.

### Week 17 (WebSockets + Live Dashboard Feed) - Complete
- Added branch-scoped WebSocket endpoint at `/ws/dashboard` with token authentication.
- Added event-bus to WebSocket broadcast bridge for inventory/sales domain write events.
- Added anomaly alert broadcasts for sale void/refund domain actions.
- Added frontend live connection indicator and event stream panel in POS UI.
- Added Week 17 WebSocket integration test coverage.

## 3. Architecture Summary

### Runtime Layers
1. API Layer (request parsing, HTTP status handling)
2. Dependency Layer (auth, RBAC, branch scoping, DB session, Redis)
3. Service Layer (business logic and query composition)
4. Data Layer (SQLAlchemy models, Alembic migrations)

### Why this structure
- Keeps endpoint files thin.
- Keeps business rules testable in service functions.
- Supports gradual feature growth without large rewrites.

## 4. Security and Isolation Guarantees
- Every authenticated request resolves a current user from JWT.
- Branch isolation is enforced by passing current branch into service queries.
- Role checks are enforced by dedicated dependency guards.
- Refresh tokens can be invalidated/rotated through Redis key lifecycle.

## 5. Stock and Inventory Design
- Stock is event-sourced from stock_movements table, not a mutable current_stock column.
- Computed stock endpoint calculates SUM(qty) grouped by product.
- Low-stock endpoint compares computed stock with product reorder_level.
- Cache entries are invalidated when new stock movements are created.

## 6. File Map by Responsibility

### Root
- pyproject.toml: package metadata and dependencies.
- .env.example: environment template.
- docker-compose.yml: local service topology.
- Dockerfile: API image build.
- alembic.ini: migration configuration.
- README.md: quick start.

### app/
- main.py: app factory and router registration.

#### app/api/
- health.py: liveness endpoint.
- auth.py: login, refresh, me.
- dependencies.py: auth and role dependencies.
- inventory.py: week 4 inventory endpoints.
- procurement.py: purchase order, goods receipt, and procurement report endpoints.
- audit.py: audit query endpoint with branch-scoped filtering.

#### app/core/
- config.py: settings and computed DB URL.
- redis.py: Redis dependency.
- events.py: in-process event bus used for inventory write event handling.
- observability.py: shared structured logging and in-process metrics helpers.

#### app/db/
- base.py: declarative base.
- session.py: async engine/session factory.
- seed_week3.py: minimal branch/category/unit/supplier/product/BOM/stock seed logic.

#### app/db/models/
- branch.py, user.py: auth and tenancy core.
- category.py, unit.py, supplier.py, product.py: inventory catalog core.
- stock_movement.py: event ledger model.
- bom.py: product-ingredient relationships.
- audit_log.py: immutable audit model with hash-chain fields.
- __init__.py: model exports for discovery.

#### app/schemas/
- auth.py: auth request/response schemas.
- inventory.py: inventory request/response schemas.
- audit.py: audit response/filter schemas.

#### app/services/
- security.py: bcrypt + JWT helpers.
- auth_service.py: token issue and refresh rotation.
- inventory_service.py: product/movement/stock/alert logic.
- procurement_service.py: purchase order lifecycle, GRN receipt, and procurement reporting logic.
- audit_service.py: audit write/query logic and branch scope resolver.
- inventory_events.py: event subscriptions for audit write and cache invalidation.

### alembic/versions/
- 20260527_0001_initial_empty_schema.py
- 20260527_0002_auth_and_branches.py
- 20260527_0003_inventory_core_schema.py
- 20260528_0004_immutable_audit_log.py
- 20260530_0009_procurement_workflow.py

### tests/
- test_health.py
- test_auth_security.py
- test_rbac.py
- test_week3_models.py
- test_week4_inventory_service.py
- test_week6_procurement.py
- test_week5_audit_events.py (covers audit/event utility behavior)
- test_week6_audit_integration.py (integration coverage for audit persistence and branch-scope querying)
- test_week7_observability.py (metrics/logging instrumentation behavior)

## 7. Current Known Gaps (What Is Not There Yet)
- Production Alertmanager destinations are placeholders and not integrated with real notification providers.
- End-to-end migration execution still depends on reachable PostgreSQL infrastructure in the target environment.
- POS scope now includes pricing/tender contracts, provider skeleton, and durable async reconciliation workflow, but a real payment gateway adapter is not implemented.
- Request-level distributed tracing is not implemented.

## 8. Recommended Next Step
Prioritize production integration: wire real Alertmanager receivers, validate migration + runtime startup in an environment with active PostgreSQL/Redis services, and replace the simulated payment provider with a real gateway adapter while preserving branch-scoped behavior and immutable write-side guarantees.
