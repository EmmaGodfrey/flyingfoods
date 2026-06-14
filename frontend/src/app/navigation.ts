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

export const NAV_SECTIONS: NavSection[] = [
  { key: "kitchen", label: "Kitchen", path: "/kitchen", icon: ChefHat, roles: ["CHEF", "STOREKEEPER", "MANAGER", "ADMIN"] },
  { key: "waiter", label: "Service", path: "/waiter", icon: ConciergeBell, roles: ["WAITER", "MANAGER", "ADMIN"] },
  { key: "stock", label: "Stock", path: "/stock", icon: Boxes, roles: ["STOREKEEPER", "MANAGER", "RESTAURANT_ISSUER", "UNIT_ISSUER", "RECEIVING_OFFICER", "ADMIN"] },
  { key: "issues", label: "Issues & Transfers", path: "/issues", icon: ClipboardList, roles: ["RESTAURANT_ISSUER", "UNIT_ISSUER", "STOREKEEPER", "MANAGER", "ADMIN"] },
  { key: "procurement", label: "Procurement", path: "/procurement", icon: ShoppingCart, roles: ["RECEIVING_OFFICER", "MANAGER", "ADMIN"] },
  { key: "wastage", label: "Wastage", path: "/wastage", icon: Trash2, roles: ["CHEF", "STOREKEEPER", "MANAGER", "ADMIN"] },
  { key: "menu", label: "Menu & Recipes", path: "/menu", icon: PackageSearch, roles: ["ADMIN", "MANAGER"] },
  { key: "approvals", label: "Approvals", path: "/approvals", icon: FileText, roles: ["MANAGER", "ADMIN"] },
  { key: "reports", label: "Reports", path: "/reports", icon: BarChart3, roles: ["MANAGER", "ADMIN", "STOREKEEPER", "RECEIVING_OFFICER"] },
  { key: "admin", label: "Administration", path: "/admin", icon: Settings, roles: ["ADMIN"] },
];

void ALL;

/** Sections visible to a role, in nav order. */
export function sectionsForRole(role: Role): NavSection[] {
  return NAV_SECTIONS.filter((section) => section.roles.includes(role));
}

/** The landing path for a role (its first permitted section). */
export function landingPathForRole(role: Role): string {
  return sectionsForRole(role)[0]?.path ?? "/kitchen";
}
