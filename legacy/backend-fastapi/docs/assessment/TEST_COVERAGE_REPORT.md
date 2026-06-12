# Test Coverage Report

## Covered Feature Areas (Implemented + Tested)
- Auth security primitives (hashing/JWT).
- Role dependency behavior.
- Health endpoint.
- Inventory model/service contracts.
- Audit hashing, branch scope, and integration.
- Procurement end-to-end flow and reports.
- Observability metrics and exporter semantics.
- Inventory UI API contract behavior.
- Sales POS creation/summary/receipt.
- Sale void and refund lifecycle controls.
- Supplier CRUD and branch scope.
- Sales pricing/tender contract validations.
- Payment intent and reconciliation contracts (sync + async).
- Reconciliation operations alert signal checks.
- Celery durable async task behavior.
- Search branch scoping and ES highlight path.
- Reporting APIs and async task status branch scoping.
- Websocket live dashboard event and anomaly alert flow.

## Testable But Under-Tested Areas
- Login brute-force/rate-limit behaviors.
- Invalid token edge matrix across all endpoints.
- Concurrency/race tests for stock and procurement writes.
- Production infrastructure failure drills (RabbitMQ/Redis/ES outages under load).
- CORS/security header verification.
- Full frontend component behavior tests (UI test suite not present in workspace).

## Missing Features Affecting Coverage
- Real payment gateway integration scenarios.
- Full reports/settings frontend modules.
- Dedicated auditor role pathway.

## High-Risk Areas
- Auth revocation degraded mode (Redis unavailable).
- Async metadata fallback durability.
- Financial/inventory race conditions at high concurrency.
- Secret/config hardening assumptions.

## Recommended Test Priority By Severity
### Critical
- Branch isolation and RBAC for every mutating endpoint.
- Sale/void/refund stock integrity under repeated operations.
- GRN over-receipt and PO status transition protections.
- Async reconcile/report status correctness across worker restarts.

### High
- Token refresh replay resistance with/without Redis.
- Audit append-only guarantees and hash-chain continuity checks.
- Search fallback correctness and response consistency.

### Medium
- CSV export formatting and date filter boundary behavior.
- Websocket ping/pong timeout behavior under network jitter.

### Low
- UI shell route acceptance checks and messaging consistency.
