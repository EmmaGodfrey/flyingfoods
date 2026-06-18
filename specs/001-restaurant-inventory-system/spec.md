# Feature Specification: Flying Foods Restaurant & Inventory Management System

**Feature Branch**: `001-restaurant-inventory-system`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "Rebuild the existing ERP as a restaurant & inventory management system satisfying the Flying Foods BRD v2.0 (kitchen fulfillment, waiter service, multi-location inventory, procurement with budgets and 3-way match, wastage, versioned menus/recipes, POS ingestion, Pastel accounting sync) plus approved quality enhancements (immutable stock ledger, document-driven postings, leakage reporting, unit-of-measure conversions, generic approval engine, transactional outbox for integrations, recipe costing, reorder suggestions)."

**Source requirements**: Flying Foods BRD v2.0
(`docs/Restaurant_Inventory_BRD.pdf`). BRD requirement IDs (FR-PI, FR-PA,
FR-KD, FR-SV, FR-PR, FR-IS, FR-WA, FR-MR, FR-AD, FR-RP) are
cross-referenced throughout.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sale to Kitchen to Service (Priority: P1)

A customer pays at the existing POS. The sale event arrives in the system within seconds, an order ticket appears on the Kitchen Display, and the recipe's ingredients are automatically deducted from Restaurant Stores stock. The Chef marks the order In Preparation, logs any extra ingredient usage (e.g. a dropped egg), and marks it Ready. The order appears on the Waiter view; the Waiter delivers it and marks it Served. No paper tickets, no manual stock entry, every status change timestamped.

**Why this priority**: This is the operational heart of the BRD — the entire automation principle ("no manual receipt entry, no manual stock deduction") hangs on this flow. Without it the system is just another inventory ledger.

**Independent Test**: Submit a simulated POS sale event; verify the order appears on the Kitchen Display within 5 seconds, stock decreases by the recipe quantities, and the full Ingested → In Preparation → Ready → Served lifecycle can be walked with timestamps recorded at each step.

**Acceptance Scenarios**:

1. **Given** a published recipe for "Beef Burger" and sufficient stock, **When** the POS records a sale of 2 Beef Burgers, **Then** an order appears on the Kitchen Display within 5 seconds showing items, quantities, modifiers, and table/counter reference, and Restaurant Stores stock decreases by 2× the recipe quantities. (FR-PI-01/02, FR-KD-01/02)
2. **Given** the same POS sale event is delivered twice (retry or duplicate push), **When** the second event arrives, **Then** the system ingests it exactly once, keyed on the POS sale ID, and the raw payload of every received event is persisted for audit. (FR-PI-03/04)
3. **Given** an order on the Kitchen Display, **When** the Chef taps Start then Ready, **Then** status moves Ingested → In Preparation → Ready with a timestamp per change, and the order becomes visible on the Waiter view. (FR-KD-03/04, FR-SV-01)
4. **Given** a Ready order, **When** the Waiter taps Served, **Then** the order leaves the Waiter view and records the waiter user, table/counter, and served timestamp. (FR-SV-02/03)
5. **Given** a served order with a problem, **When** the Waiter flags it Returned with a reason, **Then** the order goes back to In Preparation, the Chef is alerted, and the reason and user are recorded. (FR-SV-04)
6. **Given** a sale referencing a menu item with no published recipe, **When** the event is ingested, **Then** the order is flagged for the Administrator and no stock is deducted until resolved. (FR-PI-05)
7. **Given** an order whose recipe ingredients are insufficient in stock, **When** it reaches the Kitchen Display, **Then** the order is flagged and the Storekeeper is alerted. (FR-KD-05)
8. **Given** a dropped egg during preparation, **When** the Chef logs extra usage (item, quantity, reason code) against the active order, **Then** the extra quantity is deducted, the entry records who logged it, and above-threshold entries require Manager approval before the order can be marked Ready. (FR-KD-07, FR-WA-01)

---

### User Story 2 - Procurement: Budget to PO to GRN to 3-Way Match (Priority: P2)

