# ERP Backend Documentation - Operations, Testing, and Handoff

## 1. Local Runbook

### Environment
1. Copy .env.example to .env.
2. Set JWT secret and service URLs if needed.

### Install
- pip install -e .[dev]

### Migrate
- alembic upgrade head

### Run API
- uvicorn app.main:app --reload

### Run with Docker
- docker compose up --build

## 2. Health and Smoke Checks
- GET /healthz should return status ok.
- Auth flow requires seeded or manually inserted users.
- Inventory endpoints require authenticated user context and branch assignment.

## 3. Test Suite Guide

### Current tests
- test_health.py: liveness endpoint.
- test_auth_security.py: hashing and token behavior.
- test_rbac.py: role guard semantics.
- test_week3_models.py: schema constraints and branch fields.
- test_week4_inventory_service.py: low-stock and cache-key helper behavior.
- test_week5_audit_events.py: audit/event utility behavior.
- test_week6_procurement.py: procurement order draft-submit-approve-receive flow, stock receipt side effects, and procurement reports.
- test_week6_audit_integration.py: integration checks for write-generated audit logs, branch-scope denial, and deterministic pagination.
- test_week7_observability.py: event/audit observability metrics and instrumentation checks.
- test_week8_monitoring_export.py: exporter adapter correctness and /metrics endpoint behavior.
- test_week9_inventory_ui_contract.py: movement history endpoint filters/order and UI contract validation.
- test_week10_sales_pos.py: POS sales flow (happy path, BOM insufficiency rejection, branch mismatch rejection, receipt + daily summary contracts).
- test_week11_sales_void.py: sale void flow (stock reversal, branch denial, duplicate-void rejection).
- test_week11_sales_refund.py: sale refund flow (stock reversal, branch denial, duplicate-refund rejection, and refund-after-void rejection).
- test_week12_sales_pricing.py: POS pricing and split-tender validation contracts.
- test_week13_payment_integration.py: payment provider intent/reconciliation contracts including async reconcile job enqueue + status polling.
- test_week14_reconciliation_ops.py: async reconciliation failure reason labeling and Prometheus alert rule coverage.
- test_week15_durable_async_jobs.py: Celery task execution behavior for successful and failed reconciliation runs.
- test_week16_reporting.py: reporting endpoint contracts (sales JSON/CSV, inventory valuation/movements, async procurement spend task status).
- test_week17_websocket_dashboard.py: websocket auth/connect behavior and branch-scoped domain/anomaly broadcast contract coverage.

### Suggested command
- python -m pytest

## 4. Security Notes
- Replace default JWT secret immediately in non-local environments.
- Never use default credentials in shared or production systems.
- Keep role checks explicit on all write endpoints.
- Enforce branch checks in all queries and service functions.

## 5. Observability Notes (Current)
- Structured observability helpers are wired in write-event and audit query paths.
- Request IDs and event correlation IDs are included in structured logs.
- In-process counters and latency histograms are recorded for event publish/handlers and audit query flow.
- Week 8 exporter adapter now forwards in-process counters and histogram samples to Prometheus.
- /metrics is exposed for pull-based scraping by Prometheus.
- Monitoring stack assets are in monitoring/ (Prometheus rules, Grafana dashboard provisioning, Loki/Promtail log pipeline, Alertmanager routing).

## 6. Current Integration Status

### Fully wired
- health router
- auth router
- inventory router
- procurement router
- Redis stock caching for stock/current
- audit router
- immutable audit migration
- startup event handler registration
- inventory write event publishing with audit + cache invalidation handlers
- procurement order lifecycle and goods received note workflow with stock receipt event publication
- sales router with transactional sale creation, receipt endpoint, and daily summary endpoint
- sales void endpoint with audit/cache side-effects preserved through shared event bus handlers
- sales refund endpoint with audit/cache side-effects preserved through shared event bus handlers
- sales payment intent + reconciliation contract endpoints (simulated provider abstraction)
- asynchronous reconciliation workflow endpoints (enqueue + poll status) over simulated provider
- Week 14 alert rules for async reconciliation failures and queue lag
- Week 15 Celery worker-backed execution for async reconciliation jobs
- Week 16 reports router for sales, inventory, and procurement spend analytics
- Week 17 live dashboard WebSocket endpoint and event broadcast bridge

