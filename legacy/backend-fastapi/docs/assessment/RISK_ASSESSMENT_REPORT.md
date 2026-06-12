# Risk Assessment Report

## Risk Summary By Severity

### Critical
1. Token security default secret present in config defaults.
- Impact: Token forgery risk if default leaks to deployed environment.
- Evidence: app/core/config.py default jwt_secret_key string.
- Mitigation: Enforce non-default secret at startup; fail fast in non-test environments.

2. Refresh token revocation depends on Redis availability.
- Impact: Replay protection weakens when Redis unavailable (degraded mode).
- Evidence: get_redis yields None fallback; auth_service only validates JTI if redis_client is not None.
- Mitigation: Require Redis for auth in production; add strict mode flag.

### High
3. Websocket auth token in query parameter.
- Impact: Token may appear in logs/browser history/proxies.
- Evidence: dashboard_ws reads websocket.query_params token.
- Mitigation: Move token to subprotocol/header during handshake via trusted gateway.

4. Async metadata durability fallback is in-process memory.
- Impact: Job status lookup loss across process restarts/scale-out.
- Evidence: _RECONCILIATION_META_FALLBACK and _REPORT_TASK_META_FALLBACK.
- Mitigation: Persist metadata in Redis/DB only; disable in-memory fallback in production.

5. Broad exception handling in procurement API path.
- Impact: Root cause masking and generic 500 responses.
- Evidence: procurement endpoints catch Exception and map to translate helper.
- Mitigation: Catch explicit domain exceptions and log structured error context.

6. UI does not enforce role-specific navigation.
- Impact: Users can attempt unauthorized actions repeatedly, generating noisy failures.
- Evidence: frontend route protection is auth-only, not role-aware.
- Mitigation: Add role-driven route/action visibility while keeping backend as source of truth.

### Medium
7. Event bus idempotency is process-local only.
- Impact: Duplicate event handling possible in distributed/multi-process deployments.
- Evidence: InProcessEventBus tracks processed_event_ids in memory.
- Mitigation: External dedupe key store or broker-level dedupe strategy.

8. started_at in async payment status not populated.
- Impact: Operational observability gap for job lifecycle.
- Evidence: started_at initialized None and never set.
- Mitigation: propagate Celery task start timestamps from backend state.

9. Search reliability depends on optional ES and fallback query performance.
- Impact: In high-volume systems, SQL fallback may degrade.
- Evidence: search_service fallback path with ilike scans.
- Mitigation: ensure ES availability and DB indexing strategy.

### Low
10. Reports and settings UI pages are shell routes.
- Impact: Feature expectation mismatch for users.
- Evidence: ReportsPage/SettingsPage display shell messages.
- Mitigation: Clarify in release notes or complete feature implementation.

## Edge Cases Identified
- Split payment where all tenders are cash but payment_method split.
- Sale with tax/discount combinations that produce near-zero totals and rounding effects.
- GRN with repeated line references in one request (should be validated for duplicates).
- Async job status polling after worker restart with missing fallback metadata.
- Search query containing only whitespace.

## Potential Race Conditions
- Concurrent sale creation against same stock with aggregate read then write could oversell under high contention.
- Concurrent GRN receipts on same PO line may challenge received_quantity bounds without locking strategy.
- Event handling side effects (audit/cache/websocket) are eventually consistent and not transactionally atomic with primary write.

## Data Corruption Risks
- Redis unavailable mode may desynchronize cache-invalidated expectations and token revocation semantics.
- In-memory task metadata fallback can drift from actual Celery state after restarts.

## Permission Bypass Opportunities (Assessed)
- No direct bypass found in tested endpoint guards; server-side role checks are consistently applied on protected actions.
- Remaining concern is usability/visibility mismatch in UI, not backend bypass.

## Recommended Mitigation Priority
1. Enforce secure JWT secret + strict auth dependency mode.
2. Remove/limit in-memory fallbacks for production.
3. Harden websocket auth transport.
4. Add transaction/locking strategy for high-contention stock and procurement updates.
5. Improve exception taxonomy and structured error observability.
