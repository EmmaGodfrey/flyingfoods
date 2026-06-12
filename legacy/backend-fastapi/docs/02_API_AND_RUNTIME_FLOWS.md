# ERP Backend Documentation - API and Runtime Flows

## 1. Auth Endpoints

### POST /auth/login
Input:
- email
- password

Flow:
1. Query user by email.
2. Verify user active status.
3. Verify password hash.
4. Issue access token and refresh token.
5. Store refresh jti in Redis with TTL.

Output:
- access_token
- refresh_token
- token_type
- access_expires_in
- refresh_expires_in

### POST /auth/refresh
Input:
- refresh_token

Flow:
1. Decode token and require type=refresh.
2. Validate jti exists in Redis.
3. Delete old jti (rotation).
4. Re-issue access/refresh pair.

### GET /auth/me
Flow:
1. Parse bearer token.
2. Decode JWT and require type=access.
3. Load current user and require active.
4. Return current user profile.

## 2. Inventory Endpoints

### GET /inventory/products
Purpose:
- Branch-scoped product listing.

Filters:
- limit/offset pagination
- search by product name
- optional category_id

### POST /inventory/products
Purpose:
- Create product in current branch.

Role:
- superadmin, admin, manager, inventory_officer

Write side effects:
1. Product row is inserted.
2. inventory.write.v1 event is published.
3. Audit handler appends immutable audit log row.
4. Cache invalidation handler clears branch stock snapshot key.

### GET /inventory/products/{product_id}
Purpose:
- Read a single product scoped to current branch.

### PUT /inventory/products/{product_id}
Purpose:
- Update product fields.

Role:
- superadmin, admin, manager, inventory_officer

Write side effects:
1. Product row is updated.
2. inventory.write.v1 event is published with before/after payload.
3. Audit handler appends immutable audit log row.
4. Cache invalidation handler clears branch stock snapshot key.

### DELETE /inventory/products/{product_id}
Purpose:
- Delete product if no blocking references.

Role:
- superadmin, admin, manager

Write side effects:
1. Product row is deleted.
2. inventory.write.v1 event is published.
3. Audit handler appends immutable audit log row.
4. Cache invalidation handler clears branch stock snapshot key.

### POST /inventory/movements
Purpose:
- Append a stock movement record.

Role:
- superadmin, admin, manager, inventory_officer, cashier

Flow:
1. Validate product exists in current branch.
2. Insert new movement record.
3. Publish inventory.write.v1 event.
4. Audit handler appends immutable audit log row.
5. Cache invalidation handler clears branch stock snapshot key.

### GET /inventory/movements
Purpose:
- Query stock movement history for inventory UI views.

Filters:
- limit/offset pagination
- product_id
- movement_type (receive/sale/waste/adjustment)
- occurred_after
- occurred_before

Behavior:
- Branch-scoped query only.
- Ordered by created_at DESC, id DESC for deterministic pagination.
- Response includes created_at for timeline tables and date filtering.

### GET /audit/logs
Purpose:
- Query immutable audit records with branch-safe filtering.

Role:
- superadmin, admin, manager

Filters:
- branch_id (restricted by role and branch scope)
- actor_user_id
- action
- entity_type
- entity_id
- occurred_after
- occurred_before

Behavior:
- Ordered by occurred_at desc, id desc.
- Supports limit/offset pagination.
- Non-elevated roles cannot query cross-branch data.

### GET /inventory/stock/current
Purpose:
- Return computed stock from stock movement sums.

Behavior:
- If product_id omitted, may return Redis-cached branch snapshot (TTL 60s).
- If cache miss, query DB, return and populate cache.

### GET /inventory/stock/low
Purpose:
- Return branch products where computed stock < reorder_level.

## 3. Sales/POS Endpoints

### POST /sales
Purpose:
- Create a sale transaction for the current branch.

Role:
- superadmin, admin, manager, cashier

Flow:
1. Normalize and aggregate requested line items by product.
2. Validate all products exist in current branch.
3. Expand BOM requirements when product has ingredients.
4. Validate computed stock sufficiency for affected ingredient/product rows.
5. Insert sale + sale_line_items.
6. Append stock_movements with movement_type=sale and reference `sale:{id}`.
7. Publish inventory.write.v1 event with action `sale.create`.
8. Existing handlers append immutable audit row and invalidate branch stock cache key.

### GET /sales/{sale_id}/receipt
Purpose:
- Return receipt payload for a branch-scoped sale.

Behavior:
- 404 when sale does not exist in current branch.

### GET /sales/summary/daily
Purpose:
- Return branch-scoped daily aggregates.

Behavior:
- Filters by UTC day window.
- Returns total sales_count, gross_total, and payment_method_totals.

### POST /sales/{sale_id}/void
Purpose:
- Reverse stock effects for an already completed sale and mark it voided.

