# UAT Test Cases

## Instructions
- Execute tasks using role-specific accounts.
- Record Pass/Fail and notes for each acceptance criterion.
- Any failure in Critical tasks blocks UAT sign-off.

## Admin UAT Checklist

| Task | Expected Outcome | Acceptance Criteria | Pass/Fail |
|---|---|---|---|
| Login and view profile | Token issued and /auth/me returns admin context | Login succeeds in <= 3s | |
| Approve submitted PO | PO status transitions to approved | Only admin/superadmin can approve | |
| Query audit logs for another branch | Allowed with branch parameter | 200 response with filtered rows | |
| Run sales report CSV export | Downloadable CSV with matching totals | Header and values consistent with JSON report | |
| Trigger async procurement report and poll status | Task reaches succeeded | Result rows rendered and branch-scoped | |

## Manager UAT Checklist

| Task | Expected Outcome | Acceptance Criteria | Pass/Fail |
|---|---|---|---|
| Create product | Product appears in products list | Product persisted and searchable | |
| Create purchase order draft and submit | Status draft -> submitted | Submit blocked if not draft | |
| Record GRN for approved PO | Stock increases and PO closes/received | Received qty never exceeds ordered qty | |
| Create POS sale with split tender | Receipt includes tax/discount/payment_tenders | Tender sum equals total | |
| Void sale and confirm stock restoration | Sale status voided, stock reverts | Double void blocked | |
| Search product/supplier/invoice globally | Search returns branch-only items | No cross-branch leakage | |

## Inventory Officer UAT Checklist

| Task | Expected Outcome | Acceptance Criteria | Pass/Fail |
|---|---|---|---|
| Update product pricing/reorder level | Product updates saved | Role can edit but not delete product | |
| Create stock movement receive | Movement history updates | Movement appears with reference_id | |
| List procurement orders | Orders visible for branch | Pagination/filtering works | |
| Record GRN | GRN created and stock updated | Over-receipt prevented with error | |

## Cashier UAT Checklist

| Task | Expected Outcome | Acceptance Criteria | Pass/Fail |
|---|---|---|---|
| Create sale | Receipt generated with line totals | Stock deducted correctly | |
| Fetch receipt by sale id | Receipt matches checkout values | 404 for unknown sale id | |
| Run payment intent | Authorization references returned | Cash-only sale rejected | |
| Enqueue async payment reconcile | Job status progresses to succeeded/failed | Failure contains meaningful error | |
| Refund sale | Sale status refunded and stock restored | Refund after void blocked | |

## Auditor Persona UAT Checklist (Admin/Manager-backed)

| Task | Expected Outcome | Acceptance Criteria | Pass/Fail |
|---|---|---|---|
| Filter audit by actor/action/entity/date | Correct subset returned | Pagination deterministic | |
| Verify hash chain fields present | hash_chain_prev/hash_chain_curr visible | Every row has hash_chain_curr | |
| Attempt cross-branch query as manager | Denied | 403 Cross-branch audit access denied | |

## API Consumer UAT Checklist

| Task | Expected Outcome | Acceptance Criteria | Pass/Fail |
|---|---|---|---|
| Authenticate and call protected endpoint | 200 with bearer token | 401 without token | |
| Handle token refresh | Session recovered on 401 refresh flow | Tokens rotated and requests retried | |
| Consume websocket dashboard events | Receives connection and domain events | Invalid token rejected | |

## Acceptance Exit Criteria
- All Critical tasks pass.
- No unresolved High severity defects in sales/procurement/audit/auth flows.
- Branch isolation checks pass for all tested roles.
