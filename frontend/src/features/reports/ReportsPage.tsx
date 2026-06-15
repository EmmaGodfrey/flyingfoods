import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/apiClient";
import { Column, DataTable, PageHeader } from "../../components/ui";

interface ReportDef {
  key: string;
  label: string;
  path: string;
}

const REPORTS: ReportDef[] = [
  { key: "stock-on-hand", label: "Stock on hand", path: "/reports/stock-on-hand/" },
  { key: "budget-vs-actual", label: "Budget vs actual", path: "/reports/budget-vs-actual/" },
  { key: "wastage", label: "Wastage", path: "/reports/wastage/" },
  { key: "service-time", label: "Service time", path: "/reports/service-time/" },
  { key: "movers", label: "Slow / fast movers", path: "/reports/movers/" },
  { key: "leakage", label: "Leakage", path: "/reports/leakage/" },
  { key: "recipe-costing", label: "Recipe costing", path: "/reports/recipe-costing/" },
  { key: "reorder-suggestions", label: "Reorder suggestions", path: "/reports/reorder-suggestions/" },
];

type Row = Record<string, unknown>;

/** Report browser: pick a report, preview rows, export to Excel. */
export function ReportsPage(): JSX.Element {
  const [active, setActive] = useState<ReportDef>(REPORTS[0]);

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["report", active.key],
    queryFn: () => api.get<Row[]>(active.path),
  });

  const columns: Column<Row>[] =
    rows.length > 0
      ? Object.keys(rows[0]).map((key) => ({
          header: key.replaceAll("_", " "),
          cell: (row) => formatCell(row[key]),
        }))
      : [];

  const onExport = async (): Promise<void> => {
    try {
      const res = await api.getRaw(`${active.path}?format=xlsx`);
      const blob = await res.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = `${active.key}.xlsx`;
      a.click();
      URL.revokeObjectURL(href);
    } catch {
      toast.error("Export failed");
    }
  };

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Inventory, procurement, and operations — export any report to Excel."
        actions={
          <button className="btn btn-ghost" onClick={() => void onExport()}>
            <Download size={16} /> Export Excel
          </button>
        }
      />

      <div className="toolbar">
        <div className="seg" style={{ flexWrap: "wrap" }}>
          {REPORTS.map((report) => (
            <button
              key={report.key}
              className={active.key === report.key ? "active" : ""}
              onClick={() => setActive(report)}
            >
              {report.label}
            </button>
          ))}
        </div>
      </div>

      {rows.length === 0 && !isLoading ? (
        <div className="table-wrap empty" style={{ padding: 48 }}>
          <FileSpreadsheet size={36} strokeWidth={1.3} color="var(--ink-300)" />
          <div style={{ marginTop: 8 }}>No data for {active.label.toLowerCase()} yet.</div>
        </div>
      ) : (
        <DataTable columns={columns} rows={rows} rowKey={(_r, index) => String(index)} loading={isLoading} />
      )}
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}
