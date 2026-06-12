# Permission Matrix

## Role Mapping Used
- Admin: admin + superadmin (superadmin treated as superset)
- Manager: manager
- Staff: inventory_officer and cashier combined (not a single DB role)
- User: authenticated frontend user without guaranteed role privileges
- API: non-UI clients using JWT roles

## Feature Access Matrix

| Feature | Admin | Manager | Staff | User | API |
|---|---|---|---|---|---|
| Login/Refresh/Profile | Yes | Yes | Yes | Yes | Yes |
| List Products | Yes | Yes | Yes | Yes (if authenticated) | Yes |
| Create/Update Product | Yes | Yes | Yes (inventory_officer) | No guaranteed | Yes (role-bound) |
| Delete Product | Yes | Yes | No | No | Yes (admin/manager) |
| Create Stock Movement | Yes | Yes | Yes (inventory_officer/cashier) | No guaranteed | Yes (role-bound) |
| View Stock/Movements/Low Stock | Yes | Yes | Yes | Yes (if authenticated) | Yes |
| Create Supplier | Yes | Yes | No | No | Yes (role-bound) |
| Update/Delete Supplier | Yes | Yes | No | No | Yes (role-bound) |
| Create PO | Yes | Yes | No | No | Yes (role-bound) |
| Submit PO | Yes | Yes | No | No | Yes (role-bound) |
| Approve PO | Yes | No | No | No | Yes (admin/superadmin) |
| Create GRN | Yes | Yes | Yes (inventory_officer) | No | Yes (role-bound) |
| POS Sale Create | Yes | Yes | Yes (cashier) | No | Yes (role-bound) |
| POS Void/Refund | Yes | Yes | Yes (cashier) | No | Yes (role-bound) |
| Payment Intent/Reconcile | Yes | Yes | Yes (cashier) | No | Yes (role-bound) |
| Sales/Inventory/Procurement Reports | Yes | Yes | No | No | Yes (admin/manager/superadmin) |
| Audit Log Query | Yes | Yes (own branch) | No | No | Yes (role-bound) |
| Global Search | Yes | Yes | Yes | No guaranteed | Yes |
| Monitoring /metrics | Internal | Internal | Internal | N/A | N/A |
| Websocket dashboard | Yes | Yes | Yes | Yes if token valid | Yes |

## Findings

### Missing Permissions (Functional Gaps)
- No dedicated read-only auditor role; audit is tied to admin/manager role strings.
- No explicit end-user/business-user role model in backend role enum beyond operational roles.

### Excessive Permissions
- Cashier can create generic inventory stock movement, which may be broader than strict POS duties.
- Authenticated users can access some read endpoints without explicit role gating (still branch-scoped).

### Potential Security Risks
- Frontend exposes tabs regardless of role; backend rejects unauthorized actions but UX may encourage probing.
- Staff role is composite in practice; policy drift can occur if inventory_officer and cashier expectations diverge.

## Role-Based Testing Matrix (Requested Format)

| Feature | Admin | Manager | Staff | User | API |
|---|---|---|---|---|---|
| Create Record | Yes | Yes | Partial | No | Yes |
| Approve Workflow Step | Yes | No | No | No | Yes |
| Reverse Sale | Yes | Yes | Partial | No | Yes |
| Access Audit | Yes | Partial (branch-limited) | No | No | Yes |
| Run Reports | Yes | Yes | No | No | Yes |