### Remaining hardening tasks (What Is Not There Yet)
- Hook Alertmanager webhooks to production notification targets.
- Calibrate alert thresholds against production baselines.
- Add SLO burn-rate alerts when baseline traffic/latency distributions are available.
- Expand simulated provider abstraction to a real payment gateway adapter.
- Add production task monitoring, retry policy tuning, and dead-letter queue strategy.
- Add role-specific report visibility/preset governance if multi-tenant reporting requirements expand.

## 7. Handoff Block for New Chat
Use this block whenever you split chats:

- Stage: Week 17 live dashboard websocket feed complete
- Built: foundation, auth/RBAC, core schema, inventory APIs, immutable audit/event flow, week 6 integration hardening, week 7 observability instrumentation, week 8 monitoring exporter + dashboards + alerts assets, week 9 inventory frontend app + movement history contract endpoint, week 10 POS backend/API + POS UI flow, week 11 sale void + refund backend flows + POS reversal UI controls, week 12 POS pricing contracts + split tender validation + receipt pricing breakdowns, week 13 payment-provider abstraction with intent/reconciliation API contracts, week 14 async reconciliation operations hardening (polling + alerts + failure reason labels), week 15 Celery worker execution for async reconciliation jobs, week 16 reporting APIs/contracts, and week 17 live dashboard websocket broadcasts
- Validated: backend sale regression slice plus Week 13/14/15/16/17 tests, and frontend production build
- Current blockers: production Alertmanager destinations are placeholders; live migration/run still requires reachable PostgreSQL/Redis infrastructure
- Key risk: maintain strict branch scoping, append-only audit guarantees, and cache invalidation consistency on every new write path

### Ready-to-Paste Chat Handoff
Stage: Week 17 live dashboard websocket feed complete
Built: foundation, auth/RBAC, core schema, inventory APIs, immutable audit/event flow, integration hardening tests, observability instrumentation, metrics export and monitoring stack assets, inventory frontend UI app, movement history API contract, POS sales backend/API, POS frontend checkout/receipt/summary flow, sale void + refund backend flows, POS reversal UI controls, POS pricing/tender contracts, payment intent/reconciliation API contracts behind a simulated provider abstraction, async reconciliation polling + alert signals, Celery worker-backed reconciliation execution, reports router contracts (sales, inventory, procurement spend), and branch-scoped websocket dashboard broadcasts
Validated: backend sale regression slice and Week 13/14/15/16/17 tests passing plus frontend production build
Current focus: productionization and replacing simulated payment adapters with real gateway integrations
Required outcomes:
1. Wire real Alertmanager receivers and validate notification routing.
2. Validate migration and runtime startup in an environment with reachable PostgreSQL/Redis.
3. Replace simulated payment adapter with real provider integration while preserving Celery async contracts, branch-safe status polling, and report consistency.
Risk to watch: preserve strict branch-scoping, immutable audit append behavior, and cache invalidation consistency on every new write path.
First implementation step: implement a real payment adapter for card/mobile tenders while preserving current async reconciliation/reporting API contracts and strict branch scoping.

## 8. Week 8 Hardening Checklist
1. Export observability metrics/logs to external backend. (Done: Prometheus + Loki/Promtail wiring)
2. Add dashboards for event and audit telemetry. (Done: monitoring/grafana/dashboards/erp-observability.json)
3. Add operational runbook checks using dashboard and alert signals. (Partial: deployment-side webhook destinations still required)
4. Define and wire alerting thresholds for repeated event-handler failures and audit query degradation. (Done: monitoring/prometheus/alerts.yml)

## 9. Documentation Update Checklist (Use for Every Future Stage)
1. Update milestone status in [01_SYSTEM_OVERVIEW.md](01_SYSTEM_OVERVIEW.md).
2. Update endpoint/runtime flow changes in [02_API_AND_RUNTIME_FLOWS.md](02_API_AND_RUNTIME_FLOWS.md).
3. Update migration/schema notes in [03_DATABASE_AND_MIGRATIONS.md](03_DATABASE_AND_MIGRATIONS.md).
4. Update validation counts and handoff block in this file.
5. Include risks and next target explicitly in handoff format.