A requester submits a Purchase Budget ("50 tomatoes, 20kg flour"). The Manager approves it on screen. The Receiving Officer creates one or more Purchase Orders against the approved budget, and the system emails each PO as a PDF to the supplier, logging the send. When goods arrive, the Receiving Officer enters a GRN against the PO capturing actual quantity, unit cost, and variance; stock increases at Restaurant Stores and Budget vs Actual updates. The supplier invoice is later matched against PO and GRN in a 3-way match before payment approval.

**Why this priority**: Procurement traceability is the second business driver ("every PO recorded, every GRN matched, every invoice reconciled") and feeds Budget vs Actual — the Manager's main control surface.

**Independent Test**: Walk one budget through submit → approve → PO → email send (captured by a test mailbox) → partial GRN → final GRN → invoice match, verifying stock, budget consumption, and the audit trail at each step.

**Acceptance Scenarios**:

1. **Given** a draft Purchase Budget, **When** the requester submits it, **Then** it routes to the Manager who can Approve, Reject with reason, or Request Revision, and the Receiving Officer is notified on approval. (FR-PR-01/02/03)
2. **Given** an approved budget, **When** the Receiving Officer creates POs, **Then** items can be split across multiple suppliers, each PO generates a PDF, is emailed to the supplier's address on file, and the send (recipient, timestamp, PDF) is recorded in the PO's audit log. (FR-PR-04/05)
3. **Given** a supplier with no email on file, **When** a PO is created for them, **Then** the PO is still recorded, its status reflects "manual contact required", and the Receiving Officer is prompted to contact the supplier outside the system. (FR-PR-06)
4. **Given** an open PO, **When** the Receiving Officer posts a GRN with actual quantities, unit costs, condition, and variance reason, **Then** Restaurant Stores stock increases, Budget vs Actual updates, and the movement is queued for accounting sync. (FR-PR-07/08)
5. **Given** a PO delivered across multiple shipments, **When** several GRNs are posted against it, **Then** each line tracks running fulfilled quantity. (FR-PR-09)
6. **Given** a PO, its GRNs, and a supplier invoice, **When** the invoice is entered, **Then** the system flags any discrepancy between the three documents for review, and the Receiving Officer can resolve, dispute, or escalate to the Manager. (FR-PR-10)
7. **Given** any supplier, **When** their history is viewed, **Then** all POs, GRNs, invoices, and disputes are listed. (FR-PR-11)

---

### User Story 3 - Multi-Location Issuing & Transfers (Priority: P3)

Stock lives at three locations: Restaurant Stores (central), Restaurant Kitchen, and the in-flight Unit. The Restaurant Issuer requests stock from Stores daily; the Unit Issuer requests on Tuesdays and Thursdays (warned, not blocked, on other days). Issues deduct from Stores and add to the destination. Restaurant Kitchen and Unit can transfer stock between each other in both directions; transfers above a configurable value need Manager approval. No issue may drive stock below zero without a Manager override.

**Why this priority**: The three-location model is what the current system lacks entirely and everything else (deduction, wastage, reporting by location) writes against it — but it can ship after the kitchen flow because issuing can briefly remain on paper while kitchen automation already delivers value.

**Independent Test**: Create issues and transfers across all three locations and verify per-location stock-on-hand, the Tue/Thu warning, threshold approval, and negative-stock prevention.

**Acceptance Scenarios**:

1. **Given** stock at Restaurant Stores, **When** the Restaurant Issuer posts a daily Issue Note to Restaurant Kitchen, **Then** Stores decreases and Kitchen increases by the issued quantities. (FR-IS-01/04)
2. **Given** a Wednesday, **When** the Unit Issuer attempts an issue to the Unit, **Then** the system warns that issuing is for Tuesdays/Thursdays, asks for a reason, but allows them to proceed. (FR-IS-02/03)
3. **Given** a transfer between Kitchen and Unit above the configured threshold, **When** it is submitted, **Then** it enters Pending Manager Approval and only posts once approved. (FR-IS-05/06)
4. **Given** an issue that would drive an item's on-hand below zero, **When** it is posted, **Then** the system blocks it unless a Manager explicitly overrides, and the override is logged. (FR-IS-07)
5. **Given** any posted movement, **When** its history is inspected, **Then** every movement is an immutable entry referencing its parent document (issue, transfer, GRN, order, wastage, stock-take adjustment) — no balance can change without a document. *(quality enhancement)*

