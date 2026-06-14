import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "../../../lib/apiClient";
import { Column, DataTable, Dialog } from "../../../components/ui";
import { adminApi, type Threshold } from "../api";

/** Approval thresholds: list and edit the amount per scope. */
export function ThresholdsTab(): JSX.Element {
  const [editing, setEditing] = useState<Threshold | null>(null);

  const { data: thresholds = [], isLoading } = useQuery({ queryKey: ["thresholds"], queryFn: adminApi.listThresholds });

  const columns: Column<Threshold>[] = [
    { header: "Scope", cell: (r) => <span className="strong">{r.scope.replaceAll("_", " ").toLowerCase()}</span> },
    { header: "Amount", align: "right", cell: (r) => <span className="mono">{r.amount}</span> },
    {
      header: "",
      align: "right",
      cell: (r) => (
        <button className="btn btn-ghost" onClick={() => setEditing(r)}>
          <Pencil size={15} /> Edit
        </button>
      ),
    },
  ];

  return (
    <div>
      <DataTable columns={columns} rows={thresholds} rowKey={(r) => r.id} loading={isLoading} empty="No thresholds configured." />
      {editing && <ThresholdDialog threshold={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function ThresholdDialog({ threshold, onClose }: { threshold: Threshold; onClose: () => void }): JSX.Element {
  const qc = useQueryClient();
  const [amount, setAmount] = useState(threshold.amount);

  const save = useMutation({
    mutationFn: () => adminApi.updateThreshold(threshold.id, Number(amount)),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["thresholds"] });
      onClose();
      toast.success("Threshold updated");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not update threshold"),
  });

  return (
    <Dialog open onClose={onClose} title={`Edit threshold — ${threshold.scope.replaceAll("_", " ").toLowerCase()}`}>
      <label className="field">
        <span>Amount</span>
        <input type="number" min={0} value={amount} onChange={(e) => setAmount(e.target.value)} />
      </label>
      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn btn-primary" disabled={save.isPending} onClick={() => save.mutate()}>
          Save
        </button>
      </div>
    </Dialog>
  );
}
