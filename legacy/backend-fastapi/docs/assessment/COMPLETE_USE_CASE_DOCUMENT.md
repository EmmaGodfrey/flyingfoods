# Complete Use Case Document

## Scope Note
This document enumerates use cases directly evidenced by API routes and frontend workflows in this workspace.

## UC-01 Login
- Actor: Superadmin/Admin/Manager/Inventory Officer/Cashier/API Consumer
- Description: Authenticate with email/password and receive access/refresh tokens.
- Preconditions: User exists, is_active true, correct password hash.
- Trigger: POST /auth/login.
- Main Success Flow:
  1. Submit email and password.
  2. System verifies user and password.
  3. System issues access + refresh tokens.
- Alternative Flows: None.
- Error Flows: Invalid credentials -> 401.
- Postconditions: Client holds token pair.
- Business Rules: Password min length 8 in schema.
- Security Considerations: JWT secret hygiene; brute-force protections not implemented in code.

## UC-02 Refresh Session
- Actor: Authenticated API Consumer
- Description: Rotate refresh token and mint new token pair.
- Preconditions: Valid refresh token; user still active.
- Trigger: POST /auth/refresh.
- Main Success Flow:
  1. Submit refresh token.
  2. System validates token type and revocation key (if Redis available).
  3. System rotates token and returns new pair.
- Alternative Flows: Redis unavailable path skips revocation check.
- Error Flows: Invalid token/replayed token -> 401.
- Postconditions: New token pair returned.
- Business Rules: Refresh token JTI tracked in Redis when available.
- Security Considerations: Revocation enforcement depends on Redis availability.

## UC-03 Get Current User
- Actor: Authenticated User
- Description: Retrieve own user profile context.
- Preconditions: Valid access token.
- Trigger: GET /auth/me.
- Main Success Flow: Validate token -> fetch user -> return profile.
- Alternative Flows: None.
- Error Flows: Missing/invalid token, inactive user -> 401.
- Postconditions: None.
- Business Rules: Access token type must equal access.
- Security Considerations: Depends on strict token verification.

## UC-04 List Products
- Actor: Any authenticated role
- Description: Retrieve branch-scoped product list with pagination/filter.
- Preconditions: Valid access token.
- Trigger: GET /inventory/products.
- Main Success Flow: Apply branch + optional search/category filters -> return list and total.
- Alternative Flows: Empty result set allowed.
- Error Flows: Validation errors on query constraints.
- Postconditions: None.
- Business Rules: limit 1..200, offset >= 0.
- Security Considerations: Branch is derived from token user context.

## UC-05 Create/Update/Delete Product
- Actor: Superadmin/Admin/Manager/Inventory Officer (delete excludes inventory_officer)
- Description: Maintain product master data.
- Preconditions: Role allowed; valid references (unit/category/supplier).
- Trigger: POST/PUT/DELETE product endpoints.
- Main Success Flow:
  1. Validate role + payload.
  2. Persist mutation.
  3. Publish inventory.write event.
  4. Write audit via event handler.
  5. Invalidate stock cache and update search index.
- Alternative Flows: Integrity conflict mapped to 400/409.
- Error Flows: Missing product -> 404.
- Postconditions: Product state changed.
- Business Rules: Branch-scoped data; FK constraints enforce integrity.
- Security Considerations: Event handler failures are isolated but logged.

## UC-06 Record Stock Movement
- Actor: Superadmin/Admin/Manager/Inventory Officer/Cashier
- Description: Append stock movement entry.
- Preconditions: Product exists in branch.
- Trigger: POST /inventory/movements.
- Main Success Flow: Validate payload -> insert movement -> publish event/audit/cache invalidation.
- Alternative Flows: None.
- Error Flows: Product not found in branch -> 404.
- Postconditions: Stock ledger updated.
- Business Rules: movement_type limited by enum.
- Security Considerations: Write action audited and branch-scoped.

## UC-07 Query Movement History/Stock/Low Stock
- Actor: Authenticated users (no explicit role gate for history/stock endpoints)
- Description: Analyze stock history and current state.
- Preconditions: Valid token.
- Trigger: GET movement/current/low endpoints.
- Main Success Flow: Apply filters and return computed state.
- Alternative Flows: Cache hit for current stock summary.
- Error Flows: Invalid date format or invalid movement_type -> 400.
- Postconditions: None.
- Business Rules: Query limits and date parsing constraints.
- Security Considerations: Branch filtering enforced in query layer.

## UC-08 Create Supplier
- Actor: Superadmin/Admin/Manager
- Description: Add procurement supplier record.
- Preconditions: Authorized role.
- Trigger: POST /procurement/suppliers.
- Main Success Flow: Persist supplier -> index supplier doc.
- Alternative Flows: None.
- Error Flows: Validation or unique violation from DB.
- Postconditions: Supplier available for PO workflow.
- Business Rules: Branch-scoped unique supplier names via DB constraint.
- Security Considerations: Server-side role checks only.

