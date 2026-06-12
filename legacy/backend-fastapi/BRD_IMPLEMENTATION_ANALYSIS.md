# BRD Implementation Gap Analysis

**Document:** Flying Foods Restaurant & Inventory Management System BRD v2.0  
**Date:** Comparison against current ERP implementation  
**Status:** Implementation coverage assessment

---

## Executive Summary

The current ERP system implements a modular monolith with inventory, procurement, POS, and reporting capabilities. However, the BRD requires a **Restaurant-Specific** system with kitchen fulfillment workflows, waiter service management, menu/recipe versioning, and Pastel integration - none of which are currently implemented.

This analysis compares the BRD requirements against the existing ERP implementation to identify gaps.

---

## Section-by-Section Coverage

### 1. Executive Summary & Scope

| BRD Requirement | ERP Implementation Status | Notes |
|-----------------|---------------------------|-------|
| **In Scope:** Kitchen Display, Chef workflow, extra-usage logging | ❌ NOT IMPLEMENTED | No kitchen display module exists |
| **In Scope:** Waiter view, order delivery & served status | ❌ NOT IMPLEMENTED | No waiter service workflow |
| **In Scope:** Inventory at Stores, Kitchen, and Unit (3 locations) | ⚠️ PARTIAL | ERP supports inventory but only basic stock tracking, no location-specific multi-location model |
| **In Scope:** Procurement: Budget → PO → Supplier email → GRN | ⚠️ PARTIAL | ERP has procurement orders and GRN but no budget workflow, no supplier email integration |
| **In Scope:** Wastage, breakage, stock-take adjustments | ❌ NOT IMPLEMENTED | No wastage management module |
| **In Scope:** Inter-unit transfers (Restaurant ↔ Unit) | ❌ NOT IMPLEMENTED | No inter-unit transfer functionality |
| **In Scope:** Menu & Recipe Management with versioning | ❌ NOT IMPLEMENTED | ERP has products but no menu items or recipe versioning |
| **In Scope:** POS integration (sale events in) | ⚠️ PARTIAL | ERP has sales module but no POS event ingestion (push/pull) |
| **In Scope:** Pastel integration (stock movements out) | ❌ NOT IMPLEMENTED | No Pastel integration exists |
| **Out of Scope:** Cashiering, payment processing, receipt printing | ✅ ALREADY IN POS | ERP correctly doesn't duplicate this |

---

### 2. Functional Requirements (FR-xx) Coverage

#### 6.1 POS Integration Module (FR-PI) - **0% Complete**

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-PI-01 | Accept sale events from existing POS (push/pull) | ❌ | ERP has `/sales` endpoints but no POS event ingestion |
| FR-PI-02 | Sale event fields (ID, timestamp, items, modifiers) | ❌ | Not implemented |
| FR-PI-03 | Deduplicate sale events by POS sale ID | ❌ | No deduplication logic |
| FR-PI-04 | Persist raw copy of every sale event for audit | ❌ | No sale event audit trail |
| FR-PI-05 | Flag unknown menu items/recipes | ❌ | No menu item master with recipes |
| FR-PI-06 | Admin screen to re-trigger ingestion | ❌ | No admin tooling |

#### 6.2 Pastel Integration Module (FR-PA) - **0% Complete**

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-PA-01 | Push stock movements to Pastel (GRN, issues, transfers, wastage, adjustments, sales) | ❌ | No Pastel integration |
| FR-PA-02 | Configurable sync mode (Real-time, Daily Batch, Event-only) | ❌ | Not implemented |
| FR-PA-03 | Failed syncs with retry queue | ❌ | No retry mechanism |
| FR-PA-04 | Log sync attempts with timestamp and payload | ❌ | No Pastel sync logging |
| FR-PA-05 | Admin manual re-send of failed syncs | ❌ | No admin interface |
| FR-PA-06 | Daily Pastel Reconciliation Report | ❌ | No reconciliation reports |

