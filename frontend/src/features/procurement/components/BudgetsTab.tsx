import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "../../../lib/apiClient";
import { Column, DataTable, Dialog, StatusBadge } from "../../../components/ui";
import { procurementApi, type Budget, type CreateBudgetBody } from "../api";

interface DraftLine {
  product: string;
  qty: string;
  estUnitCost: string;
}

const emptyLine: DraftLine = { product: "", qty: "", estUnitCost: "" };

/** Budgets list with create-draft and submit-for-approval actions. */
export function BudgetsTab(): JSX.Element {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  const { data: budgets = [], isLoading } = useQuery({ queryKey: ["budgets"], queryFn: procurementApi.listBudgets });

  const submit = useMutation({
    mutationFn: (id: string) => procurementApi.submitBudget(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["budgets"] });
      toast.success("Budget submitted");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not submit budget"),
  });

  const columns: Column<Budget>[] = [
    { header: "Reference", cell: (r) => <span className="mono">{r.reference ?? r.id.slice(0, 8)}</span>, className: "strong" },
    { header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
    { header: "Total", align: "right", cell: (r) => (r.total != null ? <span className="mono">{r.total}</span> : "—") },
    {
      header: "",
      align: "right",
      cell: (r) =>
        r.status === "DRAFT" ? (
          <button className="btn btn-ghost" disabled={submit.isPending} onClick={() => submit.mutate(r.id)}>
            <Send size={15} /> Submit
          </button>
        ) : null,
    },
  ];

  return (
    <div>
      <div className="toolbar">
        <div className="grow" />
        <button className="btn btn-primary" onClick={() => setOpen(true)}>
          <Plus size={16} /> New budget
        </button>
      </div>

      <DataTable columns={columns} rows={budgets} rowKey={(r) => r.id} loading={isLoading} empty="No budgets yet." />

      <NewBudgetDialog open={open} onClose={() => setOpen(false)} />
    </div>
  );
}

function NewBudgetDialog({ open, onClose }: { open: boolean; onClose: () => void }): JSX.Element {
  const qc = useQueryClient();
  const [lines, setLines] = useState<DraftLine[]>([{ ...emptyLine }]);

  const { data: products = [] } = useQuery({ queryKey: ["products"], queryFn: procurementApi.products, staleTime: 60 * 60 * 1000 });

  const update = (index: number, patch: Partial<DraftLine>): void =>
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  const remove = (index: number): void => setLines((prev) => prev.filter((_, i) => i !== index));

  const budgetLines = lines
    .filter((line) => line.product && Number(line.qty) > 0)
    .map((line) => ({ product: line.product, qty: Number(line.qty), est_unit_cost: Number(line.estUnitCost) }));

  const create = useMutation({
    mutationFn: (body: CreateBudgetBody) => procurementApi.createBudget(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["budgets"] });
      setLines([{ ...emptyLine }]);
      onClose();
      toast.success("Budget created");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not create budget"),
  });

  return (
    <Dialog open={open} onClose={onClose} title="New budget">
      <div className="form-grid">
        {lines.map((line, index) => (
          <div className="form-row" key={index} style={{ gridTemplateColumns: "2fr 1fr 1fr auto", alignItems: "end" }}>
            <label className="field">
              <span>Product</span>
              <select value={line.product} onChange={(e) => update(index, { product: e.target.value })}>
                <option value="">Select…</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.code})
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Qty</span>
              <input type="number" min={0} value={line.qty} onChange={(e) => update(index, { qty: e.target.value })} />
            </label>
            <label className="field">
              <span>Est. unit cost</span>
              <input type="number" min={0} value={line.estUnitCost} onChange={(e) => update(index, { estUnitCost: e.target.value })} />
            </label>
            <button className="btn btn-ghost" disabled={lines.length === 1} onClick={() => remove(index)}>
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        <button className="btn btn-ghost" onClick={() => setLines([...lines, { ...emptyLine }])}>
          <Plus size={15} /> Add line
        </button>
      </div>

      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn btn-primary" disabled={budgetLines.length === 0 || create.isPending} onClick={() => create.mutate({ lines: budgetLines })}>
          Create budget
        </button>
      </div>
    </Dialog>
  );
}
