# Data Model: Flying Foods Restaurant & Inventory Management System

All models inherit `core.BaseModel`: `id` (UUID v4 PK), `created_at`, `updated_at`. FKs are UUID. Money fields are `DecimalField(max_digits=12, decimal_places=2)`; quantities `DecimalField(max_digits=12, decimal_places=3)`. Soft-delete is `is_active=False` (deactivate-not-delete) wherever history can exist.

## core

### ReasonCode
| Field | Type | Notes |
|---|---|---|
| category | choices: WASTAGE, RETURN, OVERRIDE, ISSUE_DAY, VARIANCE | FR-AD-05 |
| label | char(100) | |
| is_active | bool | |

### ThresholdConfig
| Field | Type | Notes |
|---|---|---|
| scope | choices: TRANSFER, WASTAGE, ADJUSTMENT, EXTRA_USAGE | FR-AD-04 |
| amount | decimal | monetary threshold |
| is_active | bool | one active row per scope |

### Approval
| Field | Type | Notes |
|---|---|---|
| subject_type / subject_id | GenericFK | budget, wastage entry, transfer, stock-take, negative-stock override |
| threshold_snapshot | decimal, null | threshold in force at submission (edge case: threshold changed mid-flight) |
| status | choices: PENDING, APPROVED, REJECTED, INVESTIGATION | state machine, terminal: APPROVED/REJECTED |
| requested_by / decided_by | FK User | |
| reason | text | required on REJECTED |
| decided_at | datetime, null | |

### OutboxRecord
| Field | Type | Notes |
|---|---|---|
| entity_type / entity_id | char / UUID | movement batch, GRN, adjustment… |
| payload | JSON | Pastel-shaped payload built at write time |
| status | choices: PENDING, SENDING, SENT, FAILED, ABANDONED | |
| attempts | int | |
| next_attempt_at | datetime | backoff schedule |
| created same transaction as source document | — | invariant |

### IdempotencyKey
| Field | Type | Notes |
|---|---|---|
| key | char(64), unique | client header or derived |
| endpoint | char | |
| response_snapshot | JSON | replayed on duplicate |

### AuditLog (append-only; no update/delete ever)
| Field | Type | Notes |
|---|---|---|
| entity / entity_id | char / UUID | |
| action | char | CREATE, POST, APPROVE, OVERRIDE, REPLAY, SEND… |
| user | FK User, null | null = system |
| before / after | JSON, null | |
| at | datetime | indexed with entity |

### Notification
| Field | Type | Notes |
|---|---|---|
| recipient | FK User | fan-out by role at creation |
| kind | choices: BUDGET_APPROVED, SYNC_FAILED, LOW_STOCK, ORDER_RETURNED, APPROVAL_PENDING, INSUFFICIENT_STOCK | |
| subject_type / subject_id | GenericFK, null | deep-link target |
| body | text | |
| read_at | datetime, null | |

### IntegrationSettings (singleton-per-key config)
| Field | Type | Notes |
|---|---|---|
| key | char unique: POS_MODE, POS_ENDPOINT, PASTEL_MODE, PASTEL_CREDENTIALS, EMAIL_GATEWAY | FR-AD-06 |
| value | JSON (encrypted at rest for credentials) | |

## users

### User (AbstractBaseUser + PermissionsMixin + BaseModel)
| Field | Type | Notes |
|---|---|---|
| email | unique | USERNAME_FIELD |
| full_name | char(255) | |
| role | choices: CHEF, WAITER, STOREKEEPER, RECEIVING_OFFICER, UNIT_ISSUER, RESTAURANT_ISSUER, MANAGER, ADMIN | FR-AD-01; permission classes map per role |
| is_active / is_staff | bool | deactivate keeps history |

## masterdata

### Category — name, is_active
### Location — name, kind choices: STORES, KITCHEN, UNIT (seeded: Restaurant Stores, Restaurant Kitchen, Unit)

### Product
| Field | Type | Notes |
|---|---|---|
| code | char unique | |
| name | char | |
| category | FK Category | |
| stock_uom | char | canonical ledger unit |
| purchase_uom / recipe_uom | char | display/entry units |
| purchase_to_stock_factor / recipe_to_stock_factor | decimal | UoM conversions (enhancement) |
| reorder_level | decimal | in stock_uom |
| pastel_code | char | accounting mapping |
| is_active | bool | |

### Supplier
| Field | Type | Notes |
|---|---|---|
| name, contact_name, email (null), phone | | FR-AD-03; null email triggers manual-contact PO path |
| approval_status | choices | |
| payment_terms | char | |
| is_active | bool | deactivate-not-delete |

