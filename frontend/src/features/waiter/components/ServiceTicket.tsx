import { useState } from "react";
import { Check, RotateCcw } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import { formatAge } from "../../../lib/useTicker";
import { ticketVariants, easeOut } from "../../../lib/motion";
import type { Order, ReasonCode } from "../../../types";

interface ServiceTicketProps {
  order: Order;
  ageSeconds: number;
  reasons: ReasonCode[];
  onServe: () => void;
  onReturn: (reasonCode: string) => void;
}

/** A ready order on the waiter board, with an inline return-reason picker. */
export function ServiceTicket({ order, ageSeconds, reasons, onServe, onReturn }: ServiceTicketProps): JSX.Element {
  const [picking, setPicking] = useState(false);
  const ageClass = ageSeconds > 300 ? "late" : ageSeconds > 120 ? "warn" : "";

  return (
    <motion.article
      layout
      variants={ticketVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="ticket board-status s-ready"
    >
      <header className="ticket-head">
        <div>
          <div className="ticket-no">#{order.sale_event.slice(0, 6).toUpperCase()}</div>
          <div className="ticket-table">{order.table_ref || "Counter"}</div>
        </div>
        <span className={`ticket-age ${ageClass}`}>ready {formatAge(ageSeconds)}</span>
      </header>

      <div>
        {order.items.map((item) => (
          <div key={item.id} className="ticket-line">
            <span>{item.menu_item_name ?? item.pos_code}</span>
            <span className="qty">×{Number(item.qty)}</span>
          </div>
        ))}
      </div>

      <AnimatePresence mode="wait" initial={false}>
        {picking ? (
          <motion.div
            key="reasons"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto", transition: { duration: 0.2, ease: easeOut } }}
            exit={{ opacity: 0, height: 0, transition: { duration: 0.15, ease: easeOut } }}
            style={{ display: "grid", gap: 8, overflow: "hidden" }}
          >
            <div className="ticket-mods">Return reason</div>
            {reasons.map((reason) => (
              <button
                key={reason.id}
                className="btn btn-ghost btn-block"
                onClick={() => onReturn(reason.id)}
              >
                {reason.label}
              </button>
            ))}
            <button className="btn btn-ghost btn-block" onClick={() => setPicking(false)}>
              Cancel
            </button>
          </motion.div>
        ) : (
          <motion.div key="actions" className="ticket-actions" exit={{ opacity: 0 }}>
            <button className="btn btn-ghost" onClick={() => setPicking(true)}>
              <RotateCcw size={16} /> Return
            </button>
            <button className="btn btn-success btn-block" onClick={onServe}>
              <Check size={16} /> Served
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}