---

### User Story 4 - Wastage, Breakage & Stock-Take (Priority: P4)

Three event types feed the wastage ledger: in-the-moment extra usage during preparation, breakage/spoilage events with reason codes, and periodic stock-take variances (physical count vs system on-hand). Adjustments above a configurable monetary threshold need Manager approval before posting. All adjustments flow into the Wastage Report and Budget vs Actual so real consumption is visible.

**Why this priority**: Wastage is the anti-leakage core — the gap between theoretical (recipe-driven) and actual consumption is the number the business bought this system for — but it requires the ledger (P3) and kitchen flow (P1) to exist first.

**Independent Test**: Log each wastage type, verify threshold routing to Manager approval, stock adjustment on approval, and appearance in the Wastage Report and the theoretical-vs-actual (leakage) report.

**Acceptance Scenarios**:

1. **Given** spoiled stock, **When** the Storekeeper logs a breakage/spoilage event with item, quantity, reason code, and optional note, **Then** below-threshold entries post immediately and above-threshold entries await Manager approval. (FR-WA-02/05)
2. **Given** a stock-take in progress, **When** the Storekeeper submits physical counts, **Then** the system computes variance per line against system on-hand and posts the total as a Stock-Take Adjustment, with above-threshold totals requiring Manager approval. (FR-WA-04)
3. **Given** an approved adjustment, **When** it posts, **Then** stock is adjusted, the audit log captures it, and it is queued for accounting sync. (FR-WA-06)
4. **Given** a reporting period, **When** the Manager opens the Wastage Report, **Then** wastage is broken down by reason, item, location, user, and period, and wastage value appears in Budget vs Actual. (FR-WA-07/08)
5. **Given** a period of trading, **When** the Manager opens the leakage report, **Then** theoretical consumption (recipe deductions) is compared against actual consumption (stock-take adjusted) per item, surfacing unexplained variance. *(quality enhancement)*

---

### User Story 5 - Versioned Menu & Recipe Management (Priority: P5)

Menus and recipes change. Editing a recipe creates a new version with an effective-from date — never overwrites. Historical orders always reference the recipe version active when the order was placed, so cost reports stay accurate over time. A Draft → Review → Published workflow lets the Administrator stage changes (e.g. a seasonal menu) ahead of an effective date without affecting live service. Menu items and recipes with history can be deactivated, never deleted.

**Why this priority**: Versioning correctness protects every historical report, but a single "current version" suffices for the P1 flow to start delivering value — full versioning workflow can land just behind it.

**Independent Test**: Publish a recipe, place orders, publish a v2 with different quantities, place more orders, and verify old orders still report against v1 quantities and costs.

**Acceptance Scenarios**:

1. **Given** a published recipe, **When** the Administrator edits it, **Then** a new version is created with a chosen effective-from date and the previous version is preserved. (FR-MR-01/02)
2. **Given** orders placed before and after a recipe version change, **When** consumption or cost reports run, **Then** each order applies the version active on its order date. (FR-MR-03)
3. **Given** a draft seasonal menu, **When** it moves Draft → Review → Published with a future effective date, **Then** live service is unaffected until that date. (FR-MR-04)
4. **Given** a menu item with historical transactions, **When** deletion is attempted, **Then** the system refuses and offers deactivation instead. (FR-MR-05)
5. **Given** a menu item scheduled for specific days/time windows, **When** the schedule is configured, **Then** availability reflects it. (FR-MR-06, could-have)

---

### User Story 6 - Pastel Accounting Sync (Priority: P6)

Every stock movement (GRN, issue, transfer, wastage, stock-take adjustment, recipe-driven sale deduction) is mirrored to Pastel, the company's accounting system, in a configurable mode: real-time, daily batch, or event-only. Failed syncs enter a retry queue with exponential backoff and are visible to the Administrator, who can manually re-send after correction. A daily reconciliation report flags any item where system on-hand and Pastel on-hand diverge.

