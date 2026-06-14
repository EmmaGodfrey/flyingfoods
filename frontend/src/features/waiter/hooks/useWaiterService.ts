import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "../../../lib/apiClient";
import type { Order, Paginated } from "../../../types";
import { waiterApi } from "../api";
import { newActionId, type PendingAction, useActionQueue } from "../store/actionQueue";

const KEY = ["waiter", "orders"];

/** Ready orders, oldest first, with the queued (in-flight) ones hidden. */
export function useWaiterOrders() {
  const pending = useActionQueue((s) => s.pending);
  const pendingIds = new Set(pending.map((a) => a.orderId));

  const query = useQuery({
    queryKey: KEY,
    queryFn: waiterApi.listReady,
    staleTime: 0,
    refetchInterval: 20_000,
    select: (page: Paginated<Order>) => page.results,
  });

  return { ...query, data: (query.data ?? []).filter((o) => !pendingIds.has(o.id)) };
}

/** Return-reason options. */
export function useReturnReasons() {
  return useQuery({ queryKey: ["reason-codes", "RETURN"], queryFn: waiterApi.returnReasons });
}

async function runAction(action: PendingAction): Promise<void> {
  if (action.kind === "served") {
    await waiterApi.served(action.orderId, action.id);
  } else {
    await waiterApi.returnOrder(action.orderId, action.reasonCode, action.id);
  }
}

/**
 * Drain the offline queue while online. Terminal API errors (4xx) drop the
 * action; network failures keep it for the next attempt. Runs on mount, on
 * `online`, and whenever the queue changes.
 */
export function useQueueFlusher(): void {
  const qc = useQueryClient();
  const pending = useActionQueue((s) => s.pending);
  const remove = useActionQueue((s) => s.remove);

  useEffect(() => {
    if (pending.length === 0) return;
    let cancelled = false;

    const flush = async (): Promise<void> => {
      if (!navigator.onLine) return;
      for (const action of pending) {
        if (cancelled) return;
        try {
          await runAction(action);
          remove(action.id);
        } catch (error) {
          // 4xx is terminal (already served, bad reason); 5xx/network: retry later.
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
            remove(action.id);
          } else {
            break;
          }
        }
      }
      if (!cancelled) void qc.invalidateQueries({ queryKey: KEY });
    };

    void flush();
    window.addEventListener("online", flush);
    const timer = window.setInterval(flush, 8_000);
    return () => {
      cancelled = true;
      window.removeEventListener("online", flush);
      window.clearInterval(timer);
    };
  }, [pending, remove, qc]);
}

/** Enqueue Served / Return; the order disappears optimistically. */
export function useServiceActions() {
  const enqueue = useActionQueue((s) => s.enqueue);
  return {
    serve: (orderId: string) => enqueue({ id: newActionId(), kind: "served", orderId }),
    returnOrder: (orderId: string, reasonCode: string) =>
      enqueue({ id: newActionId(), kind: "return", orderId, reasonCode }),
  };
}
