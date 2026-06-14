/** Shared presentational primitives used across every standard screen. */

import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import { easeOut } from "../lib/motion";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}): JSX.Element {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="sub">{subtitle}</p>}
      </div>
      {actions && <div style={{ display: "flex", gap: 12 }}>{actions}</div>}
    </div>
  );
}

export function StatCard({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: ReactNode;
  icon?: LucideIcon;
  tone?: "ok" | "warn" | "bad";
}): JSX.Element {
  return (
    <div className="stat">
      <div className="label">
        {Icon && <Icon size={15} />}
        {label}
      </div>
      <div className={`value${tone ? ` ${tone}` : ""}`}>{value}</div>
    </div>
  );
}

export interface Column<T> {
  header: string;
  cell: (row: T) => ReactNode;
  align?: "left" | "right";
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  empty = "Nothing to show yet.",
  loading,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string;
  empty?: string;
  loading?: boolean;
}): JSX.Element {
  if (loading) {
    return (
      <div className="table-wrap" style={{ padding: 16, display: "grid", gap: 10 }}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton" style={{ height: 20 }} />
        ))}
      </div>
    );
  }
  if (rows.length === 0) {
    return <div className="table-wrap empty" style={{ padding: 48 }}>{empty}</div>;
  }
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th key={i} className={col.align === "right" ? "num" : ""}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={rowKey(row, index)}>
              {columns.map((col, i) => (
                <td key={i} className={`${col.align === "right" ? "num" : ""} ${col.className ?? ""}`}>
                  {col.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Dialog({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}): JSX.Element {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="dialog-scrim"
          onClick={onClose}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.16, ease: easeOut }}
        >
          <motion.div
            className="dialog"
            onClick={(e) => e.stopPropagation()}
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 4 }}
            transition={{ duration: 0.2, ease: easeOut }}
          >
            <h2>{title}</h2>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function StatusBadge({ status }: { status: string }): JSX.Element {
  const tone = STATUS_TONE[status] ?? "neutral";
  return <span className={`badge badge-${tone}`}>{status.replaceAll("_", " ").toLowerCase()}</span>;
}

const STATUS_TONE: Record<string, string> = {
  APPROVED: "success",
  POSTED: "success",
  SENT: "success",
  RECEIVED: "success",
  PUBLISHED: "success",
  MATCHED: "success",
  PENDING: "warning",
  PENDING_APPROVAL: "warning",
  SUBMITTED: "warning",
  DRAFT: "neutral",
  PARTIALLY_RECEIVED: "warning",
  REVISION_REQUESTED: "warning",
  INVESTIGATION: "warning",
  MANUAL_CONTACT_REQUIRED: "warning",
  DISCREPANCY: "danger",
  REJECTED: "danger",
  FAILED: "danger",
  DISPUTED: "danger",
  ESCALATED: "danger",
};