**Why this priority**: Pastel sync removes double-entry for finance — a top business driver — but operations function without it, and reconciliation only matters once movements exist (P1-P4).

**Independent Test**: Post one movement of each type against a simulated Pastel endpoint, verify sync log entries with payload and response, force failures and verify retry/backoff/manual re-send, and run the reconciliation report against a seeded divergence.

**Acceptance Scenarios**:

1. **Given** any posted stock movement, **When** it is committed, **Then** an outbound sync record is created atomically with the movement — a movement can never post without its sync record existing. (FR-PA-01, transactional-outbox enhancement)
2. **Given** sync mode set to real-time / daily batch / event-only, **When** movements post, **Then** delivery to Pastel follows the configured mode. (FR-PA-02)
3. **Given** a Pastel outage, **When** syncs fail, **Then** they retry with exponential backoff, every attempt is logged with timestamp, payload, and response, and failures surface to the Administrator who can re-send manually after correction. (FR-PA-03/04/05)
4. **Given** a divergence between system on-hand and Pastel on-hand, **When** the daily reconciliation report runs, **Then** the item is flagged. (FR-PA-06)

---

### User Story 7 - Reporting & Dashboards (Priority: P7)

Managers, Finance, the Storekeeper, and the Administrator get the reports the BRD lists: Stock on Hand by location, Budget vs Actual (including wastage), PO Register, GRN Register, Issues by Destination, Wastage Report, Service Time, Pastel Reconciliation, Slow/Fast Movers — plus recipe costing (plate cost and margin from GRN unit costs) and reorder suggestions. All reports export to PDF and Excel and paginate without freezing the screen.

**Why this priority**: Reports consume data the earlier stories produce; most are straightforward views once the ledger and documents exist.

**Independent Test**: Seed a known set of transactions, run every report, verify figures against hand-calculated expectations, and export each to PDF and Excel.

**Acceptance Scenarios**:

1. **Given** stock across three locations, **When** Stock on Hand runs for any date, **Then** quantities show by item and location with at/below-reorder-level items highlighted. (FR-RP-01)
2. **Given** approved budgets, GRNs, and wastage in a period, **When** Budget vs Actual runs, **Then** it shows approved budget, GRN actual, wastage value, and variance with drill-down into the underlying documents. (FR-RP-02, US-MGR-03)
3. **Given** served orders, **When** the Service Time report runs, **Then** average and median durations for Ingested → In Preparation → Ready → Served show per shift. (FR-RP-07)
4. **Given** any report, **When** it is exported, **Then** PDF and Excel outputs match on-screen figures. (FR-RP-09)
5. **Given** GRN unit costs and published recipes, **When** recipe costing runs, **Then** plate cost and margin per menu item are reported. *(quality enhancement)*
6. **Given** items below reorder level and recent movement velocity, **When** reorder suggestions run, **Then** a draft purchase list with suggested quantities is produced. *(quality enhancement)*

---

### User Story 8 - Master Data, Roles & Administration (Priority: P8 — but foundation built first)

The Administrator manages users across eight roles (Chef, Waiter, Storekeeper, Receiving Officer, Unit Issuer, Restaurant Issuer, Manager/Finance, System Administrator), the product master (with purchase/stock/recipe units of measure and conversion factors), the supplier master (with email for PO sending), configurable approval thresholds, reason-code lists, and integration settings (POS endpoint, Pastel mode and credentials, supplier email gateway).

**Why this priority**: Listed last as a user-facing story but its data model is the foundation laid first — every other story references products, suppliers, locations, roles, and thresholds.

**Independent Test**: Create users in each role and verify each sees only their permitted screens and API operations; maintain product/supplier masters; change a threshold and verify approval routing changes accordingly.

**Acceptance Scenarios**:

