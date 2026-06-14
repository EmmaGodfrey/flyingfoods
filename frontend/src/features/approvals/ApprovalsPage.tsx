import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Search, X } from "lucide-react";
import { toast } from "sonner";

import { api, ApiError } from "../../lib/apiClient";
import type { Paginated } from "../../types";
import { Column, DataTable, Dialog, PageHeader, StatusBadge } from "../../components/ui";

interface Approval {
  id: string;
  scope: string;
  status: string;
  threshold_snapshot: string | null;
  requested_by_name?: string;
  reason: string;
  created_at: string;
}

const approvalsApi = {
  pending: () =>
    api
      .get<Paginated<Approval>>("/approvals/?status=PENDING&page_size=100")
      .then((p) => p.results),
  decide: (id: string, action: "approve" | "reject" | "investigate", reason: string) =>
    api.post(`/approvals/${id}/${action}/`, reason ? { reason } : {}),
};

/** Manager approval queue: budgets, wastage, transfers, overrides in one place. */
export function ApprovalsPage(): JSX.Element {
  const qc = useQueryClient();
  const [rejecting, setRejecting] = useState<Approval | null>(null);
  const [reason, setReason] = useState("");

  const { data: approvals = [], isLoading } = useQuery({
    queryKey: ["approvals", "pending"],
    queryFn: approvalsApi.pending,
    refetchInterval: 30_000,
  });

  const decide = useMutation({
    mutationFn: ({ id, action, reason }: { id: string; action: "approve" | "reject" | "investigate"; reason: string }) =>
      approvalsApi.decide(id, action, reason),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["approvals"] });
      setRejecting(null);
      setReason("");
      toast.success("Decision recorded");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not record decision"),
  });

  const columns: Column<Approval>[] = [
    { header: "Scope", cell: (r) => <span className="strong">{r.scope.replaceAll("_", " ").toLowerCase() || "general"}</span> },
    { header: "Requested by", cell: (r) => <span className="muted">{r.requested_by_name ?? "—"}</span> },
    { header: "Threshold", align: "right", cell: (r) => (r.threshold_snapshot ? <span className="mono">{r.threshold_snapshot}</span> : "—") },
    { header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
    {
      header: "",
      align: "right",
      cell: (r) => (
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn btn-ghost" onClick={() => decide.mutate({ id: r.id, action: "investigate", reason: "" })}>
            <Search size={15} /> Investigate
          </button>
          <button className="btn btn-ghost" onClick={() => setRejecting(r)}>
            <X size={15} /> Reject
          </button>
          <button className="btn btn-success" onClick={() => decide.mutate({ id: r.id, action: "approve", reason: "" })}>
            <Check size={15} /> Approve
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader title="Approvals" subtitle="Budgets, large wastage, transfers, and stock overrides awaiting your sign-off." />

      <DataTable
        columns={columns}
        rows={approvals}
        rowKey={(r) => r.id}
        loading={isLoading}
        empty="Nothing waiting on you. Above-threshold actions land here."
      />

      <Dialog open={!!rejecting} onClose={() => setRejecting(null)} title="Reject request">
        <label className="field">
          <span>Reason (required)</span>
          <textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        </label>
        <div className="dialog-actions">
          <button className="btn btn-ghost" onClick={() => setRejecting(null)}>Cancel</button>
          <button
            className="btn btn-danger"
            disabled={!reason.trim()}
            onClick={() => rejecting && decide.mutate({ id: rejecting.id, action: "reject", reason })}
          >
            Reject
          </button>
        </div>
      </Dialog>
    </div>
  );
}
