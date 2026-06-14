import { LogOut } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";

import { pageVariants } from "../lib/motion";
import { useAuthStore } from "../store/authStore";
import { sectionsForRole } from "./navigation";

/**
 * Authenticated layout: role-aware sidebar, sticky topbar, and an animated
 * outlet. Kitchen and waiter boards opt out of the chrome (they render their
 * own full-bleed dark surface), so the shell only wraps the standard pages.
 */
const ROLE_LABELS: Record<string, string> = {
  CHEF: "Chef",
  WAITER: "Waiter",
  STOREKEEPER: "Storekeeper",
  RECEIVING_OFFICER: "Receiving Officer",
  UNIT_ISSUER: "Unit Issuer",
  RESTAURANT_ISSUER: "Restaurant Issuer",
  MANAGER: "Manager",
  ADMIN: "Administrator",
};

const initials = (name: string): string =>
  name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

export function AppShell(): JSX.Element {
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  if (!user) return <Outlet />;

  const sections = sectionsForRole(user.role);
  const active = sections.find((section) => location.pathname.startsWith(section.path));

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">FF</span>
          Flying Foods
        </div>
        {sections.map((section) => {
          const Icon = section.icon;
          return (
            <NavLink
              key={section.key}
              to={section.path}
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
            >
              <Icon size={16} />
              {section.label}
            </NavLink>
          );
        })}
        <div className="nav-spacer" />
        <button className="nav-item" onClick={() => void logout()}>
          <LogOut size={16} />
          Sign out
        </button>
      </aside>

      <main>
        <header className="topbar">
          <h1>{active?.label ?? "Flying Foods"}</h1>
          <div className="user-chip">
            <div style={{ textAlign: "right" }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{user.full_name}</div>
              <div style={{ fontSize: 12, color: "var(--ink-500)" }}>{ROLE_LABELS[user.role]}</div>
            </div>
            <span className="avatar">{initials(user.full_name)}</span>
          </div>
        </header>

        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            className="page page-narrow"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
