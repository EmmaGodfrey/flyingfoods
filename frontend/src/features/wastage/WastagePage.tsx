import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "../../lib/apiClient";
import { Column, DataTable, Dialog, PageHeader, StatusBadge } from "../../components/ui";
import { stockApi } from "../stock/api";
import {
  wastageApi,
  type CreateWastageBody,
  type StockTakeLine,
  type WastageEntry,
  type WastageEntryType,
} from "./api";

type Mode = "WASTAGE" | "STOCK_TAKE";

/** Log breakage/spoilage and run location stock-takes with variance posting. */
export function WastagePage(): JSX.Element {
  const [mode, setMode] = useState<Mode>("WASTAGE");

  return (
    <div>
      <PageHeader
        title="Wastage & stock-take"
        subtitle="Log breakage and spoilage, run stock-takes, and review variance."
      />

      <div className="toolbar">
        <div className="seg">
          <button className={mode === "WASTAGE" ? "active" : ""} onClick={() => setMode("WASTAGE")}>
            Log wastage
          </button>
          <button className={mode === "STOCK_TAKE" ? "active" : ""} onClick={() => setMode("STOCK_TAKE")}>
            Stock-take
          </button>
        </div>
      </div>

      {mode === "WASTAGE" ? <WastageTab /> : <StockTakeTab />}
    </div>
  );
}

function WastageTab(): JSX.Element {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["wastage", "list"],
    queryFn: wastageApi.list,
  });

  const columns: Column<WastageEntry>[] = [
    { header: "Type", cell: (r) => <span className="strong">{r.entry_type.toLowerCase()}</span> },
    { header: "Product", cell: (r) => r.product_name ?? <span className="mono">{r.product}</span> },
    { header: "Location", cell: (r) => <span className="muted">{r.location_name ?? "—"}</span> },
    { header: "Qty", align: "right", cell: (r) => <span className="mono">{r.qty}</span> },
    { header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
  ];

  return (
    <div>
      <div className="toolbar">
        <div className="grow" />
        <button className="btn btn-primary" onClick={() => setOpen(true)}>
          <Plus size={16} /> Log wastage
        </button>
      </div>

      <DataTable
        columns={columns}
        rows={entries}
        rowKey={(r) => r.id}
        loading={isLoading}
        empty="No wastage logged yet."
      />

      <LogWastageDialog open={open} onClose={() => setOpen(false)} onLogged={() => void qc.invalidateQueries({ queryKey: ["wastage"] })} />
    </div>
  );
}

function LogWastageDialog({
  open,
  onClose,
  onLogged,
}: {
  open: boolean;
  onClose: () => void;
  onLogged: () => void;
}): JSX.Element {
  const [entryType, setEntryType] = useState<WastageEntryType>("BREAKAGE");
  const [product, setProduct] = useState("");
  const [location, setLocation] = useState("");
  const [qty, setQty] = useState("");
  const [reasonCode, setReasonCode] = useState("");
  const [note, setNote] = useState("");

  const { data: products = [] } = useQuery({ queryKey: ["products"], queryFn: wastageApi.products, staleTime: 60 * 60 * 1000 });
  const { data: locations = [] } = useQuery({ queryKey: ["locations"], queryFn: stockApi.locations, staleTime: 60 * 60 * 1000 });
  const { data: reasons = [] } = useQuery({
    queryKey: ["reason-codes", "WASTAGE"],
    queryFn: () => wastageApi.reasonCodes("WASTAGE"),
    staleTime: 60 * 60 * 1000,
  });

  const reset = (): void => {
    setEntryType("BREAKAGE");
    setProduct("");
    setLocation("");
    setQty("");
    setReasonCode("");
    setNote("");
  };

  const create = useMutation({
    mutationFn: (body: CreateWastageBody) => wastageApi.create(body),
    onSuccess: () => {
      onLogged();
      reset();
      onClose();
      toast.success("Wastage logged");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not log wastage"),
  });

  const canSubmit = product && location && reasonCode && Number(qty) > 0;

  return (
    <Dialog open={open} onClose={onClose} title="Log wastage">
      <div className="form-grid">
        <div className="form-row">
          <label className="field">
            <span>Type</span>
            <select value={entryType} onChange={(e) => setEntryType(e.target.value as WastageEntryType)}>
              <option value="BREAKAGE">Breakage</option>
              <option value="SPOILAGE">Spoilage</option>
            </select>
          </label>
          <label className="field">
            <span>Quantity</span>
            <input type="number" min={0} value={qty} onChange={(e) => setQty(e.target.value)} />
          </label>
        </div>

        <label className="field">
          <span>Product</span>
          <select value={product} onChange={(e) => setProduct(e.target.value)}>
            <option value="">Select a product…</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.code})
              </option>
            ))}
          </select>
        </label>

        <div className="form-row">
          <label className="field">
            <span>Location</span>
            <select value={location} onChange={(e) => setLocation(e.target.value)}>
              <option value="">Select a location…</option>
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Reason</span>
            <select value={reasonCode} onChange={(e) => setReasonCode(e.target.value)}>
              <option value="">Select a reason…</option>
              {reasons.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="field">
          <span>Note (optional)</span>
          <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
      </div>

      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn btn-primary"
          disabled={!canSubmit || create.isPending}
          onClick={() =>
            create.mutate({
              entry_type: entryType,
              product,
              location,
              qty: Number(qty),
              reason_code: reasonCode,
              note: note.trim() || undefined,
            })
          }
        >
          <Trash2 size={16} /> Log wastage
        </button>
      </div>
    </Dialog>
  );
}

