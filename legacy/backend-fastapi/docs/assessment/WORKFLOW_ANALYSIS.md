# Workflow Analysis

## WF-01 Product Lifecycle
- Starting Point: Product create request.
- Ending Point: Product persisted and searchable.
- Actors: Admin/Manager/Inventory Officer/API.
- Data: products, audit_logs, search documents.
- Decision Points:
  - Role authorized?
  - FK references valid?
- Failure Points:
  - IntegrityError on duplicate/invalid refs.
- Approval Stages: None.
- Notifications Triggered: websocket domain_event broadcast.

Text Diagram:
[Create Product] -> [Validate Role/Payload] -> [DB Commit] -> [Publish inventory.write] -> [Audit Log + Cache Invalidate + WS Broadcast + Search Index]

## WF-02 Stock Movement Recording
- Starting Point: Movement create request.
- Ending Point: Movement appended and stock cache invalidated.
- Actors: Admin/Manager/Inventory Officer/Cashier.
- Data: stock_movements, audit_logs, cache key.
- Decision Points: Product exists in branch?
- Failure Points: Product not found.
- Approval Stages: None.
- Notifications Triggered: websocket domain_event.

Text Diagram:
[Create Movement] -> [Validate Product] -> [Insert Movement] -> [Publish inventory.write] -> [Audit + Cache Delete + WS]

## WF-03 Purchase Order Workflow
- Starting Point: PO draft creation.
- Ending Point: PO submitted/approved/received/closed.
- Actors: Manager/Admin/Superadmin/Inventory Officer.
- Data: purchase_orders, line_items, GRNs, stock_movements, audit_logs.
- Decision Points:
  - Draft before submit?
  - Submitted before approve?
  - GRN qty <= ordered qty?
  - Full receipt closes order?
- Failure Points:
  - Invalid status transitions.
  - Over-receipt validation.
- Approval Stages: Approve stage requires admin/superadmin.
- Notifications Triggered: stock receipt emits inventory.write events.

Text Diagram:
[Create PO(draft)] -> [Submit] -> [Approve] -> [Create GRN] -> [Update received qty] -> {All lines received?}
Yes -> [Close PO]
No -> [Mark received]

## WF-04 POS Checkout Workflow
- Starting Point: Sale create request.
- Ending Point: Sale completed with stock depletion and receipt.
- Actors: Cashier/Manager/Admin/Superadmin.
- Data: sales, sale_line_items, stock_movements, audit_logs, search invoice docs.
- Decision Points:
  - Products exist/active in branch?
  - BOM exists for product?
  - Stock sufficient?
  - Split tender totals valid?
  - Total non-negative?
- Failure Points:
  - Insufficient stock.
  - Product not found.
  - Tender mismatch.
- Approval Stages: None.
- Notifications Triggered: domain_event websocket broadcast.

Text Diagram:
[Create Sale] -> [Resolve products/BOM] -> [Stock Validation] -> [Compute totals/tenders] -> [Commit sale + lines + movements] -> [Publish events/audit/index]

## WF-05 Sale Void/Refund Workflow
- Starting Point: Void or refund request.
- Ending Point: Sale status updated and stock reversed.
- Actors: Cashier/Manager/Admin/Superadmin.
- Data: sales status metadata, adjustment stock_movements, audit_logs.
- Decision Points:
  - Sale exists in branch?
  - Valid current status?
- Failure Points: Already voided/refunded or invalid status.
- Approval Stages: None.
- Notifications Triggered: domain_event + anomaly_alert websocket message.

Text Diagram:
[Void/Refund Request] -> [Validate status] -> [Insert adjustment movements] -> [Update sale status metadata] -> [Publish events] -> [Anomaly alert]

## WF-06 Payment Reconciliation (Async)
- Starting Point: Enqueue reconcile request.
- Ending Point: Job status succeeded/failed with payload.
- Actors: Cashier/Manager/Admin/Superadmin + Celery worker.
- Data: celery task result, reconciliation metadata in Redis/in-memory fallback.
- Decision Points:
  - Sale exists?
  - Provider reference format valid?