#### 6.3 Kitchen Display & Completion Module (FR-KD) - **0% Complete**

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-KD-01 | Display active orders to Chef in real-time | ❌ | No kitchen display |
| FR-KD-02 | Auto-deduct recipe ingredients when order reaches Kitchen Display | ❌ | No recipe-based deduction |
| FR-KD-03 | Chef can mark order In Preparation → Ready | ❌ | No order status management |
| FR-KD-04 | Record timestamp at each status change | ❌ | No order lifecycle timestamps |
| FR-KD-05 | Flag orders with insufficient stock | ❌ | No stock alerting |
| FR-KD-06 | Chef can mark menu item Out of Stock | ❌ | No stock status flags |
| FR-KD-07 | Chef can log extra ingredient usage with reason code | ❌ | No extra usage logging |

#### 6.4 Waiter / Service Module (FR-SV) - **0% Complete**

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-SV-01 | Waiter view showing Ready orders with time-since-Ready | ❌ | No waiter interface |
| FR-SV-02 | Waiter can mark order Served | ❌ | No service workflow |
| FR-SV-03 | Record Waiter user, table/counter, served timestamp | ❌ | No service data captured |
| FR-SV-04 | Waiter can flag order Returned with reason | ❌ | No return workflow |

#### 6.5 Procurement Module (FR-PR) - **30% Complete**

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-PR-01 | Submit Purchase Budget (items & quantities) | ❌ | No budget module |
| FR-PR-02 | Route Budget to Manager for approval | ❌ | No budget approval workflow |
| FR-PR-03 | Notify Receiving Officer when Budget approved | ❌ | No budget notifications |
| FR-PR-04 | Create PO against approved Budget | ⚠️ PARTIAL | ERP has `POST /procurement/orders` but no budget linkage |
| FR-PR-05 | Generate PO PDF and email to supplier | ❌ | No email integration |
| FR-PR-06 | Manual fallback when supplier has no email | ❌ | No fallback workflow |
| FR-PR-07 | Enter GRN against PO | ⚠️ PARTIAL | ERP has GRN but not linked to Budget/PO flow |
| FR-PR-08 | On GRN post: increase Opening Balance, sync to Pastel, update Budget vs Actual | ❌ | No Pastel sync, no budget tracking |
| FR-PR-09 | Partial GRNs (multiple deliveries against one PO) | ⚠️ PARTIAL | Not explicitly supported |
| FR-PR-10 | 3-way match (PO ↔ GRN ↔ Invoice) | ❌ | No invoice matching |
| FR-PR-11 | Supplier history of POs, GRNs, invoices, disputes | ❌ | No supplier history |

#### 6.6 Inventory: Issuing & Transfers Module (FR-IS) - **20% Complete**

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-IS-01 | Restaurant Issuer: daily Issue Notes from Stores to Kitchen | ❌ | No issue note workflow |
| FR-IS-02 | Unit Issuer: Issue Notes on Tues/Thurs from Stores to Unit | ❌ | No unit ordering |
| FR-IS-03 | Warn Unit Issuer when not Tues/Thu | ❌ | No day-of-week validation |
| FR-IS-04 | Deduct from source, add to destination, sync to Pastel | ❌ | No multi-location tracking, no Pastel sync |
| FR-IS-05 | Inter-unit transfers (Restaurant ↔ Unit) in both directions | ❌ | No transfer functionality |
| FR-IS-06 | Manager approval for transfers above threshold | ❌ | No approval workflow |
| FR-IS-07 | Prevent negative stock without Manager override | ⚠️ PARTIAL | Basic stock checks exist, no override |

