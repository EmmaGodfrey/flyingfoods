# System Analysis Report

## 1. Executive Summary
This workspace contains a modular-monolith ERP platform with:
- Backend API in FastAPI (inventory, procurement, sales/POS, reports, audit, search, monitoring, auth, websocket dashboard).
- PostgreSQL transactional store with branch-scoped multi-tenant style data partitioning.
- Redis for cache and token/job metadata (with graceful None fallback if unavailable).
- RabbitMQ + Celery for async jobs (payment reconciliation and report/search tasks).
- Optional Elasticsearch-backed global search with SQL fallback.
- React + Vite frontend with protected routes and direct role-agnostic UI access to backend capabilities.

The system is functionally rich for core branch operations (inventory, sales, procurement), but still includes shell/stub UI areas and multiple operational fallbacks that reduce strictness/durability when infra services are unavailable.

## 2. System Purpose And Objectives
Evidence from route modules and tests indicates objectives are:
- Branch-scoped inventory control: product catalog, stock ledger, computed stock, low-stock alerts.
- Procurement workflow: suppliers, purchase orders, submit/approve transitions, GRN posting, spend/order reporting.
- POS workflow: sale creation, receipt retrieval, daily summary, void/refund operations.
- Payment integration contract: simulated provider intent + synchronous/asynchronous reconciliation.
- Governance: immutable audit chain for domain writes and query endpoint with branch controls.
- Observability: counters/histograms, Prometheus /metrics export, alert rules, websocket event fan-out.
- Search: unified product/supplier/invoice lookup.

## 3. High-Level Architecture Overview
- API composition: app factory registers routers and event handlers.
- Domain services: business logic lives in app/services.
- Persistence: SQLAlchemy ORM + Alembic migrations.
- Eventing: in-process event bus publishes inventory.write.v1 events; handlers write audit rows, invalidate stock cache, and broadcast websocket events.
- Async processing: Celery tasks execute reconciliation/report/search jobs.
- Frontend: React SPA consumes backend APIs and performs token refresh.

## 4. Technology Stack
### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy asyncio + asyncpg
- Alembic
- Redis
- Celery
- RabbitMQ
- PyJWT + bcrypt/passlib
- prometheus-client
- Elasticsearch client

### Frontend
- React 18
- Vite
- TypeScript
- React Router
- Zustand
- TanStack React Query

### Ops/Infra
- Docker Compose stack: API, worker, PostgreSQL, Redis, RabbitMQ, Elasticsearch, Prometheus, Alertmanager, Loki/Promtail, Grafana.

## 5. Database Structure And Relationships
### Core entities
- branches: tenant partition key.
- users: auth principals with role + branch_id.
- categories, units, suppliers, products: branch-scoped master data.
- stock_movements: append-only inventory ledger (receive/sale/waste/adjustment).
- bill_of_materials: finished product -> ingredient product mapping.
- sales, sale_line_items: POS transactions.
- purchase_orders, purchase_order_line_items, goods_received_notes, goods_received_note_line_items: procurement workflow.
- audit_logs: immutable hash-chained audit trail.

### Key relationship patterns
- Almost all domain rows carry branch_id and FK to branches.
- products can reference category/unit/supplier.
- stock_movements references products/users and drives computed stock.
- BOM supports ingredient depletion during sale creation.
- Sales and procurement both generate stock movements and audit events.

### Integrity constraints from migrations
- Unique constraints per branch for key names (categories, units, suppliers, products).
- BOM self-reference prevention + uniqueness on (branch_id, product_id, ingredient_id).
- Append-only audit protections via PostgreSQL triggers (update/delete forbidden when PG dialect is active).
- Sale and procurement status metadata with audit/user references.

## 6. Authentication And Authorization Mechanisms
### Authentication
- JWT bearer access tokens and refresh tokens.
- Login verifies email/password and active user.
- Refresh rotation validates token type; Redis-backed JTI revocation when Redis is available.
- /auth/me returns current principal.

