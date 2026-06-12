# ERP Delivery TODO + Interactive Workflow

This document tracks:
- Past completed work
- Current blocked/pending work
- Future roadmap work
- User input required for each step
- Execution process and validation checklist

## 1) Completed Work (Past TODOs)

### Done: Plan parity and backend milestones
- [x] Week 3 index strategy completed and validated (including EXPLAIN script path).
- [x] Week 6 procurement backend completed (PO, submit, approve, GRN, reporting).
- [x] Week 11 procurement UI core flows completed in web app.
- [x] Week 11 supplier CRUD/search backend + UI completed.
- [x] Week 15 search backend + UI completed with Elasticsearch integration path.
- [x] Week 16 procurement spend reporting moved to GRN/PO data source.
- [x] Regression tests and frontend build passed for changed slices.

### Done: Infrastructure/code additions
- [x] Elasticsearch config/dependency/service wiring added.
- [x] Search indexing tasks and indexing helpers added.
- [x] Search response upgraded with highlights support.
- [x] Backfill script added for search index population.

### Done: Week 8 frontend skeleton + auth completion
- [x] Added protected route architecture with login page and `PrivateRoute` guard.
- [x] Added in-memory token session store via Zustand and auth context provider.
- [x] Wired app bootstrap with `react-router-dom` and `@tanstack/react-query` providers.
- [x] Added centralized toast error surface (`sonner`) for API failures.
- [x] Implemented module-per-domain API layer (`api/modules/auth|inventory|sales|procurement|search`).
- [x] Updated shell nav coverage to include Dashboard, Inventory, POS, Procurement, Reports, Settings.
- [x] Converted shell navigation from local-tab state to URL-routed sections (`/dashboard`, `/products`, `/movements`, `/pos`, `/procurement`, `/reports`, `/settings`).
- [x] Frontend build validated after refactor.

#### Week 8 validation snapshot
1. Command run: `npm run build` (in `erp-web`)
2. Result: success
3. Bundle output generated under `erp-web/dist`

## 2) Active Pending Items (Need User-Driven Completion)

### Pending A: Run Elasticsearch live and populate index
Status: blocked on local Docker availability.

#### User input required
1. Confirm Docker Desktop is installed and running.
2. Confirm you want Elasticsearch-only startup or full stack startup.
3. Confirm whether to run against local dev database now.

#### Process to complete
1. Start Elasticsearch service:
   - cd erp
   - docker compose up -d elasticsearch
2. Verify Elasticsearch health:
   - docker compose ps elasticsearch
   - curl or Invoke-WebRequest to http://localhost:9200/_cluster/health
3. Backfill search index:
   - cd erp
   - set PYTHONPATH=.
   - run: python scripts/week15_backfill_search_index.py
4. Validate indexed search behavior:
   - call API: GET /search?q=burge
   - confirm grouped results returned for products/suppliers/invoices
   - confirm highlights are present in response where matched

#### Completion criteria
- Elasticsearch responds on port 9200.
- Backfill runs with non-error completion.
- Search endpoint returns fuzzy/highlighted matches from index.

### Pending B: Populate meaningful data for live search demo
Status: not blocked, but needs user decision.

#### User input required
1. Approve whether to use seed fixtures or real sample business data.
2. Provide preferred branch/user login for demo.

#### Process to complete
1. Insert/seed sample products, suppliers, and sales with realistic names.
2. Re-run backfill.
3. Test several typo/fuzzy queries (example: burge, acm, 9001).
4. Capture expected screenshots or API payload snapshots.

#### Completion criteria
- At least 1 result appears in each category for demo queries.
- Fuzzy query typo still returns intended records.

## 3) Future TODOs (Need Your Direction Before Execution)

### Future 1: Week 16 offline POS implementation (original roadmap)
Status: not started.

#### User input required
1. Confirm if you want Flutter implementation started now.
2. Confirm target platform priority (Android first, desktop test shell, or both).
3. Confirm sync conflict policy preference.

#### Proposed process
1. Scaffold Flutter app and local SQLite schema.
2. Implement offline checkout flow and pending-sales queue.
3. Build sync engine to post pending sales when online.
4. Add conflict handling + manager review UX.
5. Run acceptance test scenarios offline/online transitions.

#### Completion criteria
- Sales can be created fully offline.
- Pending queue syncs correctly when connectivity returns.
- Conflict cases are surfaced for manager action.

### Future 2: Search UX deepening in web app
Status: partial (core is done).

#### User input required
1. Choose preferred result interaction:
   - inline detail panel
   - route navigation to tab and entity
   - modal preview
2. Confirm whether to render highlight HTML formatting in UI.

#### Proposed process
1. Implement click-through navigation by result route/type.
2. Add grouped dropdown and keyboard navigation.
3. Optionally render highlighted fragments.
4. Add frontend tests for interaction behavior.

#### Completion criteria
- Selecting a search result takes the user to actionable detail state.
- Keyboard and mouse interaction both work smoothly.

### Future 3: Final release hardening and operational runbook
Status: partially done.

#### User input required
1. Confirm target deployment environment (local server/cloud provider).
2. Confirm acceptable downtime window for release.
3. Confirm observability/alerting thresholds.

#### Proposed process
1. Finalize env configuration and deployment checklist.
2. Run migration preflight and smoke tests.
3. Run performance tests and tune hot queries.
4. Publish handoff and rollback runbook.

#### Completion criteria
- Deployment checklist passes end-to-end.
- Monitoring and rollback paths are documented and tested.

## 4) Execution Template For Any New Task

Use this interactive pattern each time:
1. Define scope and acceptance criteria.
2. Collect required user inputs and approvals.
3. Implement in small verified increments.
4. Run targeted tests and build checks.
5. Record outcome and next action in this file.

## 5) Next Action Waiting For You

Please provide these inputs so the next live step can be executed immediately:
1. Is Docker Desktop installed and running now? (yes/no)
2. Should I start Elasticsearch only, or full docker-compose stack?
3. Should I seed demo data first, or validate search with existing data first?

## 6) Work Log (Latest Delta)

- Added dependencies: `react-router-dom`, `@tanstack/react-query`, `zustand`, `sonner`.
- Added new files: auth context/store, router guards, login page, API transport/modules.
- Refactored API client to delegate to module files with centralized transport handling.
- Kept existing Week 9+ functional surfaces while introducing Week 8 architecture requirements.
- Recovered `erp-web/src/App.tsx` after patch corruption, completed section-page wiring, and revalidated frontend build (`npm run build` passed).
- Completed all-UI route smoke pass (login + dashboard + products + movements + POS + procurement + reports + settings) with mocked API transport; all sections rendered and navigated successfully.