- Failure Points:
  - Mismatch reference -> failed job.
  - Missing metadata -> 404 job not found.
- Approval Stages: None.
- Notifications Triggered: observability counters/histograms and alert rules.

Text Diagram:
[Enqueue API] -> [Store metadata] -> [Celery Task Start] -> {Reference valid?}
Yes -> [Success result]
No -> [Failure result]
-> [Status Poll Endpoint]

## WF-07 Audit Query Workflow
- Starting Point: Query audit logs endpoint.
- Ending Point: Paginated filtered immutable log response.
- Actors: Admin/Superadmin/Manager.
- Data: audit_logs.
- Decision Points:
  - Is role elevated?
  - Requested branch allowed?
- Failure Points: Cross-branch request denied for manager.
- Approval Stages: None.
- Notifications Triggered: observability metrics and logs.

Text Diagram:
[GET /audit/logs] -> [Resolve branch scope] -> [Denied? 403] or [Query filters + pagination] -> [Return rows]

## WF-08 Global Search Workflow
- Starting Point: Search query request.
- Ending Point: Grouped products/suppliers/invoices results.
- Actors: Operational roles + API.
- Data: Elasticsearch index or DB tables fallback.
- Decision Points:
  - Query non-empty?
  - ES available?
- Failure Points: ES exception path falls back to DB.
- Approval Stages: None.
- Notifications Triggered: warning logs on ES failure.

Text Diagram:
[Search Request] -> [Trim/validate q] -> {ES available?}
Yes -> [ES search + highlights]
No -> [SQL fallback]
-> [Grouped response]

## Simple Test Checklist Per Workflow

Run from: erp

### WF-01 Product Lifecycle
- Command: `python -m pytest tests/test_week3_models.py -q`
- Command: `python -m pytest tests/test_week4_inventory_service.py -q`
- What to verify:
  - Product creation succeeds with valid references.
  - Duplicate/invalid references are rejected.

### WF-02 Stock Movement Recording
- Command: `python -m pytest tests/test_week4_inventory_service.py -q`
- Command: `python -m pytest tests/test_week9_inventory_ui_contract.py -q`
- What to verify:
  - Stock movement is persisted for existing branch product.
  - Missing product paths return expected error responses.

### WF-03 Purchase Order Workflow
- Command: `python -m pytest tests/test_week6_procurement.py -q`
- Command: `python -m pytest tests/test_week11_suppliers.py -q`
- What to verify:
  - PO status transitions follow draft -> submitted -> approved -> received/closed.
  - Over-receipt and invalid transitions are blocked.

### WF-04 POS Checkout Workflow
- Command: `python -m pytest tests/test_week10_sales_pos.py -q`
- Command: `python -m pytest tests/test_week12_sales_pricing.py -q`
- What to verify:
  - Sale creation succeeds with valid products and stock.
  - Tender and pricing validations reject invalid totals/contracts.

### WF-05 Sale Void/Refund Workflow
- Command: `python -m pytest tests/test_week11_sales_void.py -q`
- Command: `python -m pytest tests/test_week11_sales_refund.py -q`
- What to verify:
  - Valid void/refund transitions update status.
  - Duplicate or invalid status transitions fail safely.

### WF-06 Payment Reconciliation (Async)
- Command: `python -m pytest tests/test_week13_payment_integration.py -q`
- Command: `python -m pytest tests/test_week14_reconciliation_ops.py -q`
- Command: `python -m pytest tests/test_week15_durable_async_jobs.py -q`
- What to verify:
  - Async reconciliation jobs enqueue and return job status.
  - Invalid provider references fail with expected error state.
  - Metadata/status persistence works across polling calls.

### WF-07 Audit Query Workflow
- Command: `python -m pytest tests/test_week5_audit_events.py -q`
- Command: `python -m pytest tests/test_week6_audit_integration.py -q`
- What to verify:
  - Immutable audit records are produced for domain writes.
  - Branch-scope and role restrictions are enforced on queries.

