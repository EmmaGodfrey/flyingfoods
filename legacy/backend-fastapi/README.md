# ERP Core (Week 17 Live Dashboard WebSockets)

This project starts implementation of the ERP roadmap with a modular monolith backend.

## What is included

- FastAPI application skeleton with health endpoint.
- Docker Compose development stack: API, PostgreSQL 16, Redis 7, RabbitMQ 3.
- SQLAlchemy async session wiring.
- Alembic migration setup with an initial empty migration.
- Basic project layout for upcoming auth, inventory, procurement, POS, and audit modules.
- Week 8 observability export endpoint at /metrics backed by Prometheus adapter wiring.
- Monitoring stack definitions for Prometheus, Grafana, Loki/Promtail, and Alertmanager.
- Week 9 inventory frontend app scaffold is available in sibling folder ../erp-web.
- Week 10 sales/POS backend APIs are available at:
   - POST /sales
   - GET /sales/{id}/receipt
   - GET /sales/summary/daily
- Week 6 procurement backend APIs are available at:
   - POST /procurement/orders
   - GET /procurement/orders
   - PUT /procurement/orders/{id}/submit
   - PUT /procurement/orders/{id}/approve
   - POST /procurement/grn
   - GET /procurement/reports/orders
   - GET /procurement/reports/spend
- Week 11 sales reversal APIs are available at:
   - POST /sales/{id}/void
   - POST /sales/{id}/refund
- Week 12 POS pricing/tender contract support is available at:
   - POST /sales with tax, discount, and split-tender validation
   - GET /sales/{id}/receipt with pricing and tender breakdown fields
- Week 13/14 payment reconciliation contracts are available at:
   - POST /sales/{id}/payments/intent
   - POST /sales/{id}/payments/reconcile
   - POST /sales/{id}/payments/reconcile/async
   - GET /sales/{id}/payments/reconcile/jobs/{job_id}
- Week 15 durable async foundation is wired with Celery worker execution for async reconciliation jobs.
- Week 16 reporting endpoints are available at:
   - GET /reports/sales
   - GET /reports/sales/export/csv
   - GET /reports/inventory/valuation
   - GET /reports/inventory/movements
   - GET /reports/procurement/spend
   - POST /reports/procurement/spend/async
   - GET /reports/tasks/{task_id}/status
- Week 17 live dashboard WebSocket endpoint is available at:
   - WS /ws/dashboard?token=<access_token>
   - Branch-scoped domain event broadcasts from inventory/sales write paths

## Quick start

1. Copy environment file:

   cp .env.example .env

2. Install dependencies:

   pip install -e .[dev]

3. Run migrations:

   alembic upgrade head

   Optional preflight (recommended when local infrastructure may be down):

   python scripts/migration_preflight.py

   To only check DB connectivity without running Alembic:

   python scripts/migration_preflight.py --check-only

4. Start API:

   uvicorn app.main:app --reload

   Optional durable async worker:

   celery -A app.core.celery_app.celery_app worker --loglevel=info

5. Health check:

   GET /healthz

## Docker

Run from this folder:

- docker compose up --build

Then open:

- http://localhost:5173
- http://localhost:8001/healthz
- http://localhost:8001/metrics
- http://localhost:3000 (Grafana, admin/admin)
- http://localhost:9090 (Prometheus)
- http://localhost:9093 (Alertmanager)

Notes:

- The frontend is now started by Compose as the `frontend` service.
- The API is published on port `8001` to avoid conflicts with local services already using `8000`.

## Week 8 Monitoring Notes

- Application metrics are exported from in-process counters/histograms through a Prometheus adapter.
- Dashboards and alert rules are provisioned under monitoring/.
- Alerts currently route to webhook placeholders:
   - http://host.docker.internal:5001/alerts/ops
   - http://host.docker.internal:5001/alerts/oncall

## What Is Not There Yet

- Production Alertmanager destinations are still placeholders.
- End-to-end runtime still requires reachable PostgreSQL/Redis infrastructure in your target environment.
- Payment gateway integration and reconciliation workflows are not implemented.
- Real payment gateway integration is not implemented (simulated provider is used).
- Durable async execution is implemented through Celery; distributed job persistence beyond broker/result backend defaults is not yet implemented.

## Documentation

Start with the documentation index:

- docs/00_INDEX.md

Detailed implementation docs are in the docs folder:

- docs/01_SYSTEM_OVERVIEW.md
- docs/02_API_AND_RUNTIME_FLOWS.md
- docs/03_DATABASE_AND_MIGRATIONS.md
- docs/04_OPERATIONS_TESTING_AND_HANDOFF.md

## Week 9 Frontend App

- Folder: ../erp-web
- Run:
   - npm install
   - npm run dev
- Build:
   - npm run build