1. **Given** an Administrator, **When** they create, edit, or deactivate users, **Then** deactivated users keep their history and role assignment controls screen and API access. (FR-AD-01)
2. **Given** a product bought in crates, stored in units, and consumed in grams, **When** it is configured with conversion factors, **Then** GRNs, issues, and recipe deductions each operate in their own unit and convert correctly. *(quality enhancement)*
3. **Given** a supplier record, **When** it is maintained, **Then** name, contact, email, phone, approval status, and payment terms are stored, and deactivation (not deletion) is enforced once history exists. (FR-AD-03, US-ADM-02)
4. **Given** configurable thresholds and reason codes, **When** the Administrator changes them, **Then** new approvals and wastage entries follow the updated configuration. (FR-AD-04/05)
5. **Given** integration settings, **When** the Administrator views the integration health dashboard, **Then** POS ingestion and Pastel sync status and failures are visible, with re-send controls. (FR-AD-06, US-ADM-04)

---

### Edge Cases

- POS pushes a sale during a network outage between POS and system → pull/import path or replay admin recovers it; dedupe prevents double ingestion when both paths deliver. (FR-PI-01/03/06)
- Sale arrives for a menu item whose recipe version is Draft (not yet Published) → treated as unknown recipe: flagged, no deduction until resolved.
- Two waiters tap Served on the same order simultaneously → exactly one served record; second tap is a no-op with feedback.
- GRN posted with zero or negative received quantity → rejected with validation message.
- Stock-take submitted while unposted issues exist for the same location → variance computed against on-hand at count start time; concurrent movements flagged on the count sheet.
- Approval threshold changed while items sit in the pending queue → in-flight approvals keep the threshold active at submission time.
- Pastel rejects a payload (mapping error) → sync marked failed with response logged; retries stop after the configured max and the entry waits for Administrator correction; it does not block other syncs.
- Supplier email bounces → bounce logged against the PO send record where the gateway reports it; PO status flags follow-up needed. (BRD §3.3)
- Internet outage in kitchen/stores → screens remain usable on the local network and sync resumes when connectivity returns (NFR: Availability).
- Order returned after stock was deducted and extra usage logged → return reason recorded; stock is not silently re-credited (any re-credit is an explicit wastage/adjustment decision).
- Year-end: reports spanning recipe version changes and price changes must remain internally consistent (versioned references, not current values).

## Requirements *(mandatory)*

### Functional Requirements

**POS Ingestion**

- **FR-001**: System MUST accept sale events from the existing POS through both push (POS-initiated) and pull (system-initiated) paths feeding one ingestion pipeline. (FR-PI-01)
- **FR-002**: System MUST capture sale ID, timestamp, cashier, line items (menu item, quantity, modifiers), and totals per event, and MUST persist the raw payload of every event. (FR-PI-02/04)
- **FR-003**: System MUST deduplicate sale events by POS sale ID so no sale is ingested twice. (FR-PI-03)
- **FR-004**: System MUST flag events referencing unknown menu items/recipes for the Administrator and withhold stock deduction until resolved. (FR-PI-05)
- **FR-005**: System MUST provide an administrator replay/re-trigger screen for a given sale ID with an audit log of who replayed it. (FR-PI-06)

**Kitchen & Service**

- **FR-006**: System MUST display active orders to the Chef in real time, with the order visible within 5 seconds of ingestion. (FR-KD-01, NFR)
- **FR-007**: System MUST automatically deduct the active recipe version's ingredients from Restaurant Stores when the order reaches the Kitchen Display, and queue the deduction for accounting sync. (FR-KD-02)
- **FR-008**: System MUST support the order lifecycle Ingested → In Preparation → Ready → Served with a recorded timestamp and user per transition. (FR-KD-03/04, FR-SV-02/03)
- **FR-009**: System MUST flag orders with insufficient recipe stock and alert the Storekeeper. (FR-KD-05)
- **FR-010**: System MUST let the Chef mark a menu item Out of Stock. (FR-KD-06)
- **FR-011**: System MUST let the Chef or Storekeeper log extra ingredient usage against an active order with item, quantity, reason code, and logged-by; above-threshold entries require Manager approval before the order can be marked Ready. (FR-KD-07, FR-WA-01)
- **FR-012**: System MUST provide a Waiter view of Ready orders (table/counter, items, time-since-Ready, oldest first) and let the Waiter mark Served or flag Returned with a reason that alerts the Chef. (FR-SV-01/04)

