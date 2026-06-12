# Security Test Cases

## Authentication And Token Security

| Test ID | Security Scenario | Steps | Expected Result | Risk If Fails |
|---|---|---|---|---|
| ST-AUTH-001 | Missing bearer token | Call protected endpoint without Authorization header | 401 Missing authorization token | Unauthorized data access |
| ST-AUTH-002 | Invalid JWT signature | Send tampered access token | 401 Invalid access token | Token forgery |
| ST-AUTH-003 | Wrong token type | Use refresh token on protected endpoint | 401 Invalid access token type | Privilege abuse |
| ST-AUTH-004 | Inactive user token | Deactivate user and call endpoint | 401 User not found or inactive | Stale identity access |
| ST-AUTH-005 | Refresh replay | Reuse consumed refresh token with Redis available | 401 Refresh token is no longer valid | Session replay |
| ST-AUTH-006 | Refresh with Redis unavailable | Stop Redis and retry refresh replay | Replay may succeed if no revocation metadata | Elevated replay exposure |

## Authorization And Permission Tests

| Test ID | Scenario | Steps | Expected Result | Risk If Fails |
|---|---|---|---|---|
| ST-RBAC-001 | Manager tries PO approve | PUT /procurement/orders/{id}/approve as manager | 403 Insufficient role | Unauthorized approvals |
| ST-RBAC-002 | Cashier tries report endpoint | GET /reports/sales as cashier | 403 Insufficient role | Data exposure |
| ST-RBAC-003 | Manager cross-branch audit query | GET /audit/logs?branch_id=other | 403 Cross-branch denied | Governance data leak |
| ST-RBAC-004 | Branch B user fetches branch A sale | GET /sales/{id}/receipt with branch mismatch | 404 Sale not found | Tenant boundary breach |
| ST-RBAC-005 | Branch B user search leakage check | /search query for branch A entity | No branch A entities returned | Cross-tenant leak |

## Input Validation And Abuse Cases

| Test ID | Scenario | Steps | Expected Result | Risk If Fails |
|---|---|---|---|---|
| ST-VAL-001 | Empty search query trim bypass | /search?q='   ' | 400 Query must not be empty | Unexpected heavy scans |
| ST-VAL-002 | Invalid datetime filter | /inventory/movements?occurred_after=bad | 400 invalid format | Runtime exception paths |
| ST-VAL-003 | Invalid movement enum | /inventory/movements?movement_type=foo | 400 invalid movement_type | Inconsistent processing |
| ST-VAL-004 | Negative discount in sale create | POST /sales discount_amount < 0 | 422 schema validation | Financial logic corruption |
| ST-VAL-005 | Split tender mismatch | POST /sales split sum != total | 400 validation error | Reconciliation mismatch |
| ST-VAL-006 | GRN over-receipt | POST /procurement/grn exceeds ordered qty | 400 validation error | Inventory inflation |

## Workflow And Integrity Security Tests

| Test ID | Scenario | Steps | Expected Result | Risk If Fails |
|---|---|---|---|---|
| ST-INT-001 | Duplicate void attempt | Void already voided sale | 400 Sale already voided | Double reversal/fraud |
| ST-INT-002 | Duplicate refund attempt | Refund already refunded sale | 400 Sale already refunded | Double reversal/fraud |
| ST-INT-003 | Refund after void | Refund voided sale | 400 invalid status | Illegal state transitions |
| ST-INT-004 | Payment reconcile reference mismatch | Async reconcile with wrong reference | Failed job + explicit error | False reconciliation |
| ST-INT-005 | Audit append-only mutation | Attempt UPDATE/DELETE audit_logs in PostgreSQL | DB trigger exception | Tamperable audit trail |

## Websocket Security Tests

| Test ID | Scenario | Steps | Expected Result | Risk If Fails |
|---|---|---|---|---|
| ST-WS-001 | Missing ws token | Connect /ws/dashboard without token | WS policy violation | Anonymous event tap |
| ST-WS-002 | Invalid ws token | Connect with bad token | WS policy violation | Forged subscriptions |
| ST-WS-003 | Cross-branch event isolation | Open two branch clients and trigger sale in branch A | Only branch A socket gets event | Event leakage |

## Security Risks Identified During Code Review
- Default JWT secret value exists in settings defaults.
- Websocket token passed as query parameter (potential exposure through logs/history if not controlled externally).
- Refresh-token replay resistance degrades when Redis unavailable due to permissive fallback.
- Multiple broad exception handlers can reduce forensic clarity and hide root causes.
- UI does not apply role-based feature hiding; relies fully on backend authorization.