Behavior:
- Branch-scoped sale lookup.
- Rejects duplicate void attempts.
- Produces adjustment stock movements and publishes sale.void audit event through inventory.write.v1.

### POST /sales/{sale_id}/refund
Purpose:
- Reverse stock effects for an already completed sale and mark it refunded.

Behavior:
- Branch-scoped sale lookup.
- Rejects duplicate refunds.
- Rejects refund when sale is not in completed status (for example, already voided).
- Produces adjustment stock movements and publishes sale.refund audit event through inventory.write.v1.

### POST /sales/{sale_id}/payments/intent
Purpose:
- Resolve provider-eligible tenders and create payment authorization contracts.

Behavior:
- Branch-scoped sale lookup.
- Authorizes card/mobile tenders through provider abstraction.
- Returns tender-level provider references for follow-up reconciliation.

### POST /sales/{sale_id}/payments/reconcile
Purpose:
- Run immediate payment reconciliation against provider abstraction.

Behavior:
- Branch-scoped sale lookup.
- Validates provider reference against sale context.
- Returns reconciled amount and timestamp when successful.

### POST /sales/{sale_id}/payments/reconcile/async
Purpose:
- Enqueue asynchronous reconciliation work for a sale/provider reference.

Behavior:
- Branch-scoped sale lookup.
- Dispatches Celery task with queued status contract.
- Returns job ID for polling.

### GET /sales/{sale_id}/payments/reconcile/jobs/{job_id}
Purpose:
- Poll asynchronous reconciliation status/result.

Behavior:
- Branch-scoped sale lookup.
- Returns queued/running/succeeded/failed status and result or error payload.

## 3A. Procurement Endpoints

### POST /procurement/orders
Purpose:
- Create a draft purchase order in the current branch.

Role:
- superadmin, admin, manager

Flow:
1. Validate supplier belongs to current branch.
2. Validate all requested products belong to current branch.
3. Insert purchase_order and purchase_order_line_items.
4. Append immutable audit row for purchase_order.create.

### GET /procurement/orders
Purpose:
- List branch-scoped purchase orders with status, supplier, and date filters.

### PUT /procurement/orders/{purchase_order_id}/submit
Purpose:
- Move draft purchase order to submitted state.

Role:
- superadmin, admin, manager

### PUT /procurement/orders/{purchase_order_id}/approve
Purpose:
- Approve a submitted purchase order.

Role:
- superadmin, admin

### POST /procurement/grn
Purpose:
- Record a goods received note against an approved purchase order.

Role:
- superadmin, admin, manager, inventory_officer

Flow:
1. Validate purchase order belongs to current branch and is approved or partially received.
2. Validate cumulative received quantity does not exceed ordered quantity.
3. Insert goods_received_note and receipt line items.
4. Append stock_movements with movement_type=receive and reference `grn:{id}`.
5. Publish inventory.write.v1 events for each receipt movement.
6. Existing handlers append immutable audit rows and invalidate branch stock cache.

### GET /procurement/reports/orders
Purpose:
- Return paginated purchase order reporting with status, supplier, and date filters.

### GET /procurement/reports/spend
Purpose:
- Return supplier/month spend totals based on recorded goods receipts.

## 3B. Reporting Endpoints

### GET /reports/sales
Purpose:
- Branch-scoped line-level sales report with aggregate totals.

### GET /reports/sales/export/csv
Purpose:
- CSV export of the sales report contract.

### GET /reports/inventory/valuation
Purpose:
- Product valuation report using computed stock multiplied by product cost price.

### GET /reports/inventory/movements
Purpose:
- Filterable, paginated movement report for analytics and export views.

### GET /reports/procurement/spend
Purpose:
- Procurement spend report grouped by supplier and month.

### POST /reports/procurement/spend/async
Purpose:
- Enqueue asynchronous procurement spend report task.

### GET /reports/tasks/{task_id}/status
Purpose:
- Poll asynchronous report task result status with branch-scoped access.

## 3B. Live Dashboard WebSocket Endpoint

### WS /ws/dashboard?token=<access_token>
Purpose:
- Provide branch-scoped live dashboard updates.

Behavior:
- Authenticates with access token query parameter.
- Joins a branch-scoped connection group.
- Broadcasts `domain_event` messages for inventory/sales writes.
- Broadcasts `anomaly_alert` messages for sale void/refund actions.

## 4. Dependency and Guard Flow

### get_current_user
- Reads bearer token.
- Decodes JWT.
- Resolves user from DB.
- Rejects missing/invalid/inactive users.

### require_role
- Wraps current user dependency.
- Rejects roles outside allowed set with HTTP 403.

### get_current_branch
- Returns branch_id from current user context.

## 5. Cache Behavior

Key format:
- inventory:stock:branch:{branch_id}