## UC-09 Update/Delete Supplier
- Actor: Superadmin/Admin/Manager
- Description: Maintain supplier records.
- Preconditions: Supplier exists in current branch.
- Trigger: PUT/DELETE supplier endpoints.
- Main Success Flow: Fetch by branch -> mutate/delete -> update search index.
- Alternative Flows: None.
- Error Flows: Supplier not found -> 404.
- Postconditions: Supplier changed or removed.
- Business Rules: Branch isolation strictly applied.
- Security Considerations: Prevents cross-branch enumeration by keyed lookup.

## UC-10 Create Purchase Order
- Actor: Superadmin/Admin/Manager
- Description: Create PO in draft with line items.
- Preconditions: Supplier + products in branch.
- Trigger: POST /procurement/orders.
- Main Success Flow: Validate refs -> create PO + lines -> audit write.
- Alternative Flows: None.
- Error Flows: Validation/not found/conflict mapped to 400/404/409.
- Postconditions: PO status draft.
- Business Rules: At least one line item, positive quantity.
- Security Considerations: Branch context from token.

## UC-11 Submit Purchase Order
- Actor: Superadmin/Admin/Manager
- Description: Move PO from draft to submitted.
- Preconditions: PO exists in branch and status draft.
- Trigger: PUT /procurement/orders/{id}/submit.
- Main Success Flow: Update status and submitted metadata -> audit.
- Alternative Flows: None.
- Error Flows: Wrong status -> 409.
- Postconditions: PO submitted.
- Business Rules: Only draft can be submitted.
- Security Considerations: Branch-scoped lookup.

## UC-12 Approve Purchase Order
- Actor: Superadmin/Admin
- Description: Approve submitted PO.
- Preconditions: Status submitted.
- Trigger: PUT /procurement/orders/{id}/approve.
- Main Success Flow: Set approved status/timestamps -> audit.
- Alternative Flows: None.
- Error Flows: Wrong status -> 409.
- Postconditions: PO approved.
- Business Rules: Approval role is stricter than submit role.
- Security Considerations: Explicit role gate prevents manager approval.

## UC-13 Create GRN (Receive Goods)
- Actor: Superadmin/Admin/Manager/Inventory Officer
- Description: Post goods receipt against approved/received PO.
- Preconditions: PO status approved or received; line quantities valid.
- Trigger: POST /procurement/grn.
- Main Success Flow:
  1. Validate PO and line references.
  2. Validate no over-receipt.
  3. Insert GRN + GRN lines + receive stock movements.
  4. Update PO status to received or closed.
  5. Audit and publish stock receipt events.
- Alternative Flows: Partial receive keeps PO in received.
- Error Flows: Over-receipt or bad line id -> 400.
- Postconditions: Stock increased; PO lifecycle advanced.
- Business Rules: received_quantity must not exceed ordered quantity.
- Security Considerations: Audited and branch-scoped.

## UC-14 Create Sale (POS Checkout)
- Actor: Superadmin/Admin/Manager/Cashier
- Description: Create completed sale with tax/discount/tender contract.
- Preconditions: Products exist and stock sufficient.
- Trigger: POST /sales.
- Main Success Flow:
  1. Normalize quantities.
  2. Resolve products and BOM ingredients.
  3. Validate available stock from stock_movements aggregate.
  4. Calculate subtotal/tax/discount/total.
  5. Validate tender rules.
  6. Insert sale, line_items, stock deductions.
  7. Publish event, audit, index invoice, invalidate stock cache.
- Alternative Flows: Split tender path.
- Error Flows: Insufficient stock -> 400; missing product -> 404; invalid tenders -> 400.
- Postconditions: Sale and inventory deltas committed.
- Business Rules: Total cannot be negative; split tender sum must equal total.
- Security Considerations: Role gated and branch-scoped.

## UC-15 Get Receipt And Daily Summary
- Actor: Superadmin/Admin/Manager/Cashier
- Description: Access sale receipt and daily aggregate summary.
- Preconditions: Sale exists in branch.
- Trigger: GET receipt/summary endpoints.
- Main Success Flow: Query branch-scoped sale(s), return response.
- Alternative Flows: business_date query optional.
- Error Flows: Sale not found -> 404.
- Postconditions: None.
- Business Rules: Daily summary based on UTC day range.
- Security Considerations: Branch scope enforced in query predicates.

## UC-16 Void Sale
- Actor: Superadmin/Admin/Manager/Cashier
- Description: Reverse sale operationally by creating adjustment movements.
- Preconditions: Sale exists and not already voided.
- Trigger: POST /sales/{id}/void.
- Main Success Flow: Validate status -> create reversal stock movements -> set void metadata -> audit/event.
- Alternative Flows: None.
- Error Flows: Already voided -> 400; not found -> 404.
- Postconditions: Sale status voided; stock restored.
- Business Rules: Requires reason text.
- Security Considerations: Emits anomaly_alert websocket event.

## UC-17 Refund Sale
- Actor: Superadmin/Admin/Manager/Cashier
- Description: Refund completed sale and reverse inventory.
- Preconditions: Sale status completed and not refunded.
- Trigger: POST /sales/{id}/refund.
- Main Success Flow: Validate status -> reversal movements -> set refund metadata -> audit/event.
- Alternative Flows: None.
- Error Flows: Already refunded -> 400; invalid prior status -> 400; not found -> 404.
- Postconditions: Sale status refunded; stock restored.
- Business Rules: Cannot refund from voided state.
- Security Considerations: Emits anomaly_alert websocket event.

