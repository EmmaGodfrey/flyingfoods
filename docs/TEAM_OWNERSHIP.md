# Three-Developer Ownership Plan

This plan divides the system by business workflow. Each developer owns the
backend, frontend, tests, and BRD traceability for their stream. Replace
`Developer A/B/C` with names and GitHub handles when assignments are confirmed.

## Working model

- Each developer works from one long-lived dedicated branch created from
  `dev`.
- Developers commit their assigned fixes and requirements directly to their
  dedicated branch; do not create feature branches.
- Open pull requests from each dedicated branch into `dev`.
- Do not push development work directly to `dev` or `main`.
- A successful merge to `dev` deploys automatically to the development server.
- Promote tested releases from `dev` to `main`.
- The primary owner implements and verifies changes.
- The secondary owner reviews changes that cross a domain boundary.
- A model or API contract change requires review from every affected owner.

Dedicated branches:

```text
dev-service
dev-stock
dev-finance
```

Branch assignment:

- Developer A uses `dev-service`.
- Developer B uses `dev-stock`.
- Developer C uses `dev-finance`.

Before starting a new issue, update the dedicated branch from `dev`:

```bash
git switch dev
git pull origin dev
git switch dev-service  # or dev-stock / dev-finance
git merge dev
git push origin HEAD
```

After a pull request is merged, repeat this synchronization before beginning
the next issue. Do not keep stacking unrelated completed work on a branch that
is behind `dev`.

Commits still need to be issue-focused:

```text
fix(stock): prevent duplicate transfer posting
feat(service): add POS pull ingestion
change(finance): apply invoice-match tolerance
```

## Developer A — Service Operations and Menu

Business responsibility: POS sale arrival through kitchen preparation and
waiter service, including the recipe snapshot used by each order.

Primary backend ownership:

- `backend/apps/pos_ingest/`
- `backend/apps/kitchen/`
- `backend/apps/menu/`
- `backend/apps/notifications/`

Primary frontend ownership:

- `frontend/src/features/kitchen/`
- `frontend/src/features/waiter/`
- `frontend/src/features/menu/`
- real-time connection and offline action behavior for these screens

Primary requirements:

- FR-PI: POS integration
- FR-KD: Kitchen Display
- FR-SV: Waiter/service workflow
- FR-MR: Menu and recipe versioning

Immediate audit backlog:

1. Implement and test the POS pull/import path.
2. Test unknown items, replay, duplicate delivery, and insufficient stock
   end-to-end.
3. Verify every order transition and concurrent Served action.
4. Complete kitchen/waiter offline and reconnection behavior.
5. Verify recipe publication, future effective dates, schedules, and
   historical recipe snapshots.
6. Add frontend tests for kitchen, waiter, and menu critical paths.

Secondary reviewer: Developer B for stock deductions and extra usage.

## Developer B — Inventory Controls and Approvals

Business responsibility: every internal stock movement and adjustment,
including the approval controls that prevent silent leakage.

Primary backend ownership:

- `backend/apps/inventory/`
- `backend/apps/wastage/`
- approval, threshold, reason-code, audit, and idempotency logic in
  `backend/apps/core/`

Primary frontend ownership:

- `frontend/src/features/stock/`
- `frontend/src/features/issues/`
- `frontend/src/features/wastage/`
- `frontend/src/features/approvals/`

Primary requirements:

- FR-IS: Issues and inter-unit transfers
- FR-WA: Wastage, breakage, and stock-take
- FR-031: Shared approval mechanism
- stock-ledger and negative-stock invariants

Immediate audit backlog:

1. Verify issue and transfer source/destination rules for all roles.
2. Complete the Manager negative-stock override workflow.
3. Test approval races, rejection/investigation paths, and duplicate posting.
4. Verify stock-take behavior when movements happen during a count.
5. Enforce and test purchase/stock/recipe UoM conversions.
6. Complete stores/inventory offline behavior.
7. Add role and API tests for stock, wastage, and approval endpoints.

Secondary reviewer: Developer C for GRN and Pastel movement effects.

## Developer C — Procurement, Finance, Reporting, and Administration

Business responsibility: budget through supplier invoice, accounting
synchronisation, management reporting, and administrative master data.

Primary backend ownership:

- `backend/apps/procurement/`
- `backend/apps/pastel/`
- `backend/apps/reports/`
- `backend/apps/masterdata/`
- `backend/apps/users/`

Primary frontend ownership:

- `frontend/src/features/procurement/`
- `frontend/src/features/reports/`
- `frontend/src/features/admin/`
- `frontend/src/features/auth/`

Primary requirements:

- FR-PR: Procurement
- FR-PA: Pastel integration
- FR-RP: Reports and dashboards
- FR-AD: Master data, users, roles, and integration settings

Immediate audit backlog:

1. Add approved-budget allocation controls across multiple POs.
2. Verify partial/over receipts, variance reasons, and invoice match
   tolerances.
3. Implement delivery/bounce feedback for supplier PO emails.
4. Replace the Pastel stub with the agreed real adapter.
5. Prove retry, resend, reconciliation, and zero-duplicate guarantees.
6. Validate every report against a signed-off fixture and confirm PDF/Excel
   parity.
7. Complete missing administration UI and the role-permission matrix.

Secondary reviewer: Developer B for all stock-producing procurement actions.

## Shared platform files

These files are not general free-for-all areas:

| Area | Steward | Required reviewer |
|---|---|---|
| `backend/config/`, auth/session security | Developer C | Developer A |
| `backend/apps/core/models.py` base/audit/outbox structures | Developer B | affected stream owner |
| `frontend/src/app/`, `frontend/src/lib/`, shared UI | Developer A | affected stream owner |
| Docker, deployment, GitHub Actions | Developer C | one other developer |
| BRD/specification documents | requirement owner | both affected owners |

For a cross-domain bug, ownership follows the source of the incorrect write,
not the screen where the symptom appeared. Examples:

- Wrong recipe deduction: Developer A, reviewed by Developer B.
- GRN increases the wrong balance: Developer C, reviewed by Developer B.
- Correct ledger but wrong report total: Developer C.
- Approval decision posts twice: Developer B.

## Issue triage

Every issue must contain:

```text
Observed:
Expected:
Role:
Steps to reproduce:
Environment/data:
Requirement ID:
Owning stream:
Affected domains:
Evidence:
Acceptance tests:
```

Use these priorities:

- `P0`: security incident, data corruption, or entire system unavailable
- `P1`: core sale, stock, or procurement flow blocked; no safe workaround
- `P2`: incorrect behavior with a workaround
- `P3`: usability, reporting presentation, or low-risk improvement

Use these labels:

```text
stream:service
stream:stock
stream:finance
type:bug
type:requirement-change
type:technical-debt
cross-domain
needs-stakeholder-decision
```

## Requirement-change workflow

Requirements will change. Do not implement a verbal change directly.

1. Record the current BRD ID and requested new behavior in an issue.
2. State whether the change replaces, extends, or contradicts the BRD.
3. Identify affected models, APIs, screens, roles, reports, and integrations.
4. Add Given/When/Then acceptance criteria.
5. Get stakeholder confirmation where business behavior changes.
6. Update the relevant specification and API/data-model contract in the same
   pull request as the implementation.
7. Add migration/backfill and rollback notes for persisted-data changes.
8. Obtain review from each affected stream owner.

## Pull-request completion checklist

- Requirement or bug is reproducible before the change.
- Tests fail before and pass after the change.
- Permissions include allowed and forbidden roles.
- Duplicate/retry behavior is tested for write operations.
- Stock-changing code goes through `post_movements()`.
- Historical records are not silently rewritten.
- Migration and existing-data impact are documented.
- Frontend loading, empty, error, and reconnect states are covered.
- Relevant BRD/spec/API documentation is updated.
- Development deployment smoke test passes.

## Weekly coordination

Hold one short triage session:

1. Review new P0/P1 bugs and requirement changes.
2. Assign one owner and one reviewer to cross-domain issues.
3. Identify migrations or API changes likely to block another developer.
4. Confirm the three highest-priority outcomes for the week.
5. Demo merged behavior on the development environment against acceptance
   criteria, not only screenshots.

The dedicated branches are broad by design, but the work on them must not be.
Each active issue needs one owner, focused commits, a pull-request description,
and a testable outcome. Open or refresh the pull request after each coherent
batch instead of accumulating weeks of unrelated changes.