#### 6.7 Wastage & Adjustments Module (FR-WA) - **0% Complete**

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-WA-01 | Chef/Storekeeper log extra ingredient usage against active order | ❌ | No extra usage logging |
| FR-WA-02 | Log breakage/spoilage events with reason code | ❌ | No wastage module |
| FR-WA-03 | Maintain configurable reason codes | ❌ | No reason code system |
| FR-WA-04 | Periodic stock-take entry with variance computation | ❌ | No stock-take functionality |
| FR-WA-05 | Manager approval for wastage above threshold | ❌ | No approval workflow |
| FR-WA-06 | Approved wastage posted to stock, audit log, sync to Pastel | ❌ | No wastage processing |
| FR-WA-07 | Wastage Report by reason, item, location, user, period | ❌ | No wastage reports |
| FR-WA-08 | Include wastage in Budget vs Actual | ❌ | No budget tracking |

#### 6.8 Menu & Recipe Management Module (FR-MR) - **0% Complete**

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-MR-01 | Versioned menu items with effective-from/effective-to dates | ❌ | No menu items |
| FR-MR-02 | Versioned recipes; change creates new version | ❌ | No recipe versioning |
| FR-MR-03 | Apply correct recipe version for historical orders | ❌ | No recipe versioning support |
| FR-MR-04 | Draft → Review → Published workflow | ❌ | No recipe workflow |
| FR-MR-05 | No deletion of menu items/recipes with historical transactions | ❌ | No menu items exist |
| FR-MR-06 | Schedule menu items by day/time | ❌ | No scheduling |

#### 6.9 Master Data & Administration (FR-AD) - **50% Complete**

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-AD-01 | Admin manage users and roles | ✅ | ERP has `/auth` and role-based access |
| FR-AD-02 | Maintain Product master (code, name, unit, category, reorder level) | ✅ | ERP has inventory products |
| FR-AD-03 | Maintain Supplier master (name, contact, email, phone, status, terms) | ⚠️ PARTIAL | ERP has suppliers but email not stored |
| FR-AD-04 | Configurable approval thresholds | ❌ | No configurable thresholds |
| FR-AD-05 | Configurable reason-code lists | ❌ | No reason codes |
| FR-AD-06 | Maintain integration settings (POS endpoint, Pastel mode, supplier email) | ❌ | No integration configuration |

#### 6.10 Reporting & Dashboards (FR-RP) - **30% Complete**

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-RP-01 | Stock-on-Hand by location (Stores, Kitchen, Unit) | ❌ | No multi-location stock views |
| FR-RP-02 | Budget vs Actual report | ❌ | No budget tracking, no budget vs actual |
| FR-RP-03 | PO Register by supplier, date, status | ⚠️ PARTIAL | ERP has procurement reports but not full PO register |
| FR-RP-04 | GRN Register by date, supplier, item | ⚠️ PARTIAL | ERP has GRN but not full reporting |
| FR-RP-05 | Issues by Destination (Unit vs Restaurant Kitchen) | ❌ | No issue reporting |
| FR-RP-06 | Wastage Report by reason, item, location, user, period | ❌ | No wastage reporting |
| FR-RP-07 | Service Time report (Ingested → InPrep → Ready → Served) | ❌ | No service time tracking |
| FR-RP-08 | Pastel Reconciliation Report | ❌ | No reconciliation |
| FR-RP-09 | Reports export to PDF and Excel | ⚠️ PARTIAL | ERP has CSV export but not PDF/Excel |

---

## Summary of Gaps

### Critical Gaps (Must-Have for BRD Compliance)

| Module | Status | Impact |
|--------|--------|--------|
| **Kitchen Display & Order Workflow** | ❌ NOT IMPLEMENTED | Core BRD requirement - kitchen fulfillment flow is completely missing |
| **Waiter Service Workflow** | ❌ NOT IMPLEMENTED | Cannot track order delivery and service times |
| **Recipe & Menu Versioning** | ❌ NOT IMPLEMENTED | Cannot support kitchen operations or accurate cost tracking |
| **Multi-Location Inventory (Stores/Kitchen/Unit)** | ❌ NOT IMPLEMENTED | Cannot support 3-location model required by business |
| **Pastel Integration** | ❌ NOT IMPLEMENTED | Cannot sync stock movements to accounting system |
| **Budget → PO Workflow** | ❌ NOT IMPLEMENTED | Cannot control spending or track budgets |
| **Wastage Management** | ❌ NOT IMPLEMENTED | Cannot track stock variances or prepare wastage reports |
| **POS Event Ingestion** | ⚠️ PARTIAL | Sales exist but no push/pull integration mechanism |
| **3-Way Match (PO ↔ GRN ↔ Invoice)** | ❌ NOT IMPLEMENTED | Cannot validate supplier payments |
| **Supplier Email Integration** | ❌ NOT IMPLEMENTED | Cannot automatically send POs to suppliers |