## UC-18 Payment Intent
- Actor: Superadmin/Admin/Manager/Cashier
- Description: Authorize provider-eligible tenders for sale.
- Preconditions: Sale exists; has non-cash tender amount.
- Trigger: POST /sales/{id}/payments/intent.
- Main Success Flow: Build provider request(s) and return authorization references.
- Alternative Flows: Multi-tender authorization list.
- Error Flows: No eligible tenders -> 400; sale not found -> 404.
- Postconditions: Authorization result returned (no DB write).
- Business Rules: Simulated provider only.
- Security Considerations: Provider reference must match sale context in later reconcile.

## UC-19 Payment Reconcile (Sync)
- Actor: Superadmin/Admin/Manager/Cashier
- Description: Reconcile sale payment reference synchronously.
- Preconditions: Valid provider reference and eligible digital total.
- Trigger: POST /sales/{id}/payments/reconcile.
- Main Success Flow: Validate sale + provider reference -> return reconciled result.
- Alternative Flows: None.
- Error Flows: Bad reference -> 400; sale not found -> 404.
- Postconditions: Reconciliation payload returned.
- Business Rules: Simulated provider contract.
- Security Considerations: Sale/branch context binding of reference prefix.

## UC-20 Payment Reconcile (Async + Status)
- Actor: Superadmin/Admin/Manager/Cashier
- Description: Queue reconciliation job and poll status.
- Preconditions: Sale exists and provider reference provided.
- Trigger: POST enqueue + GET job status.
- Main Success Flow:
  1. Enqueue Celery task.
  2. Persist metadata (Redis or in-memory fallback).
  3. Poll status until queued/running/succeeded/failed.
- Alternative Flows: Failure status with error text.
- Error Flows: Job not found/context mismatch -> 404.
- Postconditions: Final reconciliation result or failure returned.
- Business Rules: Metadata TTL path via Redis setex.
- Security Considerations: Branch + sale id matching enforced before status return.

## UC-21 Query Audit Logs
- Actor: Superadmin/Admin/Manager
- Description: Query immutable audit records with filters and pagination.
- Preconditions: Role authorized.
- Trigger: GET /audit/logs.
- Main Success Flow: Resolve allowed branch scope -> query filter set -> return ordered rows.
- Alternative Flows: Admin/superadmin can request explicit branch.
- Error Flows: Manager cross-branch request -> 403.
- Postconditions: None.
- Business Rules: order by occurred_at desc, id desc.
- Security Considerations: Cross-branch restriction for non-elevated roles.

## UC-22 Generate Reports
- Actor: Superadmin/Admin/Manager
- Description: Retrieve sales, inventory valuation/movements, procurement spend reports.
- Preconditions: Authorized role.
- Trigger: GET report endpoints.
- Main Success Flow: Query domain tables and aggregate rows.
- Alternative Flows: CSV export for sales.
- Error Flows: Invalid movement_type/date format -> 400.
- Postconditions: None.
- Business Rules: pagination and date filters applied.
- Security Considerations: Branch scope enforced.

## UC-23 Run Async Procurement Spend Report
- Actor: Superadmin/Admin/Manager
- Description: Enqueue async spend report generation and poll task status.
- Preconditions: Authorized role.
- Trigger: POST /reports/procurement/spend/async + GET /reports/tasks/{task_id}/status.
- Main Success Flow: enqueue task, store task meta, poll until completion.
- Alternative Flows: failed status with error.
- Error Flows: Missing/foreign task id -> 404.
- Postconditions: result payload available on success.
- Business Rules: Task metadata must map to requester branch.
- Security Considerations: Branch check before returning status payload.

## UC-24 Global Search
- Actor: Superadmin/Admin/Manager/Inventory Officer/Cashier
- Description: Search products/suppliers/invoices.
- Preconditions: q present and non-empty after trim.
- Trigger: GET /search?q=...
- Main Success Flow: Try Elasticsearch query; fallback to DB search if ES unavailable.
- Alternative Flows: Highlight fragments when ES path used.
- Error Flows: Empty normalized query -> 400.
- Postconditions: grouped response with total.
- Business Rules: limit per group default 8.
- Security Considerations: branch and is_active filters included in query paths.

## UC-25 Dashboard Websocket Session
- Actor: Authenticated client with access token
- Description: Receive real-time branch domain events and anomaly alerts.
- Preconditions: Valid access token in query string.
- Trigger: WS connect /ws/dashboard?token=...
- Main Success Flow: authenticate -> connect to branch channel -> receive events and ping/pong.
- Alternative Flows: idle ping every timeout interval.
- Error Flows: invalid/missing token -> websocket policy violation.
- Postconditions: live stream active while connection open.
- Business Rules: broadcasts are branch-scoped.
- Security Considerations: token in query string may leak in logs if not controlled.
