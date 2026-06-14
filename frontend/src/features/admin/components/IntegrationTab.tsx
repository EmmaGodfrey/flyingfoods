import { useQuery } from "@tanstack/react-query";

import { StatCard } from "../../../components/ui";
import { adminApi } from "../api";

/** Read-only integration health cards (POS ingest, Pastel sync, email gateway). */
export function IntegrationTab(): JSX.Element {
  const { data: health = [], isLoading } = useQuery({
    queryKey: ["integration-health"],
    queryFn: adminApi.integrationHealth,
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <div className="stat-grid">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="skeleton" style={{ height: 80 }} />
        ))}
      </div>
    );
  }

  if (health.length === 0) {
    return <div className="table-wrap empty" style={{ padding: 48 }}>No integration health data available.</div>;
  }

  return (
    <div className="stat-grid">
      {health.map((item) => (
        <StatCard
          key={item.key}
          label={item.label}
          value={item.status.replaceAll("_", " ").toLowerCase()}
          tone={toneForStatus(item.status)}
        />
      ))}
    </div>
  );
}

function toneForStatus(status: string): "ok" | "warn" | "bad" {
  if (status === "OK" || status === "HEALTHY" || status === "CONNECTED") return "ok";
  if (status === "FAILED" || status === "ERROR" || status === "DOWN") return "bad";
  return "warn";
}