## menu

### MenuItem — name, category, status (ACTIVE/INACTIVE), pos_code (maps POS line items), schedule JSON (optional day/time windows, FR-MR-06)

### RecipeVersion
| Field | Type | Notes |
|---|---|---|
| menu_item | FK | |
| version_no | int | unique with menu_item |
| status | choices: DRAFT, REVIEW, PUBLISHED, RETIRED | FR-MR-04 |
| effective_from / effective_to | date / date null | resolution: version where from ≤ order date < to, status PUBLISHED |
| selling_price_snapshot | decimal, null | for costing report |

### RecipeLine — recipe_version FK, product FK, qty_per_serving (recipe_uom)

**Invariant**: editing a PUBLISHED version is forbidden; service creates the next version (FR-MR-02). Deletion forbidden once any OrderItem references a version (FR-MR-05).

## pos_ingest

### SaleEvent
| Field | Type | Notes |
|---|---|---|
| pos_sale_id | char unique | dedupe key (FR-PI-03) |
| payload | JSON | raw, immutable (FR-PI-04) |
| cashier / sold_at / totals | extracted | FR-PI-02 |
| status | choices: INGESTED, FLAGGED_UNKNOWN_ITEM, REPLAYED, FAILED | FR-PI-05 |
| ingested_at | datetime | |

### ReplayLog — sale_event FK, replayed_by FK User, at (FR-PI-06)

## kitchen

### Order
| Field | Type | Notes |
|---|---|---|
| sale_event | OneToOne | provenance |
| table_ref | char | |
| status | choices: INGESTED, IN_PREPARATION, READY, SERVED, RETURNED | transitions: INGESTED→IN_PREPARATION→READY→SERVED; RETURNED→IN_PREPARATION (FR-SV-04) |
| flagged_insufficient_stock | bool | FR-KD-05 |

### OrderItem — order FK, menu_item FK, recipe_version FK (snapshot, FR-MR-03), qty, modifiers JSON, price

### OrderStatusEvent — order FK, status, user FK, at (FR-KD-04; feeds Service Time report)

### OutOfStockFlag — menu_item FK, flagged_by, cleared_at null (FR-KD-06)

## inventory

### StockMovement (append-only ledger; the only writer is `post_movements()`)
| Field | Type | Notes |
|---|---|---|
| product | FK | |
| location | FK | |
| qty_delta | decimal | stock_uom; + in, − out |
| movement_type | choices: SALE_DEDUCTION, EXTRA_USAGE, GRN_RECEIPT, ISSUE_OUT, ISSUE_IN, TRANSFER_OUT, TRANSFER_IN, WASTAGE, STOCKTAKE_ADJ, OVERRIDE_ADJ | |
| document_type / document_id | char / UUID | parent document — required, FR-013 |
| unit_cost | decimal, null | from GRN; valuation + costing |
| posted_by | FK User, null | null = system (sale deduction) |
| posted_at | datetime | indexed (product, location, posted_at) |

### StockBalance — product FK, location FK (unique together), qty_on_hand, last_movement_at. Cache; updated in-transaction with `select_for_update()`.

### IssueNote
| Field | Type | Notes |
|---|---|---|
| source / destination | FK Location | Stores→Kitchen daily; Stores→Unit Tue/Thu |
| requested_by | FK User | role-checked |
| off_schedule_reason | FK ReasonCode, null | warn-not-block (FR-IS-03) |
| status | choices: DRAFT, POSTED | |
| lines | child IssueNoteLine: product, qty | |

### Transfer — source/destination FK Location (Kitchen↔Unit), lines, status: DRAFT, PENDING_APPROVAL, POSTED, REJECTED; approval via core.Approval when value > threshold (FR-IS-05/06)

### StockTake
| Field | Type | Notes |
|---|---|---|
| location | FK | |
| started_by / started_at | | variance baseline = on-hand at start (edge case) |
| status | choices: IN_PROGRESS, PENDING_APPROVAL, POSTED | |

### StockTakeLine — stock_take FK, product FK, system_qty (frozen at start), counted_qty, variance (computed), value

## procurement

### PurchaseBudget
| Field | Type | Notes |
|---|---|---|
| requester | FK User | FR-PR-01 |
| status | choices: DRAFT, SUBMITTED, APPROVED, REJECTED, REVISION_REQUESTED | via Approval engine (FR-PR-02) |
| total_estimated | decimal | |
| lines | child BudgetLine: product, qty, est_unit_cost | |