function StockTakeTab(): JSX.Element {
  const qc = useQueryClient();
  const [location, setLocation] = useState("");
  const [stockTakeId, setStockTakeId] = useState<string | null>(null);
  const [counts, setCounts] = useState<Record<string, string>>({});

  const { data: locations = [] } = useQuery({ queryKey: ["locations"], queryFn: stockApi.locations, staleTime: 60 * 60 * 1000 });

  const { data: stockTake, isLoading } = useQuery({
    queryKey: ["stock-take", stockTakeId],
    queryFn: () => wastageApi.getStockTake(stockTakeId as string),
    enabled: !!stockTakeId,
  });

  const open = useMutation({
    mutationFn: () => wastageApi.openStockTake(location),
    onSuccess: (st) => {
      setStockTakeId(st.id);
      setCounts({});
      toast.success("Stock-take opened");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not open stock-take"),
  });

  const save = useMutation({
    mutationFn: () =>
      wastageApi.saveCounts(
        stockTakeId as string,
        (stockTake?.lines ?? []).map((line) => ({
          product: line.product,
          counted_qty: Number(counts[line.id] ?? line.counted_qty ?? 0),
        })),
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["stock-take", stockTakeId] });
      toast.success("Counts saved");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not save counts"),
  });

  const post = useMutation({
    mutationFn: () => wastageApi.postStockTake(stockTakeId as string),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["stock-take", stockTakeId] });
      void qc.invalidateQueries({ queryKey: ["stock"] });
      toast.success("Stock-take posted");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not post stock-take"),
  });

  const isPosted = stockTake?.status === "POSTED";

  const columns: Column<StockTakeLine>[] = useMemo(
    () => [
      { header: "Product", cell: (r) => r.product_name ?? <span className="mono">{r.product}</span>, className: "strong" },
      { header: "System", align: "right", cell: (r) => <span className="mono">{r.system_qty}</span> },
      {
        header: "Counted",
        align: "right",
        cell: (r) => (
          <input
            type="number"
            min={0}
            disabled={isPosted}
            style={{ width: 100, textAlign: "right" }}
            value={counts[r.id] ?? r.counted_qty ?? ""}
            onChange={(e) => setCounts((prev) => ({ ...prev, [r.id]: e.target.value }))}
          />
        ),
      },
      { header: "Variance", align: "right", cell: (r) => (r.variance != null ? <span className="mono">{r.variance}</span> : "—") },
      { header: "Value", align: "right", cell: (r) => (r.value != null ? <span className="mono">{r.value}</span> : "—") },
    ],
    [counts, isPosted],
  );

  return (
    <div>
      <div className="toolbar">
        <div className="seg">
          {locations.map((l) => (
            <button key={l.id} className={location === l.id ? "active" : ""} onClick={() => setLocation(l.id)}>
              {l.name}
            </button>
          ))}
        </div>
        <div className="grow" />
        <button className="btn btn-primary" disabled={!location || open.isPending} onClick={() => open.mutate()}>
          <ClipboardCheck size={16} /> Open stock-take
        </button>
      </div>

      {!stockTakeId ? (
        <div className="table-wrap empty" style={{ padding: 48 }}>
          Pick a location and open a stock-take to begin counting.
        </div>
      ) : (
        <>
          <DataTable
            columns={columns}
            rows={stockTake?.lines ?? []}
            rowKey={(r) => r.id}
            loading={isLoading}
            empty="No products to count at this location."
          />

          <div className="dialog-actions">
            <button className="btn btn-ghost" disabled={isPosted || save.isPending} onClick={() => save.mutate()}>
              Save counts
            </button>
            <button className="btn btn-success" disabled={isPosted || post.isPending} onClick={() => post.mutate()}>
              Post stock-take
            </button>
          </div>
        </>
      )}
    </div>
  );
}
