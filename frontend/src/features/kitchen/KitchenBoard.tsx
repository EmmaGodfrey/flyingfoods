import { useMemo } from "react";
import { ChefHat, LogOut } from "lucide-react";
import { AnimatePresence } from "motion/react";

import { ConnPill } from "../../components/ConnPill";
import { useTicker } from "../../lib/useTicker";
import { useAuthStore } from "../../store/authStore";
import { OrderTicket } from "./components/OrderTicket";
import { useKitchenOrders, useOrderTransition } from "./hooks/useKitchenOrders";
import { useOrderSocket } from "./hooks/useOrderSocket";

const NOW = () => Date.now();

/** Full-bleed kitchen display. Orders enter live, age in place, leave on serve. */
export function KitchenBoard(): JSX.Element {
  const { data: orders = [], isLoading } = useKitchenOrders();
  const conn = useOrderSocket("/ws/kitchen/", ["kitchen", "orders"]);
  const { start, ready } = useOrderTransition();
  const logout = useAuthStore((state) => state.logout);

  // One ticking clock for the whole board; each card derives its own age.
  useTicker(1000);
  const loadedAt = useMemo(() => NOW(), []);

  const ageOf = (order: { seconds_since_created: number }): number =>
    order.seconds_since_created + Math.floor((NOW() - loadedAt) / 1000);

  return (
    <div className="board">
      <header className="topbar">
        <h1 style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <ChefHat size={22} /> Kitchen Display
        </h1>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <ConnPill state={conn} />
          <button className="btn btn-ghost" onClick={() => void logout()}>
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </header>

      <div className="board-grid">
        <AnimatePresence mode="popLayout">
          {orders.map((order) => (
            <OrderTicket
              key={order.id}
              order={order}
              ageSeconds={ageOf(order)}
              busy={start.isPending || ready.isPending}
              onStart={() => start.mutate(order.id)}
              onReady={() => ready.mutate(order.id)}
            />
          ))}
        </AnimatePresence>

        {!isLoading && orders.length === 0 && (
          <div className="board-empty">
            <ChefHat size={40} strokeWidth={1.4} />
            <div>
              <div style={{ fontSize: 18, fontWeight: 600, color: "var(--board-text)" }}>
                All caught up
              </div>
              <div>New orders appear here the moment a sale clears.</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