### PurchaseOrder
| Field | Type | Notes |
|---|---|---|
| budget | FK PurchaseBudget | FR-PR-04 |
| supplier | FK Supplier | |
| po_number | char unique, sequential | searchable (BRD §3.3) |
| status | choices: CREATED, SENT, MANUAL_CONTACT_REQUIRED, PARTIALLY_RECEIVED, RECEIVED, CLOSED | FR-PR-06 status |
| pdf_file | file | generated PDF stored on record |
| lines | child POLine: product, qty, unit_price; fulfilled_qty running total (FR-PR-09) |

### POSendLog — po FK, recipient, sent_at, result choices: SENT, DELIVERED, BOUNCED, NONE_NO_EMAIL (FR-PR-05, BRD §3.3)

### GRN
| Field | Type | Notes |
|---|---|---|
| po | FK PurchaseOrder | |
| received_by | FK User | |
| status | DRAFT, POSTED | posting calls post_movements() (FR-PR-08) |
| lines | child GRNLine: po_line FK, qty_received, unit_cost, condition, variance_reason FK ReasonCode null |

### SupplierInvoice — supplier FK, po FK, invoice_ref, amount, file null
### InvoiceMatch — po FK, invoice FK, status: MATCHED, DISCREPANCY, DISPUTED, ESCALATED, RESOLVED; discrepancies JSON (FR-PR-10)

## wastage

### WastageEntry
| Field | Type | Notes |
|---|---|---|
| entry_type | choices: EXTRA_USAGE, BREAKAGE, SPOILAGE | FR-WA-01/02 |
| order | FK kitchen.Order, null | required for EXTRA_USAGE |
| product / location / qty | | |
| reason_code | FK ReasonCode | |
| note | text | |
| value | decimal | qty × latest cost; threshold comparison |
| logged_by | FK User | |
| status | DRAFT, PENDING_APPROVAL, POSTED, REJECTED | Approval engine above threshold (FR-WA-05) |

## pastel

### PastelSyncLog — outbox FK, attempted_at, status: SUCCESS, FAILED; request_payload JSON, response JSON (FR-PA-04)
### ReconciliationRun / ReconciliationLine — run date, product, our_on_hand, pastel_on_hand, divergence (FR-PA-06)

## State machines (authoritative)

- **Order**: INGESTED → IN_PREPARATION → READY → SERVED; RETURNED (from SERVED or READY) → IN_PREPARATION. Guard: cannot mark READY with unresolved above-threshold extra-usage approval (US1-AS8).
- **RecipeVersion**: DRAFT → REVIEW → PUBLISHED → RETIRED (auto when superseded). PUBLISHED rows immutable.
- **Approval**: PENDING → APPROVED | REJECTED | INVESTIGATION → (APPROVED | REJECTED).
- **PurchaseBudget**: DRAFT → SUBMITTED → APPROVED | REJECTED | REVISION_REQUESTED → SUBMITTED.
- **PurchaseOrder**: CREATED → SENT | MANUAL_CONTACT_REQUIRED → PARTIALLY_RECEIVED → RECEIVED → CLOSED.
- **OutboxRecord**: PENDING → SENDING → SENT | FAILED → (retry) PENDING | ABANDONED.

## Key invariants

1. No `StockMovement` without a valid `(document_type, document_id)` — enforced in `post_movements()`, the sole writer.
2. `StockBalance.qty_on_hand` ≥ 0 unless an APPROVED override Approval exists for the posting (FR-IS-07).
3. `OutboxRecord` is created in the same transaction as its movements (FR-PA-01 atomicity).
4. `SaleEvent.pos_sale_id` unique — duplicate ingestion is structurally impossible (FR-PI-03).
5. `OrderItem.recipe_version` is immutable after creation (FR-MR-03).
6. `AuditLog` and `StockMovement` have no UPDATE/DELETE paths (DB-level: no ORM update methods exposed; optionally PostgreSQL rule/trigger).
7. Products, suppliers, menu items with transaction history: `is_active=False` only, never row deletion (FR-MR-05, FR-AD-03).

## Indexes (hot paths)

- StockMovement: (product, location, posted_at), (document_type, document_id)
- StockBalance: unique (product, location)
- Order: (status, created_at); OrderStatusEvent: (order, at)
- SaleEvent: unique (pos_sale_id)
- OutboxRecord: (status, next_attempt_at)
- Approval: (status, subject_type)
- PurchaseOrder: (supplier, created_at), unique (po_number)
- WastageEntry: (entry_type, created_at), (location, created_at)
- Notification: (recipient, read_at)
