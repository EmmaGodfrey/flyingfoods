# Gap Analysis Report

## Implemented Features
- JWT auth/login/refresh/me.
- Role-gated API modules for inventory/procurement/sales/reports/audit/search.
- Branch-scoped data model with migrations and constraints.
- Event-driven audit/cache/websocket fan-out for inventory.write domain events.
- POS sales with BOM depletion, tax/discount, split tenders, void/refund.
- Payment provider abstraction (simulated), sync and async reconciliation contracts.
- Procurement PO lifecycle and GRN stock posting.
- Reporting APIs including async spend report task status.
- Search via Elasticsearch with DB fallback.
- Monitoring endpoint and alert rules.
- Week-by-week test suite covering key contracts through week 17.

## Missing/Partial Features
1. Real payment gateway integration (simulated provider only).
2. Durable, strongly consistent job metadata persistence independent of process memory.
3. Dedicated auditor/end-user RBAC roles beyond operational set.
4. Fine-grained permission model (action/attribute-level) beyond role string checks.
5. Reports and settings frontend sections are shell pages.
6. Native UI role-aware route/action hiding.
7. Explicit distributed locking/serialization strategy for high-contention stock updates.
8. Production guardrails for insecure defaults (JWT secret fallback).

## Testable Features
- All listed API endpoints are testable via HTTP clients.
- Websocket event flow testable using TestClient websocket sessions.
- Async task flows testable in eager mode and broker mode.
- DB constraints testable through migration + model operations.

## High-Risk Areas
- Auth/session security when Redis unavailable.
- Async metadata durability and status consistency across restarts.
- Financial reconciliation reliability in production provider integration (currently simulated).
- Inventory/procurement race conditions under concurrent writes.

## Recommended Test Priority
### Critical
- Auth token replay prevention in degraded infra.
- Sale creation/void/refund stock integrity.
- PO approval + GRN over-receipt prevention.
- Branch isolation tests across all modules.

### High
- Async reconcile/report status consistency under restarts.
- Audit append-only enforcement on PostgreSQL.
- Permission boundary tests for every role and endpoint.

### Medium
- Search relevance and fallback correctness under ES outages.
- Report aggregation boundary filters and CSV formatting.

### Low
- UI shell pages behavior and user guidance text.

## Coverage Summary
- Good automated coverage exists for core week 3-17 milestones.
- Residual gaps are mostly production-hardening, role granularity, and non-functional robustness at scale.
