# Functional Test Cases

## Legend
- Priority: Critical/High/Medium/Low
- Component format: API -> Service -> DB/Infra

## End-to-End Scenarios

| Test ID | Description | Actor | Steps | Expected Result | Components | Priority |
|---|---|---|---|---|---|---|
| FT-AUTH-001 | Login success | Manager | POST /auth/login with valid credentials | 200 token pair | auth.py -> auth_service.py -> user/security models | Critical |
| FT-AUTH-002 | Login invalid password | Manager | POST /auth/login wrong password | 401 Invalid credentials | auth.py -> security.verify_password | High |
| FT-AUTH-003 | Refresh success | Manager | POST /auth/refresh with valid token | 200 new token pair | auth.py -> auth_service.rotate_refresh_token | Critical |
| FT-AUTH-004 | Refresh replay token | Manager | Reuse already-rotated refresh token | 401 invalid/no longer valid | auth.py -> auth_service + Redis key | High |
| FT-INV-001 | List products pagination | Inventory Officer | GET /inventory/products?limit=20&offset=0 | 200 list + total | inventory.py -> inventory_service.list_products | High |
| FT-INV-002 | Create product happy path | Manager | POST /inventory/products valid payload | 201 created product | inventory.py -> inventory_service.create_product -> audit/event/index | Critical |
| FT-INV-003 | Create product duplicate name | Manager | POST same name in branch | 400 duplicate/integrity error | inventory.py -> DB unique constraint | High |
| FT-INV-004 | Update product missing id | Manager | PUT /inventory/products/9999 | 404 Product not found | inventory.py -> get_product_or_none | Medium |
| FT-INV-005 | Delete product referenced by records | Admin | DELETE referenced product | 409 conflict | inventory.py -> delete_product -> FK restriction | High |
| FT-INV-006 | Create stock movement receive | Cashier | POST /inventory/movements | 201 movement created | inventory.py -> inventory_service.create_stock_movement | High |
| FT-INV-007 | Movement filter boundary | Manager | GET /inventory/movements with invalid movement_type | 400 invalid movement_type | inventory.py query validation | Medium |
| FT-INV-008 | Current stock cache behavior | Manager | GET /inventory/stock/current twice | same response, second may hit cache | inventory_service.get_computed_stock + Redis | Medium |
| FT-INV-009 | Low stock alerts | Manager | Seed stock below reorder then GET /inventory/stock/low | Alert contains product | inventory_service.get_low_stock_alerts | Medium |
| FT-PROC-001 | Create supplier | Manager | POST /procurement/suppliers | 201 supplier | procurement.py -> supplier_service.create_supplier | High |
| FT-PROC-002 | Supplier cross-branch visibility | Manager | Branch2 lists suppliers | only branch2 suppliers | procurement.py -> supplier_service.list_suppliers | Critical |
| FT-PROC-003 | Create PO draft | Manager | POST /procurement/orders with lines | 201 status draft | procurement.py -> procurement_service.create_purchase_order | Critical |
| FT-PROC-004 | Submit PO from draft | Manager | PUT /procurement/orders/{id}/submit | 200 status submitted | procurement_service.submit_purchase_order | Critical |
| FT-PROC-005 | Approve PO role enforcement | Manager/Admin | Manager approve then Admin approve | Manager 403, Admin 200 | require_role + procurement approve endpoint | Critical |
| FT-PROC-006 | GRN full receipt closes PO | Inventory Officer | POST /procurement/grn receiving all qty | 201, status_after_receipt closed | procurement_service.create_goods_received_note | Critical |
| FT-PROC-007 | GRN over-receipt blocked | Inventory Officer | Receive > ordered qty | 400 validation error | procurement_service quantity check | High |
| FT-PROC-008 | Procurement reports | Manager | GET orders/spend reports | Aggregates returned | procurement_service reporting functions | Medium |
| FT-SALE-001 | Create sale with BOM depletion | Cashier | POST /sales with BOM product | 201 receipt, ingredient stock decreases | sales.py -> sales_service.create_sale -> stock_movements | Critical |
| FT-SALE-002 | Insufficient stock rejection | Cashier | POST /sales large quantity | 400 insufficient stock | sales_service._validate_stock | Critical |
| FT-SALE-003 | Split tender validation | Cashier | POST split where tender sum mismatches | 400 split tenders must sum to total | sales_service._resolve_payment_tenders | High |
| FT-SALE-004 | Receipt fetch | Cashier | GET /sales/{id}/receipt | 200 receipt | sales_service.get_sale_receipt | Medium |
| FT-SALE-005 | Daily summary aggregation | Manager | GET /sales/summary/daily | count and totals accurate | sales_service.get_daily_sales_summary | High |
| FT-SALE-006 | Void sale stock reversal | Cashier | POST /sales/{id}/void | status voided + stock restored | sales_service.void_sale | Critical |
| FT-SALE-007 | Refund sale stock reversal | Cashier | POST /sales/{id}/refund | status refunded + stock restored | sales_service.refund_sale | Critical |
| FT-SALE-008 | Refund after void blocked | Cashier | Void then refund same sale | 400 invalid status | sales_service.refund_sale checks | High |
| FT-PAY-001 | Payment intent success | Cashier | POST /sales/{id}/payments/intent | authorized_tenders returned | sales_service.create_sale_payment_intent | High |
| FT-PAY-002 | Payment intent cash-only blocked | Cashier | Intent on cash-only sale | 400 no provider-eligible tenders | sales_service._digital_tender_total_from_sale | High |
| FT-PAY-003 | Reconcile sync success | Cashier | POST /payments/reconcile valid ref | reconciled result | sales_service.reconcile_sale_payment | High |
| FT-PAY-004 | Reconcile async status lifecycle | Cashier | enqueue and poll status endpoint | queued/running/succeeded or failed | sales_service enqueue/status + sales_tasks | Critical |
| FT-AUD-001 | Audit query branch restriction | Manager | GET /audit/logs?branch_id=other | 403 denied | audit.py + audit_service.resolve_audit_branch_scope | Critical |
| FT-AUD-002 | Audit deterministic ordering | Admin | Query with same occurred_at logs | tie-break by id desc | audit_service.list_audit_logs | Medium |
| FT-RPT-001 | Sales report JSON | Manager | GET /reports/sales | totals and lines present | reports.py -> reporting_service.get_sales_report | High |
| FT-RPT-002 | Sales report CSV | Manager | GET /reports/sales/export/csv | CSV headers and rows | reports.py csv writer | Medium |
| FT-RPT-003 | Inventory valuation report | Manager | GET /reports/inventory/valuation | branch valuation returned | reporting_service.get_inventory_valuation_report | High |
| FT-RPT-004 | Inventory movement report filter | Manager | invalid movement_type | 400 | reports.py validation | Medium |
| FT-RPT-005 | Async procurement report task | Manager | POST /reports/procurement/spend/async then poll | succeeded result payload | reporting_service enqueue/status + report_tasks | High |
| FT-SEARCH-001 | Search DB fallback | Manager | disable ES, GET /search?q=... | grouped results from DB | search_service._search_workspace_db_fallback | Medium |
| FT-SEARCH-002 | Search ES highlights | Manager | mocked ES response | highlights list populated | search_service._search_workspace_elasticsearch | Medium |
| FT-WS-001 | Websocket connection and events | Manager | connect ws, create sale, void sale | domain_event + anomaly_alert messages | dashboard_ws.py + inventory_events.py + websockets.py | Critical |

## Database Validation Scenarios
- DB-VAL-001: Unique per-branch category/unit/supplier/product name constraints.
- DB-VAL-002: BOM cannot self-reference (product_id != ingredient_id).
- DB-VAL-003: BOM unique (branch, product, ingredient).
- DB-VAL-004: FK restrictions for branch integrity (ondelete RESTRICT/SET NULL/CASCADE as defined).
- DB-VAL-005: Audit hash_chain_curr unique.
- DB-VAL-006: Audit append-only trigger behavior on PostgreSQL.

## Boundary And Validation Focus
- Query pagination boundaries: limit min/max and offset >= 0.
- Date parsing: occurred_after/occurred_before/date_from/date_to invalid formats.
- Decimal boundaries: tax/discount non-negative, quantity > 0, tender sum exact total.
- Enum boundaries: movement_type and payment enums.