**Inventory Ledger, Issuing & Transfers**

- **FR-013**: System MUST maintain stock at three locations (Restaurant Stores, Restaurant Kitchen, Unit) as an append-only movement ledger; every movement MUST reference a parent document (order, GRN, issue note, transfer, wastage entry, stock-take adjustment) and on-hand MUST be derived from movements. *(enhancement; supersets FR-IS-04)*
- **FR-014**: System MUST support daily Issue Notes from Stores to Kitchen and Tue/Thu Issue Notes from Stores to Unit, warning (not blocking, reason required) on other days. (FR-IS-01/02/03)
- **FR-015**: System MUST support inter-unit transfers between Kitchen and Unit in both directions, with Manager approval required above a configurable monetary threshold. (FR-IS-05/06)
- **FR-016**: System MUST prevent any posting that drives an item's on-hand below zero unless a Manager explicitly overrides, logging the override. (FR-IS-07)

**Procurement**

- **FR-017**: System MUST support Purchase Budget submission by authorized roles, Manager approval (approve / reject with reason / request revision), and notification to the Receiving Officer on approval. (FR-PR-01/02/03)
- **FR-018**: System MUST allow one or more POs per approved budget with items split across suppliers. (FR-PR-04)
- **FR-019**: System MUST generate a PO PDF, email it to the supplier's address on file, and record the send (recipient, timestamp, PDF) in an in-system audit log; where the gateway reports it, delivery/bounce results MUST be logged. When no email exists, the PO is still recorded with a status prompting manual contact. (FR-PR-05/06, BRD §3.3)
- **FR-020**: System MUST support GRN entry against a PO capturing item, quantity received, unit cost, condition, and variance reason; posting increases Stores stock, queues accounting sync, and updates Budget vs Actual. Partial GRNs MUST track running fulfilled quantity per line. (FR-PR-07/08/09)
- **FR-021**: System MUST support 3-way matching of PO, GRN(s), and supplier invoice, flagging mismatches for resolve / dispute / escalate. (FR-PR-10)
- **FR-022**: System MUST maintain per-supplier history of POs, GRNs, invoices, and disputes. (FR-PR-11)

**Wastage & Stock-Take**

- **FR-023**: System MUST support breakage/spoilage logging at any time with item, quantity, configurable reason code, and free-text note. (FR-WA-02/03)
- **FR-024**: System MUST support periodic stock-take: count sheet of active items with current on-hand, per-line variance computation, and posting of the total as a Stock-Take Adjustment. (FR-WA-04)
- **FR-025**: System MUST route wastage/adjustments above a configurable monetary threshold to Manager approval before posting; approved entries adjust stock, write to the audit log, and queue for accounting sync. (FR-WA-05/06)

**Menu & Recipes**

- **FR-026**: System MUST maintain versioned menu items and recipes with effective-from/to dates; edits create new versions, historical orders reference the version active on their order date, and items/recipes with history can only be deactivated, never deleted. (FR-MR-01/02/03/05)
- **FR-027**: System MUST support a Draft → Review → Published workflow for menu and recipe changes, and SHOULD support day/time-window scheduling of menu items. (FR-MR-04/06)

**Accounting (Pastel) Sync**

- **FR-028**: System MUST mirror all stock movements to Pastel under a configurable mode (real-time / daily batch / event-only); the outbound record MUST be created atomically with the movement it mirrors. (FR-PA-01/02 + outbox enhancement)
- **FR-029**: System MUST retry failed syncs with exponential backoff, log every attempt (timestamp, payload, response), surface failures to the Administrator, and support manual re-send after correction. (FR-PA-03/04/05)
- **FR-030**: System MUST produce a daily Pastel Reconciliation Report listing items where system on-hand and Pastel on-hand diverge. (FR-PA-06)

