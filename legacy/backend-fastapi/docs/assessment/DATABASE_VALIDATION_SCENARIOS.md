# Database Validation Scenarios

## CRUD Coverage Matrix

| Entity | Create | Read/List | Update | Delete | Notes |
|---|---|---|---|---|---|
| users | Seed/manual | auth/me | not exposed | not exposed | auth-focused |
| branches | migration/seed | implicit | not exposed | not exposed | tenant key |
| categories/units | seed/migration | indirect | not exposed | not exposed | required FK refs |
| suppliers | API | API list | API | API | branch scoped |
| products | API | API list/detail | API | API | unique branch name |
| stock_movements | API/service | API list | append-only style | not exposed | computed stock source |
| sales | API | receipt/summary/report | status updates (void/refund) | not exposed | financial core |
| sale_line_items | API via sale | reports/receipt | no direct | cascade via sale | immutable-by-practice |
| purchase_orders | API | API list/reports | submit/approve status | not exposed | workflow statuses |
| purchase_order_line_items | API via PO | hydrated in PO | received_quantity updates via GRN | cascade via PO | qty guard |
| goods_received_notes | API | indirect/report | no direct | cascade via PO | receipt records |
| audit_logs | event-driven create | API query | blocked (PG trigger) | blocked (PG trigger) | hash chain |

## Referential Integrity Tests
- RI-001: product.unit_id must exist in units for same branch domain assumptions.
- RI-002: product.category_id set null on category delete (if category deletion ever introduced).
- RI-003: product.supplier_id set null on supplier delete.
- RI-004: stock_movement.product_id cannot reference deleted product due to RESTRICT.
- RI-005: sale_line_items cascade when sale deleted (if administrative deletion performed).
- RI-006: PO line items cascade on PO delete.
- RI-007: GRN line references PO line via RESTRICT.

## Duplicate Prevention Tests
- DP-001: categories unique (branch_id, name).
- DP-002: units unique (branch_id, name).
- DP-003: suppliers unique (branch_id, name).
- DP-004: products unique (branch_id, name).
- DP-005: BOM unique (branch_id, product_id, ingredient_id).
- DP-006: audit_logs hash_chain_curr unique.

## Data Consistency Tests
- DC-001: Sale subtotal equals sum(line_total) from sale_line_items.
- DC-002: Sale total equals subtotal + tax_amount - discount_amount.
- DC-003: Split tender amounts sum exactly to sale total.
- DC-004: GRN received_quantity aggregate does not exceed PO quantity.
- DC-005: Computed stock equals SUM(stock_movements.qty) per product/branch.

## Branch Isolation Tests
- BI-001: Cross-branch product/sale/supplier lookup returns not found.
- BI-002: Search returns only branch-matching entities.
- BI-003: Audit scope denies non-elevated cross-branch reads.

## Suggested Additional DB Tests
- Add concurrent transaction tests for oversell and over-receipt race windows.
- Add migration test proving audit append-only triggers active on PostgreSQL runtime.
- Add property-based tests for monetary precision and quantization edge cases.
