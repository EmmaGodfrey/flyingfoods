# API Contracts: Flying Foods Restaurant & Inventory Management System

Base path `/api/`. All responses use the envelope `{"success": true, "data": ...}` or `{"success": false, "error": {"code": "...", "message": "..."}}`. All list endpoints paginated (`?page=`, `?page_size=`, response `{count, next, previous, results}` inside `data`). All endpoints require `Authorization: Bearer <access>` unless marked public. Role permissions per endpoint group are listed; ADMIN passes everywhere. Write endpoints that post stock accept an optional `Idempotency-Key` header.

## auth (public where noted)

| Method | Path | Body / Notes | Roles |
|---|---|---|---|
| POST | `/auth/login/` | `{email, password}` → access in body, refresh as httpOnly cookie | public |
| POST | `/auth/refresh/` | cookie → new access + rotated refresh cookie | public (cookie) |
| POST | `/auth/logout/` | blocklists refresh | any |
| GET | `/auth/me/` | current user + role | any |

## users (FR-AD-01)

| Method | Path | Notes | Roles |
|---|---|---|---|
| GET/POST | `/users/` | list (filter: role, is_active) / create | ADMIN |
| GET/PATCH | `/users/{id}/` | edit, deactivate via `is_active` | ADMIN |

## masterdata (FR-AD-02/03)

| Method | Path | Notes | Roles |
|---|---|---|---|
| GET/POST, GET/PATCH | `/products/`, `/products/{id}/` | filters: category, is_active, below_reorder; UoM fields included | read: any; write: ADMIN |
| GET/POST, GET/PATCH | `/suppliers/`, `/suppliers/{id}/` | deactivate-not-delete enforced | read: RECEIVING_OFFICER+MANAGER; write: ADMIN |
| GET | `/locations/` | seeded three locations | any |
| GET/POST/PATCH | `/reason-codes/`, `/thresholds/` | FR-AD-04/05 | read: any; write: ADMIN |
| GET/PUT | `/integration-settings/` | POS mode/endpoint, Pastel mode, email gateway (FR-AD-06) | ADMIN |
| GET | `/integration-health/` | POS ingest + Pastel sync status, failure counts (US-ADM-04) | ADMIN |

## menu (FR-MR)

| Method | Path | Notes | Roles |
|---|---|---|---|
| GET/POST, GET/PATCH | `/menu-items/`, `/menu-items/{id}/` | delete returns 409 `MENU_ITEM_HAS_HISTORY` → deactivate | read: any; write: ADMIN |
| GET/POST | `/menu-items/{id}/recipe-versions/` | POST creates next version (DRAFT) | ADMIN |
| POST | `/recipe-versions/{id}/submit-review/`, `/publish/` | workflow transitions; publish requires effective_from | ADMIN |
| GET | `/recipe-versions/{id}/` | lines included | any |

## pos_ingest (FR-PI)

| Method | Path | Notes | Roles |
|---|---|---|---|
| POST | `/pos/sale-events/` | push ingestion; body `{pos_sale_id, sold_at, cashier, lines:[{pos_code, qty, modifiers, price}], totals}`; 200 + same order on duplicate `pos_sale_id` (idempotent); 202 FLAGGED if unknown item | POS service account |
| GET | `/pos/sale-events/` | filter: status, date; raw payload viewable | ADMIN |
| POST | `/pos/sale-events/{id}/replay/` | re-trigger ingestion, logs replayer (FR-PI-06) | ADMIN |

## kitchen + waiter (FR-KD, FR-SV)

| Method | Path | Notes | Roles |
|---|---|---|---|
| GET | `/kitchen/orders/` | active orders, filter: status | CHEF, STOREKEEPER, MANAGER |
| POST | `/kitchen/orders/{id}/start/` | → IN_PREPARATION | CHEF |
| POST | `/kitchen/orders/{id}/ready/` | → READY; 409 `APPROVAL_PENDING` if unresolved extra-usage approval | CHEF |
| POST | `/kitchen/orders/{id}/extra-usage/` | `{product, qty, reason_code}`; auto approval routing | CHEF, STOREKEEPER |
| POST | `/kitchen/out-of-stock/` / DELETE `/kitchen/out-of-stock/{id}/` | flag/clear menu item (FR-KD-06) | CHEF |
| GET | `/waiter/orders/` | READY orders, oldest first, time-since-ready | WAITER, MANAGER |
| POST | `/waiter/orders/{id}/served/` | records waiter, table, timestamp; second call 409 `ALREADY_SERVED` | WAITER |
| POST | `/waiter/orders/{id}/return/` | `{reason_code}` → back to IN_PREPARATION, chef alerted | WAITER |
| WS | `/ws/kitchen/`, `/ws/waiter/` | JSON events `{type: "order.created"|"order.status", order_id}` — notification only, client refetches | role-scoped |

## inventory (FR-IS)

