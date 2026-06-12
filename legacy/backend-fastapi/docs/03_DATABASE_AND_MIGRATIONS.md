# ERP Backend Documentation - Database and Migrations

## 1. Migration Timeline

### 20260527_0001_initial_empty_schema
- Baseline root revision.
- No tables; establishes migration chain start.

### 20260527_0002_auth_and_branches
Creates:
- branches
- users

Key points:
- users.branch_id foreign key to branches.
- email uniqueness.
- role and active flags.

### 20260527_0003_inventory_core_schema
Creates:
- categories
- units
- suppliers
- products
- stock_movements
- bill_of_materials

Key points:
- branch_id present across tenant-scoped tables.
- stock_movements has product_id + branch_id composite index.
- bill_of_materials has:
  - unique branch/product/ingredient tuple
  - check to prevent product_id == ingredient_id

### 20260528_0004_immutable_audit_log
Creates:
- audit_logs

Key points:
- append-only audit contract with DB-level update/delete protection trigger (PostgreSQL).
- hash-chain fields for tamper-evidence:
  - hash_chain_prev
  - hash_chain_curr (unique)
- indexes for branch, actor, action, entity, request correlation, and occurred_at.

### Week 6 note
- No new migration revision.
- Stage focused on integration verification of existing week 5 schema/runtime contracts.

### Week 7 note
- No new migration revision.
- Stage focused on runtime observability instrumentation and verification.

### 20260528_0005_sales_pos_domain
Creates:
- sales
- sale_line_items

Key points:
- sales rows are branch-scoped with cashier and payment_method fields.
- sale_line_items are branch-scoped and linked to products.
- sales stock deductions are still represented in stock_movements (event ledger remains source-of-truth for current stock).

### 20260528_0006_sales_void_status
Adds to sales:
- status
- voided_at
- voided_by_user_id
- void_reason

Key points:
- Enables sale lifecycle transition to voided with actor and reason tracking.

### 20260528_0007_sales_refund_status
Adds to sales:
- refunded_at
- refunded_by_user_id
- refund_reason

Key points:
- Enables sale lifecycle transition to refunded with actor and reason tracking.

## 2. Domain Tables and Purpose

### branches
Tenant boundary root object.

### users
Authenticated actors with role and branch assignment.

### categories
Branch-scoped product categorization.

### units
Branch-scoped measurement definitions (piece, kg, etc.).

### suppliers
Branch-scoped procurement partner records.

### products
Branch-scoped inventory catalog with reorder and pricing data.

### stock_movements
Append-only inventory ledger events.
Movement types currently include receive, sale, waste, adjustment.

### bill_of_materials
Finished product to ingredient mapping used for future POS/BOM explosion flows.

### audit_logs
Immutable branch-scoped audit ledger for write-path traceability.
Includes actor, action, entity identity, before/after payloads, request correlation, and hash-chain continuity.

### sales
POS sale header table for branch, cashier, payment method, and totals.

### sale_line_items
POS sale detail lines for product, quantity, unit_price, and line_total.

## 3. Relationship Summary
- Branch 1..N Users
- Branch 1..N Categories
- Branch 1..N Units
- Branch 1..N Suppliers
- Branch 1..N Products
- Product 1..N StockMovements
- Product 1..N BOM outputs/inputs (self-referential via ingredient_id)
- Branch 1..N AuditLogs
- User 1..N AuditLogs (actor relationship, nullable for system actions)
- Branch 1..N Sales
- Sale 1..N SaleLineItems
- Product 1..N SaleLineItems

## 4. Index and Performance Notes
Current important indexes:
- branch_id indexes on tenant tables.
- product_id and branch_id indexes on stock_movements.
- composite index on stock_movements(product_id, branch_id).
- audit_logs indexes on occurred_at, branch_id, actor_user_id, action, entity_type, entity_id, request_id.
- unique index on audit_logs.hash_chain_curr.
- branch_id/cashier_user_id/created_at indexes on sales.
- sale_id/branch_id/product_id indexes on sale_line_items.

Why:
- Supports fast stock sum queries and branch isolation filters.

## 5. Data Integrity Rules
- Unique branch-level naming constraints on selected catalog tables.
- Foreign keys enforce branch-compatible references by workflow.
- BOM self-reference check prevents invalid ingredient cycles at row level.
- Audit table is append-only at DB level (update/delete denied via trigger in PostgreSQL).

## 6. Migration Workflow
1. Add/modify ORM models.
2. Create new Alembic revision.
3. Run upgrade head locally.
4. Execute tests.
5. Update docs for schema contract changes.

Going forward, every stage that changes schema must update this document in the same commit that introduces the migration.

## 7. Seed Data Behavior
seed_week3.py creates:
- One branch (HQ)
- Base unit/category/supplier
- Bun, patty, burger products
- BOM rows for burger ingredients
- Initial stock receive movements

Use this only for local development/demo environments.

## 8. Not Implemented Yet
- No dedicated refund/void tables (current design stores reversal metadata on sales and stock adjustments in stock_movements).
- No payment transaction ledger with external gateway references.
- No tax/discount breakdown columns on sale lines beyond unit and line totals.