### Partial Implementation

| Module | Current ERP Support | Missing BRD Features |
|--------|--------------------|---------------------|
| **Basic Inventory** | ✅ Products, stock movements, stock levels | No location-specific stock, no recipe-based deduction |
| **Procurement** | ✅ PO creation, GRN | No budget, no supplier email, no 3-way match |
| **Reports** | ✅ Sales, inventory valuation, spend reports | No budget vs actual, no wastage, no service time |
| **Auth & RBAC** | ✅ Users, roles, branch isolation | No restaurant-specific roles (Chef, Waiter, etc.) |
| **Audit Logging** | ✅ Append-only audit | Missing service time and recipe version history |

---

## Implementation Priorities

### Phase 1: Core Restaurant Operations (High Priority)
1. **Kitchen Display Module** - Order ingestion, status management, extra usage logging
2. **Recipe & Menu Management** - Versioned recipes, menu items with effective dates
3. **Multi-Location Inventory** - Stores, Kitchen, Unit stock tracking
4. **Waiter Service Module** - Order delivery tracking, service time capture

### Phase 2: Procurement & Finance (High Priority)
5. **Budget Management** - Submit, approve, track budgets
6. **Pastel Integration** - Real-time stock movement sync
7. **3-Way Match** - PO ↔ GRN ↔ Invoice validation
8. **Supplier Email Integration** - PO PDF generation and email

### Phase 3: Reporting & Analytics (Medium Priority)
9. **Budget vs Actual Reports** - With wastage tracking
10. **Wastage Reports** - By reason, item, location, user
11. **Service Time Reports** - Kitchen performance metrics
12. **Pastel Reconciliation Reports** - Divergence alerts

### Phase 4: Advanced Features (Low Priority)
13. **Recipe Scheduling** - Day/time availability
14. **Configurable Workflows** - Thresholds, reason codes
15. **POS Integration Options** - Push/pull configuration

---

## Technical Debt & Refactoring Needed

### Data Model Changes Required
- Add `Location` entity (Stores, Kitchen, Unit) with stock per location
- Add `Menu Item` entity with recipe linkage
- Add `Recipe Version` entity with effective dates
- Add `Purchase Budget` entity with approval workflow
- Add `Wastage Entry` entity with reason codes
- Add `Stock Take` entity with variance tracking
- Add `Order Status Event` entity for service time tracking

### New Modules Required
- `kitchen` - Order display, status management, extra usage
- `recipes` - Menu items, recipes, versioning
- `budgets` - Budget submission, approval, tracking
- `pastel` - Integration adapter layer
- `wastage` - Breakage, spoilage, stock-take
- `reporting` - Enhanced reports with new data

### Integration Points Needed
- POS event ingestion (push API or pull mechanism)
- Pastel API integration for stock movements
- Email gateway for PO distribution
- PDF generation for PO documents

---

## Conclusion

**Current ERP implementation: ~15-20% aligned with Restaurant BRD requirements**

The existing ERP system provides a solid foundation for inventory and procurement concepts but lacks the restaurant-specific workflows required by the BRD. To achieve full compliance, approximately 80% of new features need to be built, including:

- Complete kitchen fulfillment workflow
- Recipe and menu management system
- Multi-location inventory model
- Pastel integration
- Wastage management
- Service time tracking

The current codebase should be extended with new modules rather than rewritten, as the existing authentication, auditing, reporting infrastructure, and basic inventory patterns can be leveraged.