**Approvals (cross-cutting)**

- **FR-031**: System MUST provide a single approval mechanism reused by budgets, wastage/adjustments, transfers, and negative-stock overrides: threshold-routed, notifying the approver with full detail, recording approve/reject/request-investigation with reason, and keeping per-period history. *(enhancement; consolidates FR-PR-02, FR-WA-05, FR-IS-06/07)*

**Master Data & Administration**

- **FR-032**: System MUST support user management across the eight BRD roles with create/edit/deactivate (history preserved) and role-based access enforced on every screen and API operation. (FR-AD-01, NFR Security)
- **FR-033**: System MUST maintain a product master (code, name, category, reorder level, accounting code) with distinct purchase, stock, and recipe units of measure and conversion factors between them. (FR-AD-02 + UoM enhancement)
- **FR-034**: System MUST maintain a supplier master (name, contact, email, phone, approval status, payment terms) with deactivate-not-delete once history exists. (FR-AD-03)
- **FR-035**: System MUST maintain configurable approval thresholds, reason-code lists, and integration settings (POS endpoint/mode, Pastel mode and credentials, supplier email gateway), with an integration health dashboard. (FR-AD-04/05/06)

**Reporting**

- **FR-036**: System MUST provide: Stock on Hand by location and date; Budget vs Actual (budget, GRN actual, wastage, variance, drill-down); PO Register; GRN Register; Issues by Destination; Wastage Report (reason/item/location/user/period); Service Time (avg/median per stage per shift); Pastel Reconciliation; Slow/Fast Movers. (FR-RP-01..08)
- **FR-037**: System MUST export every report to PDF and Excel and paginate large outputs without freezing the interface. (FR-RP-09, NFR)
- **FR-038**: System SHOULD provide a theoretical-vs-actual consumption (leakage) report per item per period, recipe costing (plate cost and margin from GRN unit costs), and reorder suggestions derived from reorder levels and movement velocity. *(enhancements)*

**Audit & Security**

- **FR-039**: System MUST log every transaction append-only with user, timestamp, and before/after values, including PO emails sent and Pastel sync attempts. (NFR Audit)
- **FR-040**: System MUST authenticate users with short-lived sessions that renew automatically and revoke on logout, hash and salt all passwords, store integration credentials encrypted, and enforce role permissions at the API level — never relying on screen-level hiding alone. (NFR Security)
- **FR-041**: System MUST apply idempotency safeguards so retries of POS ingestion, GRN posting, Pastel sync, and PO email sending never double-post or double-send. *(enhancement)*

### Key Entities

