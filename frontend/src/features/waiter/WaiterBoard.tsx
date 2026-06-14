import { useMemo } from "react";
import { ConciergeBell, LogOut } from "lucide-react";
import { AnimatePresence } from "motion/react";

import { ConnPill } from "../../components/ConnPill";
import { useTicker } from "../../lib/useTicker";
import { useAuthStore } from "../../store/authStore";
import { useOrderSocket } from "../kitchen/hooks/useOrderSocket";
import { ServiceTicket } from "./components/ServiceTicket";
import { useActionQueue } from "./store/actionQueue";
import {
  useQueueFlusher,
  useReturnReasons,
  useServiceActions,
  useWaiterOrders,
} from "./hooks/useWaiterService";

const NOW = () => Date.now();

/** Waiter view: ready orders oldest-first, served/return with offline queue. */
export function WaiterBoard(): JSX.Element {
  const { data: orders, isLoading } = useWaiterOrders();
  const { data: reasons = [] } = useReturnReasons();
  const conn = useOrderSocket("/ws/waiter/", ["waiter", "orders"]);
  const { serve, returnOrder } = useServiceActions();
  const queued = useActionQueue((s) => s.pending.length);
  const logout = useAuthStore((state) => state.logout);
  useQueueFlusher();

  useTicker(1000);
  const loadedAt = useMemo(() => NOW(), []);
  const ageOf = (order: { seconds_since_created: number }): number =>
    order.seconds_since_created + Math.floor((NOW() - loadedAt) / 1000);

  return (
    <div className="board">
      <header className="topbar">
        <h1 style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <ConciergeBell size={22} /> Service
        </h1>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <ConnPill state={conn} queued={queued} />
          <button className="btn btn-ghost" onClick={() => void logout()}>
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </header>

      <div className="board-grid">
        <AnimatePresence mode="popLayout">
          {orders.map((order) => (
            <ServiceTicket
              key={order.id}
              order={order}
              ageSeconds={ageOf(order)}
              reasons={reasons}
              onServe={() => serve(order.id)}
              onReturn={(reasonId) => returnOrder(order.id, reasonId)}
            />
          ))}
        </AnimatePresence>

        {!isLoading && orders.length === 0 && (
          <div className="board-empty">
            <ConciergeBell size={40} strokeWidth={1.4} />
            <div>
              <div style={{ fontSize: 18, fontWeight: 600, color: "var(--board-text)" }}>
                Nothing waiting
              </div>
              <div>Orders show here the moment the kitchen marks them ready.</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
