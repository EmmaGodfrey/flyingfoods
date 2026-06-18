# BRD Compliance Audit

Source reviewed: `Restaurant_Inventory_BRD2.docx`, version 2.0, dated
2026-05-22. Audit performed against the Django/React application on
2026-06-18.

## Summary

The application has the correct domain architecture and covers the main
operational workflows. It is suitable as a development repository, but it is
not yet accurate to call it fully BRD-complete. The largest remaining work is
external integration, offline operation, complete reporting/export coverage,
and a few missing administration screens.

| BRD area | Status | Evidence / remaining work |
|---|---|---|
| POS ingestion | Partial | Push ingestion, dedupe, raw payload, unknown-item flagging, and replay exist. Scheduled pull/import from the POS is not implemented. |
| Kitchen display | Implemented | Orders, recipe deduction, insufficient-stock flagging, lifecycle timestamps, extra usage, out-of-stock flags, and WebSocket updates exist. |
| Waiter service | Implemented | Ready queue, served action, returns, timestamps, and reconnect action queue exist. |
| Inventory locations | Implemented | Stores, Kitchen, and Unit balances use an append-only ledger with document references and an outbox record. |
| Issues and transfers | Implemented | Daily/Tue-Thu rules, off-schedule reasons, bidirectional transfers, threshold approvals, and negative-stock prevention exist. |
| Procurement | Mostly implemented | Budget approval, multi-supplier POs, PDF/email, GRNs, partial receipt tracking, invoice matching, and supplier history exist. Delivery/bounce callbacks and stronger budget allocation controls remain. |
| Wastage and stock-take | Implemented | Extra usage, breakage, spoilage, threshold approval, count sheets, variance posting, audit, and Pastel outbox creation exist. |
| Menu and recipes | Implemented | Versioned recipes, effective dates, Draft/Review/Published workflow, historical order snapshots, and scheduling data exist. |
| Pastel integration | Partial | Transactional outbox, retries, logs, manual resend, configurable modes, and reconciliation exist. The active adapter is still a stub; a real Pastel API/import adapter is required. |
| Master data and roles | Mostly implemented | Eight roles, users, products, suppliers, locations, thresholds, reason codes, and integration settings exist in the API. Some administration UI coverage is incomplete. |
| Reports | Partial | Stock, budget-vs-actual, PO, GRN, issues, wastage, service time, movers, leakage, recipe cost, reorder, and reconciliation selectors/endpoints exist. Confirm every report's PDF and Excel path and add missing UI drill-downs. |
| Security and audit | Mostly implemented | JWT auth, API permissions, encrypted-setting support, audit records, idempotency, and append-only ledger guards exist. Production secret/key policy and a full permission-matrix test remain. |
| Offline availability | Partial | Waiter actions have a reconnect queue. Full local cached operation for kitchen and stores during internet outages is not implemented. |
| Backup/localisation | Operational gap | Settings support timezone and deployment configuration, but backup/restore automation and user-configurable currency/date formatting need deployment work. |

## Data model assessment

The app-per-domain split is appropriate and should be retained. A wholesale
model rewrite would add risk without improving the business fit.

The cleanup adds database-level integrity for positive quantities and costs,
unique products per business-document line set, distinct source/destination
locations, valid recipe date windows, unique location kinds, non-zero ledger
movements, and non-negative configuration values. It also fixes:

- current recipe resolution when a future recipe version is published;
- stock-take sheets omitting active products with no existing balance;
- concurrency-prone `count()+1` purchase-order numbering;
- GRNs accepting lines from another PO or posting without a Stores location;
- unknown menu items being labelled as insufficient stock.

## Release blockers

Before production sign-off:

1. Implement and acceptance-test the real POS pull/import option if the vendor
   cannot push.
2. Replace the Pastel stub with the agreed API or import adapter.
3. Prove report PDF/Excel parity and drill-downs on a signed-off dataset.
4. Complete role-by-role API and screen permission tests.
5. Decide and implement the required offline/local-network mode.
6. Document backup, restore, secrets, monitoring, and deployment procedures.