| Method | Path | Notes | Roles |
|---|---|---|---|
| GET | `/stock/balances/` | filter: location, category, below_reorder | STOREKEEPER, MANAGER, issuers |
| GET | `/stock/movements/` | ledger, filter: product, location, type, document, date | STOREKEEPER, MANAGER |
| POST | `/issues/` | `{source, destination, lines, off_schedule_reason?}`; Unit on non-Tue/Thu without reason → 400 `OFF_SCHEDULE_REASON_REQUIRED` (warn-not-block via reason) | RESTAURANT_ISSUER (→Kitchen), UNIT_ISSUER (→Unit) |
| POST | `/issues/{id}/post/` | posts movements; negative stock → 409 `INSUFFICIENT_STOCK` unless `override_requested` → creates Approval | as above |
| POST | `/transfers/` + `/transfers/{id}/post/` | Kitchen↔Unit; above threshold → PENDING_APPROVAL | issuers |
| POST | `/stock-takes/` | opens count, freezes system qty | STOREKEEPER |
| PUT | `/stock-takes/{id}/lines/` | submit counts | STOREKEEPER |
| POST | `/stock-takes/{id}/post/` | computes variance, threshold-routes, posts adjustment | STOREKEEPER |

## procurement (FR-PR)

| Method | Path | Notes | Roles |
|---|---|---|---|
| GET/POST | `/budgets/` | create draft with lines | any authorised role (FR-PR-01) |
| POST | `/budgets/{id}/submit/` | → Approval engine, Manager notified | requester |
| GET/POST | `/purchase-orders/` | create against APPROVED budget; lines may split suppliers across POs | RECEIVING_OFFICER |
| POST | `/purchase-orders/{id}/send/` | generates PDF, emails supplier, logs send; no email → status MANUAL_CONTACT_REQUIRED (FR-PR-05/06) | RECEIVING_OFFICER |
| GET | `/purchase-orders/{id}/pdf/` | download stored PDF | RECEIVING_OFFICER, MANAGER |
| POST | `/purchase-orders/{id}/grns/` | partial GRNs; posting updates fulfilled qty, stock, Budget vs Actual | RECEIVING_OFFICER |
| POST | `/purchase-orders/{id}/invoices/` | enter invoice → 3-way match result; discrepancies flagged (FR-PR-10) | RECEIVING_OFFICER |
| POST | `/invoice-matches/{id}/resolve|dispute|escalate/` | resolution flow | RECEIVING_OFFICER, MANAGER |
| GET | `/suppliers/{id}/history/` | POs, GRNs, invoices, disputes (FR-PR-11) | RECEIVING_OFFICER, MANAGER |

## wastage (FR-WA)

| Method | Path | Notes | Roles |
|---|---|---|---|
| GET/POST | `/wastage/` | `{entry_type, product, location, qty, reason_code, note?, order?}`; threshold-routed | CHEF (extra usage), STOREKEEPER |

## approvals (FR-031, cross-cutting)

| Method | Path | Notes | Roles |
|---|---|---|---|
| GET | `/approvals/` | pending queue, filter: scope, status, period | MANAGER |
| POST | `/approvals/{id}/approve|reject|investigate/` | reason required on reject | MANAGER |

## pastel (FR-PA)

| Method | Path | Notes | Roles |
|---|---|---|---|
| GET | `/pastel/sync-log/` | filter: status, date, entity | ADMIN |
| POST | `/pastel/outbox/{id}/resend/` | manual re-send after correction (FR-PA-05) | ADMIN |
| GET | `/pastel/reconciliation/` | latest run + divergent lines (FR-PA-06) | ADMIN, MANAGER |

## notifications

| Method | Path | Notes | Roles |
|---|---|---|---|
| GET | `/notifications/` | own, filter unread | any |
| POST | `/notifications/{id}/read/` | | any |

## reports (FR-RP) — all support `?format=json|pdf|xlsx` (FR-RP-09)

| Path | Report | Roles |
|---|---|---|
| `/reports/stock-on-hand/?location=&date=` | FR-RP-01 | STOREKEEPER, MANAGER |
| `/reports/budget-vs-actual/?from=&to=` | FR-RP-02, drill-down links | MANAGER |
| `/reports/po-register/`, `/reports/grn-register/` | FR-RP-03/04 | RECEIVING_OFFICER, MANAGER |
| `/reports/issues-by-destination/` | FR-RP-05 | MANAGER |
| `/reports/wastage/?by=reason|item|location|user` | FR-RP-06 | STOREKEEPER, CHEF, MANAGER |
| `/reports/service-time/?shift=` | FR-RP-07 | MANAGER |
| `/reports/pastel-reconciliation/` | FR-RP-08 | ADMIN, MANAGER |
| `/reports/movers/?period=` | slow/fast movers | MANAGER |
| `/reports/leakage/?from=&to=` | theoretical vs actual (enhancement) | MANAGER |
| `/reports/recipe-costing/` | plate cost + margin (enhancement) | MANAGER |
| `/reports/reorder-suggestions/` | enhancement | RECEIVING_OFFICER, MANAGER |

## Error codes (non-exhaustive)

`VALIDATION_ERROR` 400 · `OFF_SCHEDULE_REASON_REQUIRED` 400 · `AUTH_REQUIRED` 401 · `FORBIDDEN_ROLE` 403 · `NOT_FOUND` 404 · `MENU_ITEM_HAS_HISTORY` 409 · `INSUFFICIENT_STOCK` 409 · `APPROVAL_PENDING` 409 · `ALREADY_SERVED` 409 · `DUPLICATE_SALE_EVENT` 200 (idempotent success) · `RECIPE_VERSION_IMMUTABLE` 409 · `INTERNAL_ERROR` 500 (no internals leaked)
