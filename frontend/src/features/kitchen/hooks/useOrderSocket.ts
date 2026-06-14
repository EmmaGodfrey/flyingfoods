import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { api } from "../../../lib/apiClient";

export type ConnState = "live" | "connecting" | "offline";

/**
 * Subscribe to a kitchen/waiter websocket group. The socket carries only
 * notifications ("an order changed"); on each event we invalidate the given
 * query so React Query refetches the source of truth. Auto-reconnects with
 * backoff and reports connection state for the UI pill.
 */
export function useOrderSocket(path: "/ws/kitchen/" | "/ws/waiter/", queryKey: unknown[]): ConnState {
  const qc = useQueryClient();
  const [state, setState] = useState<ConnState>("connecting");
  const attemptsRef = useRef(0);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let closed = false;

    const connect = (): void => {
      setState(attemptsRef.current === 0 ? "connecting" : "offline");
      socket = new WebSocket(api.wsUrl(path));

      socket.onopen = () => {
        attemptsRef.current = 0;
        setState("live");
      };
      socket.onmessage = () => {
        void qc.invalidateQueries({ queryKey });
      };
      socket.onclose = () => {
        if (closed) return;
        setState("offline");
        const delay = Math.min(1000 * 2 ** attemptsRef.current, 15_000);
        attemptsRef.current += 1;
        retryTimer = window.setTimeout(connect, delay);
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      closed = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      socket?.close();
    };
    // queryKey is stable per board; path never changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);

  return state;
}
