import type { LucideIcon } from "lucide-react";

/** Consistent stand-in for sections whose UI ships in a later pass. */
export function Placeholder({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}): JSX.Element {
  return (
    <div className="card card-pad empty" style={{ minHeight: 420 }}>
      <Icon size={44} strokeWidth={1.3} color="var(--ink-300)" />
      <div>
        <h2 style={{ marginBottom: 6 }}>{title}</h2>
        <p style={{ color: "var(--ink-500)", maxWidth: "46ch", margin: "0 auto" }}>{description}</p>
      </div>
      <span className="badge badge-brand">Wired to the API next</span>
    </div>
  );
}