Write invalidation:
- Called through inventory.write.v1 handlers after inventory and sales write events.

Read population:
- Called on stock/current with no product_id filter.

## 6. In-Process Event Bus

Current components:
- DomainEvent envelope
- InProcessEventBus subscribe/publish
- inventory_events handler registration at app startup

Current usage:
1. Inventory write publishes inventory.write.v1 event.
2. Audit handler writes immutable log.
3. Cache invalidation handler clears stock cache.
4. Sales create also publishes inventory.write.v1 (`sale.create`) and reuses the same handlers.

## 7. Error Handling Patterns
- IntegrityError during writes -> converted to HTTP 400 or 409.
- Missing branch-scoped entity -> HTTP 404.
- Sale validation failures (for example insufficient stock) -> HTTP 400.
- Token errors -> HTTP 401.
- Role violations -> HTTP 403.

## 8. Contract Notes
- Product and movement responses are schema-driven via Pydantic models.
- Decimal fields are preserved for monetary/quantity precision.
- Branch isolation is expected in every query path as a non-optional constraint.

## 9. Stage 6 Verified Guarantees
- Inventory write endpoints create corresponding audit records through inventory.write.v1 events.
- Non-elevated audit queries cannot access cross-branch logs.
- Audit log listing order is deterministic: occurred_at DESC then id DESC, with stable limit/offset behavior.

## 10. Stage 7 Observability Guarantees
- Inventory write publish path emits structured logs with request_id, correlation_id, branch_id, actor_user_id.
- Event bus tracks:
	- event_publish_total
	- event_publish_duplicates_total
	- event_handler_success_total
	- event_handler_failures_total
	- event_publish_duration_ms
	- event_handler_duration_ms
- Audit query path tracks:
	- audit_query_requests_total
	- audit_query_denied_total
	- audit_query_latency_ms

## 11. Stage 9 UI Contract Guarantees
- Inventory UI can call movement history endpoint (`GET /inventory/movements`) with type/date filters.
- Product list + computed stock (`GET /inventory/products` + `GET /inventory/stock/current`) support status badge rendering in UI.
- Receive stock flow is supported by `POST /inventory/movements` and immediate stock refresh calls.

## 12. Stage 10 POS Contract Guarantees
- POS checkout is supported by `POST /sales` with branch-scoped validation.
- Receipt view is supported by `GET /sales/{id}/receipt`.
- Daily summary panel polling is supported by `GET /sales/summary/daily`.
- Sales writes preserve existing audit append-only and stock cache invalidation behavior via shared event bus wiring.

## 13. Stage 11 Reversal Contract Guarantees
- Sale void is supported by `POST /sales/{id}/void` with branch-scoped guards and duplicate-void rejection.
- Sale refund is supported by `POST /sales/{id}/refund` with branch-scoped guards, duplicate-refund rejection, and status compatibility checks.
- Both reversal writes preserve existing audit append-only and stock cache invalidation behavior via shared event bus wiring.

## 14. Stage 13 Payment Contract Guarantees
- Payment intent is supported by `POST /sales/{id}/payments/intent` for provider-eligible tenders.
- Immediate reconciliation is supported by `POST /sales/{id}/payments/reconcile`.
- Payment endpoints are branch-scoped and do not mutate inventory or audit append flows.

## 15. Stage 14 Reconciliation Ops Guarantees
- Async reconciliation enqueue is supported by `POST /sales/{id}/payments/reconcile/async`.
- Async status polling is supported by `GET /sales/{id}/payments/reconcile/jobs/{job_id}`.
- Observability tracks enqueue/start/success/failure counters and async latency histogram.
- Failure metrics include reason labels to isolate reference-mismatch vs generic provider errors.

## 16. Stage 15 Durable Async Guarantees
- Async reconciliation execution is dispatched to Celery worker tasks.
- Broker/backend wiring supports RabbitMQ (broker) and Redis (result backend).
- Job status polling remains branch-scoped and returns queued/running/succeeded/failed states.
- Durable execution path no longer relies on in-process task scheduling.

## 17. Stage 16 Reporting Guarantees
- Reporting endpoints are branch-scoped and manager-role protected.
- Sales reporting supports both JSON and CSV contracts with consistent filtering.
- Inventory valuation and movement reporting contracts are available for operational analytics.
- Procurement spend reporting supports synchronous retrieval and async task status polling.

## 18. Stage 17 Live Dashboard Guarantees
- WebSocket clients receive branch-scoped domain event broadcasts for inventory/sales write actions.
- Connection lifecycle supports heartbeat ping/pong.
- Live anomaly alerts are broadcast for sale.void and sale.refund actions.

## 19. Not Implemented Yet
- Tax/discount rules and split tenders are implemented in the POS sale contract.
- Real payment provider integrations are not implemented.
- Durable job retry/backoff policy and dead-letter handling are not yet implemented.