### WF-08 Global Search Workflow
- Command: `python -m pytest tests/test_week15_search.py -q`
- What to verify:
  - Search returns grouped entity results for valid query text.
  - DB fallback behavior is correct when search backend is unavailable.

### Optional Single-Run Smoke Sweep
- Command: `python -m pytest tests/test_week4_inventory_service.py tests/test_week6_procurement.py tests/test_week10_sales_pos.py tests/test_week11_sales_void.py tests/test_week11_sales_refund.py tests/test_week13_payment_integration.py tests/test_week15_search.py -q`
- What to verify:
  - One representative test file per workflow domain passes in one run.

## UI Workflow Smoke Tests

Run from: erp-web

### UI-01 Login and Session Gate
- Command: `npm run dev`
- Steps:
  - Open `/login` and submit valid credentials.
  - Refresh the browser and verify authenticated state persists.
  - Submit invalid credentials and verify user-visible error.
- Expected:
  - Valid login routes to dashboard.
  - Invalid login does not route and shows an error message.

### UI-02 WF-01 Product Lifecycle (Products Tab)
- Steps:
  - Go to Products and create a product with valid fields.
  - Search for the created product by name.
  - Edit the product and confirm updated values render.
- Expected:
  - Product appears in list after create.
  - Updated values are visible after edit.
  - Duplicate SKU/invalid reference path shows an error toast/message.

### UI-03 WF-02 Stock Movement Recording (Movements Tab)
- Steps:
  - Create an inbound stock movement for an existing product.
  - Filter by movement type/date range.
  - Create an outbound movement and verify list refresh.
- Expected:
  - New movements appear in movement history.
  - Filters narrow results correctly.

### UI-04 WF-04 POS Checkout (POS Tab)
- Steps:
  - Add multiple products to basket.
  - Complete checkout with `cash` payment.
  - Repeat checkout with `split` payment and matching split total.
- Expected:
  - Receipt panel updates after successful checkout.
  - Split payment mismatch shows validation error.
  - Basket clears after successful sale.

### UI-05 WF-05 Sale Void/Refund (POS Tab)
- Steps:
  - Create a sale and capture resulting sale identifier/receipt.
  - Trigger void operation.
  - Create another sale and trigger refund operation.
- Expected:
  - Latest sale status changes to `voided` or `refunded` in UI.
  - Repeating void/refund on invalid status shows error.

### UI-06 WF-03 Purchase Orders and GRN (Procurement Tab)
- Steps:
  - Create a draft purchase order with one line item.
  - Submit and approve the order.
  - Create a GRN for partial receipt, then complete receipt.
- Expected:
  - PO status transitions are visible after each action.
  - Over-receipt attempt is blocked with an error.

### UI-07 Suppliers Management (Procurement Tab)
- Steps:
  - Create a supplier.
  - Search supplier by name.
  - Update contact details.
- Expected:
  - New supplier appears in list and search results.
  - Updated supplier details persist after refresh.

### UI-08 WF-08 Global Search
- Steps:
  - Enter a known product/supplier/invoice query.
  - Execute search and inspect grouped sections.
- Expected:
  - Results are grouped by entity type.
  - Empty query and no-result cases display clear UI states.

### UI-09 Dashboard Live Events (WF-06/WF-07 observability touchpoint)
- Steps:
  - Open dashboard tab.
  - In another tab perform product create, sale create, and void/refund actions.
  - Return to dashboard and observe event feed/anomaly alerts.
- Expected:
  - Live connection indicator becomes connected.
  - New domain events appear in feed after write actions.
  - Void/refund emits anomaly-style alert entry.

### UI-10 Reports and Settings Guardrails
- Steps:
  - Navigate to Reports and Settings tabs.
  - Verify placeholders or partial implementations are explicit.
- Expected:
  - UI does not crash when opening these tabs.
  - Any not-yet-implemented features are communicated clearly.
