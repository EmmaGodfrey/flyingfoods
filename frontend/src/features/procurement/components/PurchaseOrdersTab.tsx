import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PackageCheck, Plus, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "../../../lib/apiClient";
import { Column, DataTable, Dialog, StatusBadge } from "../../../components/ui";
import {
  procurementApi,
  type CreatePurchaseOrderBody,
  type GrnLine,
  type PurchaseOrder,
} from "../api";

interface DraftLine {
  product: string;
  qty: string;
  unitPrice: string;
}

const emptyLine: DraftLine = { product: "", qty: "", unitPrice: "" };

/** Purchase orders list with send and goods-received (GRN) actions. */
export function PurchaseOrdersTab(): JSX.Element {
  const qc = useQueryClient();
  const [newOpen, setNewOpen] = useState(false);
  const [receiving, setReceiving] = useState<PurchaseOrder | null>(null);

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["purchase-orders"],
    queryFn: procurementApi.listPurchaseOrders,
  });

  const send = useMutation({
    mutationFn: (id: string) => procurementApi.sendPurchaseOrder(id),
    onSuccess: (po) => {
      void qc.invalidateQueries({ queryKey: ["purchase-orders"] });
      if (po.status === "MANUAL_CONTACT_REQUIRED") {
        toast.warning("No supplier email — contact the supplier manually");
      } else {
        toast.success("Purchase order sent");
      }
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not send PO"),
  });

  const columns: Column<PurchaseOrder>[] = [
    { header: "Reference", cell: (r) => <span className="mono">{r.reference ?? r.id.slice(0, 8)}</span>, className: "strong" },
    { header: "Supplier", cell: (r) => r.supplier_name ?? <span className="muted">{r.supplier}</span> },
    { header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
    { header: "Total", align: "right", cell: (r) => (r.total != null ? <span className="mono">{r.total}</span> : "—") },
    {
      header: "",
      align: "right",
      cell: (r) => (
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          {r.status === "DRAFT" && (
            <button className="btn btn-ghost" disabled={send.isPending} onClick={() => send.mutate(r.id)}>
              <Send size={15} /> Send
            </button>
          )}
          <button className="btn btn-success" onClick={() => setReceiving(r)}>
            <PackageCheck size={15} /> Receive (GRN)
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="toolbar">
        <div className="grow" />
        <button className="btn btn-primary" onClick={() => setNewOpen(true)}>
          <Plus size={16} /> New PO
        </button>
      </div>

      <DataTable columns={columns} rows={orders} rowKey={(r) => r.id} loading={isLoading} empty="No purchase orders yet." />

      <NewPurchaseOrderDialog open={newOpen} onClose={() => setNewOpen(false)} />
      {receiving && <GrnDialog poId={receiving.id} onClose={() => setReceiving(null)} />}
    </div>
  );
}

function NewPurchaseOrderDialog({ open, onClose }: { open: boolean; onClose: () => void }): JSX.Element {
  const qc = useQueryClient();
  const [budget, setBudget] = useState("");
  const [supplier, setSupplier] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([{ ...emptyLine }]);

  const { data: budgets = [] } = useQuery({ queryKey: ["budgets"], queryFn: procurementApi.listBudgets });
  const { data: suppliers = [] } = useQuery({ queryKey: ["suppliers"], queryFn: procurementApi.suppliers, staleTime: 60 * 60 * 1000 });
  const { data: products = [] } = useQuery({ queryKey: ["products"], queryFn: procurementApi.products, staleTime: 60 * 60 * 1000 });

  const approvedBudgets = budgets.filter((b) => b.status === "APPROVED");

  const update = (index: number, patch: Partial<DraftLine>): void =>
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  const remove = (index: number): void => setLines((prev) => prev.filter((_, i) => i !== index));

  const poLines = lines
    .filter((line) => line.product && Number(line.qty) > 0)
    .map((line) => ({ product: line.product, qty: Number(line.qty), unit_price: Number(line.unitPrice) }));

  const create = useMutation({
    mutationFn: (body: CreatePurchaseOrderBody) => procurementApi.createPurchaseOrder(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["purchase-orders"] });
      setBudget("");
      setSupplier("");
      setLines([{ ...emptyLine }]);
      onClose();
      toast.success("Purchase order created");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not create PO"),
  });

  const canSubmit = budget && supplier && poLines.length > 0;

  return (
    <Dialog open={open} onClose={onClose} title="New purchase order">
      <div className="form-grid">
        <div className="form-row">
          <label className="field">
            <span>Approved budget</span>
            <select value={budget} onChange={(e) => setBudget(e.target.value)}>
              <option value="">Select…</option>
              {approvedBudgets.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.reference ?? b.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Supplier</span>
            <select value={supplier} onChange={(e) => setSupplier(e.target.value)}>
              <option value="">Select…</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
        </div>

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
              <span>Unit price</span>
              <input type="number" min={0} value={line.unitPrice} onChange={(e) => update(index, { unitPrice: e.target.value })} />
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
        <button className="btn btn-primary" disabled={!canSubmit || create.isPending} onClick={() => create.mutate({ budget, supplier, lines: poLines })}>
          Create PO
        </button>
      </div>
    </Dialog>
  );
}

function GrnDialog({ poId, onClose }: { poId: string; onClose: () => void }): JSX.Element {
  const qc = useQueryClient();
  const [received, setReceived] = useState<Record<string, { qty: string; cost: string }>>({});

  const { data: po, isLoading } = useQuery({
    queryKey: ["purchase-order", poId],
    queryFn: () => procurementApi.getPurchaseOrder(poId),
  });

  const set = (lineId: string, patch: Partial<{ qty: string; cost: string }>): void =>
    setReceived((prev) => ({ ...prev, [lineId]: { qty: prev[lineId]?.qty ?? "", cost: prev[lineId]?.cost ?? "", ...patch } }));

  const grnLines: GrnLine[] = (po?.lines ?? [])
    .map((line) => {
      const entry = received[line.id];
      if (!entry || Number(entry.qty) <= 0) return null;
      return { po_line: line.id, qty_received: Number(entry.qty), unit_cost: Number(entry.cost) };
    })
    .filter((line): line is GrnLine => line !== null);

  const create = useMutation({
    mutationFn: () => procurementApi.createGrn(poId, grnLines),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["purchase-orders"] });
      void qc.invalidateQueries({ queryKey: ["purchase-order", poId] });
      void qc.invalidateQueries({ queryKey: ["stock"] });
      onClose();
      toast.success("Goods received");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not record GRN"),
  });

  return (
    <Dialog open onClose={onClose} title="Receive goods (GRN)">
      {isLoading ? (
        <div className="skeleton" style={{ height: 80 }} />
      ) : (
        <div className="form-grid">
          {(po?.lines ?? []).map((line) => (
            <div className="form-row" key={line.id} style={{ gridTemplateColumns: "2fr 1fr 1fr", alignItems: "end" }}>
              <label className="field">
                <span>{line.product_name ?? line.product}</span>
                <input value={`ordered ${line.qty}`} disabled />
              </label>
              <label className="field">
                <span>Qty received</span>
                <input
                  type="number"
                  min={0}
                  value={received[line.id]?.qty ?? ""}
                  onChange={(e) => set(line.id, { qty: e.target.value })}
                />
              </label>
              <label className="field">
                <span>Unit cost</span>
                <input
                  type="number"
                  min={0}
                  value={received[line.id]?.cost ?? line.unit_price}
                  onChange={(e) => set(line.id, { cost: e.target.value })}
                />
              </label>
            </div>
          ))}
        </div>
      )}

      {/* TODO: 3-way invoice matching (POST /purchase-orders/{id}/invoices/) as a follow-up screen. */}

      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn btn-success" disabled={grnLines.length === 0 || create.isPending} onClick={() => create.mutate()}>
          Record GRN
        </button>
      </div>
    </Dialog>
  );
}