- **User / Role**: Account with one of eight roles; role determines screens and permitted operations.
- **Product**: Inventory item — code, name, category, reorder level, accounting code, purchase/stock/recipe units of measure with conversion factors.
- **Supplier**: External goods supplier — contact details, email for PO sending, approval status, payment terms; deactivate-not-delete.
- **Location**: Inventory holding location — Restaurant Stores, Restaurant Kitchen, Unit.
- **Stock Movement (Ledger Entry)**: Immutable movement of a product quantity at a location, always referencing a parent document; on-hand is derived.
- **Menu Item / Recipe Version / Recipe Line**: Versioned sellable item and its effective-dated bill of ingredients; orders snapshot the version in force.
- **Sale Event**: Raw ingested POS sale, keyed by POS sale ID, with full payload retained.
- **Order / Order Item / Order Status Event**: Internal order created from a sale event, its lines (with recipe version snapshot), and a timestamped record per status change.
- **Purchase Budget**: Pre-approval purchase request — items, quantities, estimated total, requester, approver, status.
- **Purchase Order**: Order against an approved budget — supplier, lines, status, PDF, send log.
- **GRN**: Goods received against a PO — lines (product, quantity, unit cost), condition, variance, poster.
- **Invoice Match**: 3-way PO↔GRN↔Invoice match with discrepancies and resolution status.
- **Issue Note / Transfer**: Internal stock movements between locations, with requester, approver where required, and status.
- **Wastage Entry**: Extra usage / breakage / spoilage — type, optional order reference, product, quantity, reason code, value, logged-by, status.
- **Stock-Take / Stock-Take Line**: Periodic count per location with per-line system vs counted quantity and variance.
- **Approval**: Generic approval record — subject document, threshold rule applied, approver, decision, reason, timestamps.
- **Reason Code**: Configurable categorized labels for wastage, returns, overrides.
- **Sync Record (Outbox) / Sync Log**: Outbound accounting mirror entry created with its movement, plus per-attempt log (payload, response, status).
- **Notification**: In-app message to a role/user (budget approved, sync failed, low stock, order returned).
- **Audit Log**: Append-only change history — entity, action, user, before/after, timestamp.
- **Integration Settings / Threshold Configuration**: POS mode and endpoint, Pastel mode and credentials, email gateway, approval thresholds.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A paid POS sale appears on the Kitchen Display within 5 seconds, end-to-end, for 95% of orders during normal operation.
- **SC-002**: 100% of stock-on-hand changes are traceable to a parent document and user — zero untraceable balance changes in any audit sample.
- **SC-003**: A duplicate POS sale event is never ingested twice: 0 duplicate orders across any replay/retry scenario.
- **SC-004**: The full procurement cycle (budget submission → approval → PO email → GRN → invoice match) completes with no paper documents and no data re-entry; every PO sent is findable by supplier, date, and PO number.
- **SC-005**: Kitchen, Waiter, and Stores screens remain usable during a short internet outage (order-taking and status changes continue; sync catches up on reconnection) — verified by a pulled-cable test during simulated service.
- **SC-006**: Critical kitchen/waiter actions (start, ready, served, return) are reachable in at most two taps on a tablet.
- **SC-007**: Budget vs Actual, Wastage, and leakage reports reconcile to hand-calculated figures on a seeded dataset with 100% agreement, and all reports export to PDF and Excel.
- **SC-008**: After a simulated Pastel outage, 100% of queued movements deliver on recovery with zero loss and zero duplicates, and the reconciliation report shows no divergence afterward.
- **SC-009**: A user in any of the eight roles can perform every action their BRD user stories require and none outside them — verified by a role-by-role permission matrix test.
- **SC-010**: Historical orders report against the recipe version active at order time even after multiple recipe edits — verified by the versioning test in User Story 5.
- **SC-011**: System availability of 99% during operating hours.
- **SC-012**: Manager approval queues (budgets, wastage, transfers) surface every above-threshold item with full detail, and nothing above threshold ever posts without an approval record.

## Assumptions

- The existing POS remains the system of record for cashiering, payments, receipts, and sales-side reporting; this system never duplicates those functions. (BRD constraint)
- The POS vendor will confirm push vs pull; until then both paths are built against one internal ingestion API so either plugs in. (BRD §3.1 decision pending)
- Pastel exposes an API or import format suitable for posting inventory movements; recommended default sync mode is real-time with retry, falling back to daily batch if Pastel cannot sustain volume. (BRD §3.2 decision pending)
- Every active menu item has a defined recipe at go-live; product master, supplier list, and opening balances are loaded at go-live. (BRD dependencies)
- The Restaurant operates a single central stores location; the Unit manages its own sub-inventory. (BRD assumption)
- Each role has access to a workstation, tablet, or shared device on the local network. (BRD assumption)
- Currency, date format, and time zone are configurable; a single currency is used per installation. (NFR Localisation)
- Sales volumes are restaurant-scale (hundreds of orders/day, thousands of products), not high-volume retail scale.
- The existing system's data (products, suppliers, historical POs/GRNs) will be migrated or re-keyed at go-live; the old system stays available read-only as reference during transition.
- "Out of Stock" flags are communicated back to the POS only if the POS supports a menu-availability feed; otherwise the Chef communicates directly. (FR-KD-06)
- Recipe-costing margin uses POS selling prices as provided in sale events; a full recipe-costing engine remains a later phase per the BRD, with plate cost/margin reporting delivered as a lightweight enhancement.
- Daily backups with a documented restore procedure are an operational requirement on the hosting environment. (NFR Backup)
