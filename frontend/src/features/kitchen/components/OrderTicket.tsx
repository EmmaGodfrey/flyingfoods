import { AlertTriangle, ChefHat, Check } from "lucide-react";
import { motion } from "motion/react";

import { formatAge } from "../../../lib/useTicker";
import { ticketVariants } from "../../../lib/motion";
import type { Order } from "../../../types";

interface OrderTicketProps {
  order: Order;
  /** Wall-clock seconds elapsed, recomputed each tick by the board. */
  ageSeconds: number;
  onStart: () => void;
  onReady: () => void;
  busy: boolean;
}

const STATUS_CLASS: Record<string, string> = {
  INGESTED: "s-ingested",
  IN_PREPARATION: "s-prep",
  READY: "s-ready",
};

/** A single kitchen order card. Spring entrance; layout animates on reorder. */
export function OrderTicket({ order, ageSeconds, onStart, onReady, busy }: OrderTicketProps): JSX.Element {
  const ageClass = ageSeconds > 600 ? "late" : ageSeconds > 300 ? "warn" : "";

  return (
    <motion.article
      layout
      variants={ticketVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={`ticket board-status ${STATUS_CLASS[order.status] ?? ""}`}
    >
      <header className="ticket-head">
        <div>
          <div className="ticket-no">#{order.sale_event.slice(0, 6).toUpperCase()}</div>
          <div className="ticket-table">{order.table_ref || "Counter"}</div>
        </div>
        <span className={`ticket-age ${ageClass}`}>{formatAge(ageSeconds)}</span>
      </header>

      <div>
        {order.items.map((item) => (
          <div key={item.id} className="ticket-line">
            <span>
              {item.menu_item_name ?? item.pos_code}
              {item.modifiers.length > 0 && (
                <span className="ticket-mods"> · {item.modifiers.join(", ")}</span>
              )}
            </span>
            <span className="qty">×{Number(item.qty)}</span>
          </div>
        ))}
      </div>

      {order.flagged_insufficient_stock && (
        <div className="ticket-flag">
          <AlertTriangle size={14} /> Low stock — check with stores
        </div>
      )}

      <div className="ticket-actions">
        {order.status === "INGESTED" && (
          <button className="btn btn-ghost btn-block" onClick={onStart} disabled={busy}>
            <ChefHat size={16} /> Start
          </button>
        )}
        {order.status === "IN_PREPARATION" && (
          <button className="btn btn-success btn-block" onClick={onReady} disabled={busy}>
            <Check size={16} /> Ready
          </button>
        )}
        {order.status === "READY" && (
          <span className="badge badge-success badge-dot" style={{ marginLeft: "auto" }}>
            Awaiting pickup
          </span>
        )}
      </div>
    </motion.article>
  );
}