### Authorization
- Role gates are endpoint-level via require_role.
- Roles used: superadmin, admin, manager, inventory_officer, cashier.
- Branch scoping mostly derived from current_user.branch_id (get_current_branch).
- Audit endpoint adds stricter cross-branch rules: only superadmin/admin can request arbitrary branch_id.

## 7. External Integrations And Dependencies
- Redis: caching, refresh token revocation, async metadata tracking.
- RabbitMQ/Celery: background jobs.
- Elasticsearch: optional search index; fallback to DB search if unavailable.
- Prometheus stack: metrics scraping and alerting.
- Websocket clients: live dashboard updates from domain events.
- Payment provider: simulated provider contract only (not real gateway).

## 8. Core Business Processes
1. Inventory management
- CRUD products.
- Record stock movements.
- Compute current stock and low-stock alerts.

2. Procurement
- Manage suppliers.
- Create -> submit -> approve purchase orders.
- Record GRN to increase stock and auto-transition PO status (received/closed).
- Generate order and spend reports.

3. Sales/POS
- Build sale from line items (BOM-aware depletion).
- Apply tax/discount and split tenders.
- Retrieve receipts and daily summary.
- Handle void/refund with stock reversal adjustments.

4. Payment reconciliation contract
- Create payment intent for eligible tenders.
- Reconcile synchronously or enqueue async job.
- Poll job status endpoint.

5. Audit + observability
- Domain writes emit events.
- Audit logs persisted with hash chain.
- Metrics counters/histograms exported and alerted.
- Websocket broadcasts for domain and anomaly events.

## 9. Endpoint Inventory (Backend)
### Auth
- POST /auth/login
- POST /auth/refresh
- GET /auth/me

### System
- GET /healthz
- GET /metrics
- WS /ws/dashboard

### Inventory
- GET /inventory/products
- POST /inventory/products
- GET /inventory/products/{product_id}
- PUT /inventory/products/{product_id}
- DELETE /inventory/products/{product_id}
- POST /inventory/movements
- GET /inventory/movements
- GET /inventory/stock/current
- GET /inventory/stock/low

### Procurement
- POST /procurement/orders
- GET /procurement/orders
- PUT /procurement/orders/{id}/submit
- PUT /procurement/orders/{id}/approve
- POST /procurement/grn
- GET /procurement/reports/orders
- GET /procurement/reports/spend
- POST /procurement/suppliers
- GET /procurement/suppliers
- PUT /procurement/suppliers/{id}
- DELETE /procurement/suppliers/{id}

### Sales
- POST /sales
- GET /sales/summary/daily
- GET /sales/{id}/receipt
- POST /sales/{id}/void
- POST /sales/{id}/refund
- POST /sales/{id}/payments/intent
- POST /sales/{id}/payments/reconcile
- POST /sales/{id}/payments/reconcile/async
- GET /sales/{id}/payments/reconcile/jobs/{job_id}

### Reports
- GET /reports/sales
- GET /reports/sales/export/csv
- GET /reports/inventory/valuation
- GET /reports/inventory/movements
- GET /reports/procurement/spend
- POST /reports/procurement/spend/async
- GET /reports/tasks/{task_id}/status

### Search
- GET /search

## 10. Manual Review Hotspots (Unclear/Incomplete Areas)
1. Frontend reports/settings are route shells, not full modules.
2. Refresh-token revocation and async metadata durability depend on Redis availability.
3. Websocket auth uses query parameter token; transport and log hygiene should be reviewed.
4. started_at in async payment status is never populated (always null in current implementation).
5. Procurement API catches broad Exception in multiple endpoints; domain-specific error mapping exists but fallback can hide root causes.

## 11. Assumptions
- Assumption: No hidden services outside this workspace are required for core CRUD behavior.
- Assumption: Role semantics are organization-defined and map directly to role string values in users.role.
- Assumption: Production-grade secret management and TLS termination are external to this repo.
