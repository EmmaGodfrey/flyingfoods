# Actor Catalogue

## Actor 1: Superadmin
- Description: Highest privilege operational and governance role.
- Responsibilities:
  - Cross-module administration.
  - Cross-branch oversight where supported.
  - Access to privileged procurement approvals and reporting.
- Permissions:
  - Included in all require_role-protected endpoints.
- Accessible Areas:
  - Auth profile, all inventory/procurement/sales/reports/search endpoints.
  - Audit logs with optional branch override.

## Actor 2: Admin
- Description: Senior operational role with broad access and some approval authority.
- Responsibilities:
  - Procurement approvals.
  - Audit investigation and reporting.
  - Operational support across branch domain.
- Permissions:
  - Most endpoints (inventory, procurement, sales, reports, audit, search).
  - Explicitly required for procurement approve endpoint.
- Accessible Areas:
  - Full backend modules except role-specific omissions not present in code.

## Actor 3: Manager
- Description: Branch-level manager handling day-to-day operations.
- Responsibilities:
  - Product and stock operations.
  - Sales operations including reversals.
  - Procurement drafting/submission and reporting.
- Permissions:
  - Broad access to inventory/procurement/sales/reports/audit/search.
  - Cannot approve purchase orders unless admin/superadmin.
  - Audit access limited to own branch scope.
- Accessible Areas:
  - Most business endpoints with branch-scoped data.

## Actor 4: Inventory Officer
- Description: Operational role focused on stock and procurement execution.
- Responsibilities:
  - Product updates and stock movement recording.
  - Procurement listing and goods receipt recording.
- Permissions:
  - Inventory create/update/movement.
  - Procurement order listing, supplier listing, GRN creation.
  - Search access.
- Accessible Areas:
  - Inventory and selected procurement/search endpoints.

## Actor 5: Cashier
- Description: Point-of-sale operator.
- Responsibilities:
  - Create sales and retrieve receipts/summaries.
  - Initiate void/refund and payment reconciliation contract flows.
  - Record stock movement (current policy includes cashier).
- Permissions:
  - Sales endpoints including async reconciliation status.
  - Inventory movement create.
  - Search access.
- Accessible Areas:
  - POS and selected inventory/search.

## Actor 6: End User (Web SPA User)
- Description: Any authenticated frontend user (UI does not enforce role-specific navigation filtering).
- Responsibilities:
  - Operate available UI tabs (dashboard/products/movements/pos/procurement/reports/settings).
- Permissions:
  - Determined server-side by JWT role; UI does not implement per-role feature hiding.
- Accessible Areas:
  - Frontend routes after login; backend may reject unauthorized actions.

## Actor 7: Auditor (Functional Persona)
- Description: Audit reviewer persona (implemented as admin/manager role in code).
- Responsibilities:
  - Query immutable audit logs with filters.
  - Investigate action/entity/request traces.
- Permissions:
  - Through /audit/logs with branch-scope rules.
- Accessible Areas:
  - Audit endpoint and related reporting context.

## Actor 8: External System - Redis
- Description: Cache and metadata store integration.
- Responsibilities:
  - Refresh token revocation keys.
  - Stock cache keys.
  - Async job/report metadata cache keys.
- Permissions:
  - Service-level dependency, not human RBAC.
- Accessible Areas:
  - Auth, inventory, reporting, sales async status flows.

## Actor 9: External System - RabbitMQ/Celery Worker
- Description: Async job execution subsystem.
- Responsibilities:
  - Payment reconciliation task execution.
  - Search index and report task execution.
- Permissions:
  - Internal service execution rights.
- Accessible Areas:
  - app.tasks modules and result backend flow.

## Actor 10: External System - Elasticsearch
- Description: Search index backend (optional).
- Responsibilities:
  - Index and query global search documents.
  - Provide highlight fragments.
- Permissions:
  - Service-level connector.
- Accessible Areas:
  - Search indexing/tasks and search service query path.

## Actor 11: External System - Prometheus/Grafana/Alertmanager
- Description: Monitoring and alerting stack.
- Responsibilities:
  - Scrape /metrics and evaluate alert rules.
  - Visualize telemetry and route alerts.
- Permissions:
  - Infrastructure-level read of metric endpoint.
- Accessible Areas:
  - Monitoring endpoint and monitoring configuration files.

## Actor 12: API Consumer (Third-Party Integration)
- Description: Any non-frontend client using HTTP API.
- Responsibilities:
  - Call authenticated API workflows programmatically.
- Permissions:
  - JWT role-dependent.
- Accessible Areas:
  - Same API surface as frontend, including websocket connection.
