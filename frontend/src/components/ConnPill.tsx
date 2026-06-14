import type { ConnState } from "../features/kitchen/hooks/useOrderSocket";

const LABELS: Record<ConnState | "queued", string> = {
  live: "Live",
  connecting: "Connecting…",
  offline: "Offline — retrying",
  queued: "Offline — actions queued",
};

/** Connection status pill for the live boards. */
export function ConnPill({ state, queued = 0 }: { state: ConnState; queued?: number }): JSX.Element {
  const mode = state === "offline" && queued > 0 ? "queued" : state;
  const className = mode === "queued" ? "conn queued" : mode === "live" ? "conn" : "conn off";
  return (
    <span className={className}>
      <span className="dot" />
      {mode === "queued" ? `${LABELS.queued} (${queued})` : LABELS[mode]}
    </span>
  );
}
