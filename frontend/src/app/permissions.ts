/** Client-side capability checks, mirroring the backend role permissions.
 *
 * These gate UI affordances only — the API enforces the same rules, so a
 * disabled or hidden button is convenience, not security.
 */

import type { Role } from "../types";

const ISSUERS: Role[] = ["STOREKEEPER", "RESTAURANT_ISSUER", "UNIT_ISSUER", "ADMIN"];
const APPROVERS: Role[] = ["MANAGER", "ADMIN"];

/** May create and post issues and transfers. */
export function canIssue(role?: Role): boolean {
  return !!role && ISSUERS.includes(role);
}

/** May approve, reject, or investigate items in the approval queue. */
export function canApprove(role?: Role): boolean {
  return !!role && APPROVERS.includes(role);
}
