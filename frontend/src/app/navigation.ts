/** Navigation model: which sections each role sees, and where each lands. */

import {
  BarChart3,
  Boxes,
  ChefHat,
  ClipboardList,
  ConciergeBell,
  FileText,
  type LucideIcon,
  PackageSearch,
  Settings,
  ShoppingCart,
  Trash2,
} from "lucide-react";

import type { Role } from "../types";

export interface NavSection {
  key: string;
  label: string;
  path: string;
  icon: LucideIcon;
  roles: Role[];
}

const ALL: Role[] = [
  "CHEF",
  "WAITER",
  "STOREKEEPER",
  "RECEIVING_OFFICER",
  "UNIT_ISSUER",
  "RESTAURANT_ISSUER",
  "MANAGER",
  "ADMIN",
];

// Least-privilege: each role sees only the sections it operates. ADMIN sees all.
export const NAV_SECTIONS: NavSection[] = [
  { key: "kitchen", label: "Kitchen", path: "/kitchen", icon: ChefHat, roles: ["CHEF", "ADMIN"] },
  { key: "waiter", label: "Service", path: "/waiter", icon: ConciergeBell, roles: ["WAITER", "ADMIN"] },
  { key: "stock", label: "Stock", path: "/stock", icon: Boxes, roles: ["STOREKEEPER", "RECEIVING_OFFICER", "UNIT_ISSUER", "RESTAURANT_ISSUER", "MANAGER", "ADMIN"] },
  { key: "issues", label: "Issues & Transfers", path: "/issues", icon: ClipboardList, roles: ["STOREKEEPER", "UNIT_ISSUER", "RESTAURANT_ISSUER", "ADMIN"] },
  { key: "procurement", label: "Procurement", path: "/procurement", icon: ShoppingCart, roles: ["RECEIVING_OFFICER", "MANAGER", "ADMIN"] },
  { key: "wastage", label: "Wastage", path: "/wastage", icon: Trash2, roles: ["CHEF", "STOREKEEPER", "ADMIN"] },
  { key: "menu", label: "Menu & Recipes", path: "/menu", icon: PackageSearch, roles: ["MANAGER", "ADMIN"] },
  { key: "approvals", label: "Approvals", path: "/approvals", icon: FileText, roles: ["MANAGER", "ADMIN"] },
  { key: "reports", label: "Reports", path: "/reports", icon: BarChart3, roles: ["MANAGER", "ADMIN"] },
  { key: "admin", label: "Administration", path: "/admin", icon: Settings, roles: ["ADMIN"] },
];

void ALL;

/** The full-bleed live boards that render outside the app shell (no sidebar). */
const BOARD_PATHS = new Set(["/kitchen", "/waiter"]);

/**
 * Where each role lands after login. Board-primary roles (chef, waiter) land
 * on their live board; everyone else lands on a shell page with the sidebar,
 * so managers and admins are never stranded on a chromeless board.
 */
const ROLE_LANDING: Record<Role, string> = {
  CHEF: "/kitchen",
  WAITER: "/waiter",
  STOREKEEPER: "/stock",
  RECEIVING_OFFICER: "/procurement",
  UNIT_ISSUER: "/issues",
  RESTAURANT_ISSUER: "/issues",
  MANAGER: "/reports",
  ADMIN: "/admin",
};

/** Sections visible to a role, in nav order. */
export function sectionsForRole(role: Role): NavSection[] {
  return NAV_SECTIONS.filter((section) => section.roles.includes(role));
}

/** The landing path for a role; falls back to its first permitted section. */
export function landingPathForRole(role: Role): string {
  return ROLE_LANDING[role] ?? sectionsForRole(role)[0]?.path ?? "/kitchen";
}

/**
 * The first shell (non-board) section a role can reach, or null if the role
 * only has live boards. Used by the boards' "Back to app" control.
 */
export function shellLandingForRole(role: Role): string | null {
  const shell = sectionsForRole(role).find((section) => !BOARD_PATHS.has(section.path));
  return shell?.path ?? null;
}
