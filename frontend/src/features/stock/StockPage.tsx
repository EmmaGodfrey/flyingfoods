import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Boxes, PackageCheck } from "lucide-react";

import { Column, DataTable, PageHeader, StatCard } from "../../components/ui";
import { stockApi, type StockBalance } from "./api";

/** Stock on hand across locations, with reorder-level highlighting. */
export function StockPage(): JSX.Element {
  const [location, setLocation] = useState<string>("");

  const { data: locations = [] } = useQuery({
    queryKey: ["locations"],
    queryFn: stockApi.locations,
    staleTime: 60 * 60 * 1000,
  });

  const { data: balances = [], isLoading } = useQuery({
    queryKey: ["stock", "balances", location],
    queryFn: () => stockApi.balances({ location: location || undefined }),
  });

  const lowCount = useMemo(
    () => balances.filter((b) => Number(b.qty_on_hand) <= 0).length,
    [balances],
  );

  const columns: Column<StockBalance>[] = [
    { header: "Code", cell: (r) => <span className="mono">{r.product_code}</span> },
    { header: "Product", cell: (r) => r.product_name, className: "strong" },
    { header: "Location", cell: (r) => <span className="muted">{r.location_name}</span> },
    {
      header: "On hand",
      align: "right",
      cell: (r) => {
        const qty = Number(r.qty_on_hand);
        const tone = qty <= 0 ? "badge-danger" : qty < 10 ? "badge-warning" : "badge-neutral";
        return <span className={`badge ${tone} mono`}>{qty}</span>;
      },
    },
  ];

  return (
    <div>
      <PageHeader title="Stock on hand" subtitle="Live balances derived from the movement ledger." />

      <div className="stat-grid">
        <StatCard label="Tracked balances" value={balances.length} icon={Boxes} />
        <StatCard label="At or below zero" value={lowCount} icon={AlertTriangle} tone={lowCount ? "bad" : "ok"} />
        <StatCard label="Locations" value={locations.length} icon={PackageCheck} />
      </div>

      <div className="toolbar">
        <div className="seg">
          <button className={location === "" ? "active" : ""} onClick={() => setLocation("")}>
            All
          </button>
          {locations.map((loc) => (
            <button
              key={loc.id}
              className={location === loc.id ? "active" : ""}
              onClick={() => setLocation(loc.id)}
            >
              {loc.name}
            </button>
          ))}
        </div>
      </div>

      <DataTable
        columns={columns}
        rows={balances}
        rowKey={(r) => r.id}
        loading={isLoading}
        empty="No stock balances for this location yet."
      />
    </div>
  );
}
