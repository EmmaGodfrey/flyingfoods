# Integration Test Cases

## API Inventory With Contract Expectations

### Auth
- POST /auth/login
  - Request: { email, password }
  - Response: TokenPair { access_token, refresh_token, token_type, access_expires_in, refresh_expires_in }
  - Auth: none
  - Errors: 401 invalid credentials

- POST /auth/refresh
  - Request: { refresh_token }
  - Response: TokenPair
  - Auth: none (token in body)
  - Errors: 401 invalid/replayed/inactive

- GET /auth/me
  - Request: bearer access token
  - Response: UserRead
  - Errors: 401 token/user invalid

### Inventory
- GET /inventory/products (limit, offset, search, category_id)
- POST /inventory/products
- GET /inventory/products/{product_id}
- PUT /inventory/products/{product_id}
- DELETE /inventory/products/{product_id}
- POST /inventory/movements
- GET /inventory/movements (limit, offset, product_id, movement_type, occurred_after, occurred_before)
- GET /inventory/stock/current
- GET /inventory/stock/low

### Procurement
- POST /procurement/orders
- GET /procurement/orders
- PUT /procurement/orders/{id}/submit
- PUT /procurement/orders/{id}/approve
- POST /procurement/grn
- GET /procurement/reports/orders
- GET /procurement/reports/spend
- POST /procurement/suppliers
- GET /procurement/suppliers
- PUT /procurement/suppliers/{id}
- DELETE /procurement/suppliers/{id}

### Sales
- POST /sales
- GET /sales/summary/daily
- GET /sales/{id}/receipt
- POST /sales/{id}/void
- POST /sales/{id}/refund
- POST /sales/{id}/payments/intent
- POST /sales/{id}/payments/reconcile
- POST /sales/{id}/payments/reconcile/async
- GET /sales/{id}/payments/reconcile/jobs/{job_id}

### Reports
- GET /reports/sales
- GET /reports/sales/export/csv
- GET /reports/inventory/valuation
- GET /reports/inventory/movements
- GET /reports/procurement/spend
- POST /reports/procurement/spend/async
- GET /reports/tasks/{task_id}/status

### Search
- GET /search?q=

### Monitoring/Websocket
- GET /healthz
- GET /metrics
- WS /ws/dashboard?token=

## Endpoint-Level Integration Cases

| Test ID | Endpoint | Scenario | Expected |
|---|---|---|---|
| IT-API-001 | POST /auth/login | valid creds | 200 token pair |
| IT-API-002 | POST /auth/login | invalid creds | 401 |
| IT-API-003 | POST /auth/refresh | valid refresh | 200 rotated pair |
| IT-API-004 | POST /auth/refresh | replay/expired | 401 |
| IT-API-005 | GET /inventory/products | list with search | filtered items + total |
| IT-API-006 | POST /inventory/products | role allowed | 201 + audit event |
| IT-API-007 | POST /inventory/products | role denied | 403 |
| IT-API-008 | GET /inventory/movements | invalid movement_type | 400 |
| IT-API-009 | GET /inventory/stock/current | cache path | consistent stock summary |
| IT-API-010 | POST /procurement/orders | valid refs | 201 draft PO |
| IT-API-011 | PUT /procurement/orders/{id}/submit | wrong status | 409 |
| IT-API-012 | PUT /procurement/orders/{id}/approve | manager role | 403 |
| IT-API-013 | POST /procurement/grn | over-receipt | 400 |
| IT-API-014 | POST /sales | BOM stock sufficient | 201 sale + stock deltas |
| IT-API-015 | POST /sales | stock insufficient | 400 |
| IT-API-016 | POST /sales/{id}/void | first call | 200 voided |
| IT-API-017 | POST /sales/{id}/void | second call | 400 already voided |
| IT-API-018 | POST /sales/{id}/refund | after void | 400 invalid status |
| IT-API-019 | POST /sales/{id}/payments/intent | cash-only sale | 400 |
| IT-API-020 | POST /sales/{id}/payments/reconcile/async | valid ref | 202 + poll to succeeded |
| IT-API-021 | POST /sales/{id}/payments/reconcile/async | mismatched ref | job failed |
| IT-API-022 | GET /audit/logs | manager cross-branch | 403 |
| IT-API-023 | GET /reports/sales/export/csv | valid auth | text/csv payload |
| IT-API-024 | POST /reports/procurement/spend/async | enqueue and poll | task status succeeded |
| IT-API-025 | GET /search | ES unavailable | DB fallback results |
| IT-API-026 | WS /ws/dashboard | valid token + sale/void actions | domain_event + anomaly_alert |

## Non-HTTP Integration Cases

| Test ID | Integration | Scenario | Expected |
|---|---|---|---|
| IT-INFRA-001 | Redis | unavailable | API continues with fallback None |
| IT-INFRA-002 | Celery eager mode | async reconcile/report | deterministic local completion |
| IT-INFRA-003 | Elasticsearch | query failure | warning log + SQL fallback |
| IT-INFRA-004 | Prometheus exporter | repeated scrape | no double counting |
| IT-INFRA-005 | Event bus | one handler fails | other handlers still execute |

## Error Handling Scenarios
- Procurement endpoints map domain exceptions to 400/404/409 with generic 500 fallback.
- Search path falls back rather than hard-failing when ES unavailable.
- Redis dependency yields None on failure, enabling degraded operation.
- Async status APIs return not found when metadata missing or branch mismatch.
