# Research: Flying Foods Restaurant & Inventory Management System

**Date**: 2026-06-12. All Technical Context items were resolved by user decision or BRD content; research below records the reasoning for each non-obvious choice. No NEEDS CLARIFICATION markers remain.

## Decisions

### 1. Backend rebuild in Django vs port of FastAPI code

- **Decision**: Fresh Django 5 + DRF project. The superseded FastAPI
  prototype was removed once the replacement workflows were established.
- **Rationale**: ~80% of BRD functionality does not exist in the old code; porting ~4.7k lines of async SQLAlchemy buys the remaining ~20% at high translation cost, then fights Django idioms forever. Greenfield with the old code as a behavioral reference is faster and yields one consistent codebase. User approved 2026-06-12.
- **Alternatives considered**: (a) port models/services first then extend — rejected: double work, mixed idioms; (b) keep FastAPI — rejected: violates the Django requirement.

### 2. Stock correctness model

- **Decision**: Append-only `StockMovement` ledger + per-(product, location) `StockBalance` cache updated in-transaction under `select_for_update()`.
- **Rationale**: BRD audit NFR ("every transaction logged... before/after") and the anti-leakage business goal demand forensic traceability; deriving on-hand from movements makes untraceable balance changes structurally impossible (SC-002). Balance cache avoids O(movements) reads on hot paths.
- **Alternatives considered**: mutable balance column with audit trail — rejected: audit can drift from balance; event-sourcing framework — rejected: overkill for restaurant scale.

### 3. Pastel + email delivery guarantees

- **Decision**: Transactional outbox (`OutboxRecord` in same transaction as movement) drained by Celery; per-attempt `PastelSyncLog`; exponential backoff via Celery `retry_backoff`; manual re-send endpoint.
- **Rationale**: FR-PA-01..05 and SC-008 (zero loss/zero duplicates across an outage) cannot be met with fire-and-forget tasks — a crash between commit and task enqueue loses the movement. Outbox closes that gap with one extra table.
- **Alternatives considered**: Celery task enqueued after commit (`transaction.on_commit`) — rejected: loses task if worker/broker down at commit time, no durable record; CDC/Debezium — rejected: infrastructure overkill.

### 4. Real-time kitchen/waiter updates

- **Decision**: Django Channels (Redis layer), notification-only sockets; clients refetch through React Query invalidation.
- **Rationale**: FR-KD-01/5-second NFR needs push, not polling. Keeping sockets dumb (signal "order changed", client refetches REST) avoids dual-write of payload schemas and keeps REST the single source of truth.
- **Alternatives considered**: SSE — workable but Channels also serves future needs and integrates with Django auth; 2-second polling — meets 5 s on paper but wastes tablet battery/bandwidth and degrades under load.

### 5. JWT/session handling

- **Decision**: djangorestframework-simplejwt; 15-min access in Zustand memory, 7-day rotating refresh in httpOnly cookie, blacklist-after-rotation, logout blocklist in Redis.
- **Rationale**: Matches project style guide verbatim; rotation + blocklist satisfies the security NFR.
- **Alternatives considered**: Django sessions for SPA — rejected: style guide mandates JWT for the SPA (sessions stay for Django admin only).

### 6. PDF and Excel generation

- **Decision**: weasyprint (HTML→PDF) for POs and report prints; openpyxl for Excel.
- **Rationale**: FR-PR-05 (PO PDF) and FR-RP-09 (all reports → PDF + Excel). HTML templates reuse Django templating; weasyprint handles tables/page headers well. openpyxl is the boring standard for xlsx.
- **Alternatives considered**: reportlab — rejected: imperative layout slows iteration on ~10 report layouts; LibreOffice headless — rejected: heavyweight runtime dependency. Note: weasyprint needs Pango/GTK libs in the Docker image — handled in the backend Dockerfile.

### 7. Supplier email + dev mail testing

- **Decision**: Django email backend (SMTP, decouple-configured) + mailpit container in docker-compose for dev; send result logged on the PO record; bounce capture where the gateway reports it.
- **Rationale**: FR-PR-05/06 and BRD §3.3. Mailpit gives the team a visual inbox to verify PO PDFs without sending real mail.
- **Alternatives considered**: third-party API (SendGrid etc.) — deferred to deployment decision; the abstraction is Django's email backend either way.

### 8. POS integration mode (BRD decision pending)

- **Decision**: One internal ingestion endpoint (`POST /api/pos/sale-events/`) used by both paths: push (POS calls it) and pull (Celery poller/file importer calls it). Mode + endpoint configurable in integration settings.
- **Rationale**: BRD §3.1 explicitly mandates building so either option plugs in; dedupe by `pos_sale_id` makes overlap of both paths safe.

### 9. Pastel sync mode (BRD decision pending)

- **Decision**: All three modes implemented behind one config flag; default real-time-with-retry, recommended fallback daily batch — per BRD §3.2 recommendation.

### 10. Offline tolerance scope

- **Decision**: Server runs LAN-local (BRD assumes devices on local network), so POS→kitchen survives internet outages by construction. Frontend additionally queues kitchen/waiter status mutations (Zustand persist + idempotency keys) to ride out brief server/Wi-Fi blips. Full offline-first (service worker, local DB) is **not** in scope.
- **Rationale**: NFR asks screens stay usable during *short internet outages*, not disconnected operation. The BRD's own availability framing (sync resumes when connectivity returns) is satisfied by LAN deployment + action queue at far lower complexity than a service-worker architecture.
- **Alternatives considered**: full PWA offline-first — rejected for v1: large complexity, BRD doesn't require it; revisit if field reality differs.

### 11. Reports architecture

- **Decision**: `reports` app holds one selector per report (pure read queries, `values()`/`annotate()`), one exporter service with PDF/Excel renderers, DRF endpoints paginated; heavy exports run as Celery tasks returning a download when scale demands (deferred until needed).
- **Rationale**: FR-RP-01..09 + style-guide rules (annotate not Python loops, pagination everywhere).

### 12. Test strategy

- **Decision**: pytest-django + factory_boy; per-app `tests/` with `test_views`
  (APIClient: happy/401/403/400), `test_services` (posting, approvals, outbox),
  and factories. Frontend: Vitest + RTL + MSW for new features. CI: GitHub
  Actions with separate backend and frontend jobs.
- **Rationale**: Style guide testing section verbatim; critical-path focus (ledger, approvals, ingestion dedupe, outbox) per "test the right things".
