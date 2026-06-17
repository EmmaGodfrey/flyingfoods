import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "../../lib/apiClient";
import { Column, DataTable, Dialog, PageHeader, StatusBadge } from "../../components/ui";
import { stockApi, type Location } from "../stock/api";
import {
  issuesApi,
  type CreateIssueBody,
  type CreateTransferBody,
  type IssueDoc,
  type MovementLine,
} from "./api";

type Mode = "ISSUES" | "TRANSFERS";

interface DraftLine {
  product: string;
  qty: string;
}

const emptyLine: DraftLine = { product: "", qty: "" };

/** Daily issues to the kitchen/unit and inter-location transfers. */
export function IssuesPage(): JSX.Element {
  const [mode, setMode] = useState<Mode>("ISSUES");

  return (
    <div>
      <PageHeader
        title="Issues & transfers"
        subtitle="Daily issues to the kitchen, Tue/Thu unit orders, and inter-unit transfers."
      />

      <div className="toolbar">
        <div className="seg">
          <button className={mode === "ISSUES" ? "active" : ""} onClick={() => setMode("ISSUES")}>
            Issues
          </button>
          <button className={mode === "TRANSFERS" ? "active" : ""} onClick={() => setMode("TRANSFERS")}>
            Transfers
          </button>
        </div>
      </div>

      {mode === "ISSUES" ? <IssuesTab /> : <TransfersTab />}
    </div>
  );
}

function LineRows({
  lines,
  products,
  onChange,
}: {
  lines: DraftLine[];
  products: { id: string; name: string; code: string }[];
  onChange: (lines: DraftLine[]) => void;
}): JSX.Element {
  const update = (index: number, patch: Partial<DraftLine>): void =>
    onChange(lines.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  const remove = (index: number): void => onChange(lines.filter((_, i) => i !== index));

  return (
    <div className="form-grid">
      {lines.map((line, index) => (
        <div className="form-row" key={index} style={{ gridTemplateColumns: "2fr 1fr auto", alignItems: "end" }}>
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
          <button className="btn btn-ghost" disabled={lines.length === 1} onClick={() => remove(index)}>
            <Trash2 size={15} />
          </button>
        </div>
      ))}
      <button className="btn btn-ghost" onClick={() => onChange([...lines, { ...emptyLine }])}>
        <Plus size={15} /> Add line
      </button>
    </div>
  );
}

function toLines(lines: DraftLine[]): MovementLine[] {
  return lines
    .filter((line) => line.product && Number(line.qty) > 0)
    .map((line) => ({ product: line.product, qty: Number(line.qty) }));
}

/** "Beef patty ×20, Burger bun ×5 +1 more" — a compact line summary. */
function summariseLines(lines?: IssueDoc["lines"]): string {
  if (!lines || lines.length === 0) return "—";
  const fmt = (l: NonNullable<IssueDoc["lines"]>[number]): string => {
    const qty = String(l.qty).replace(/\.?0+$/, "");
    return `${l.product_name ?? l.product.slice(0, 8)} ×${qty}`;
  };
  const shown = lines.slice(0, 2).map(fmt).join(", ");
  const extra = lines.length > 2 ? ` +${lines.length - 2} more` : "";
  return shown + extra;
}

function DocTable({
  rows,
  loading,
  empty,
  onPost,
  posting,
}: {
  rows: IssueDoc[];
  loading: boolean;
  empty: string;
  onPost: (id: string) => void;
  posting: boolean;
}): JSX.Element {
  const columns: Column<IssueDoc>[] = [
    { header: "Source", cell: (r) => <span className="muted">{r.source_name ?? r.source}</span> },
    { header: "Destination", cell: (r) => <span className="strong">{r.destination_name ?? r.destination}</span> },
    { header: "Items", cell: (r) => <span>{summariseLines(r.lines)}</span> },
    { header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
    {
      header: "",
      align: "right",
      cell: (r) =>
        r.status === "POSTED" ? null : (
          <button className="btn btn-success" disabled={posting} onClick={() => onPost(r.id)}>
            <Send size={15} /> Post
          </button>
        ),
    },
  ];
  return <DataTable columns={columns} rows={rows} rowKey={(r) => r.id} loading={loading} empty={empty} />;
}

function IssuesTab(): JSX.Element {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [offReason, setOffReason] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([{ ...emptyLine }]);

  const { data: docs = [], isLoading } = useQuery({ queryKey: ["issues", "list"], queryFn: issuesApi.listIssues });
  const { data: locations = [] } = useQuery({ queryKey: ["locations"], queryFn: stockApi.locations, staleTime: 60 * 60 * 1000 });
  const { data: products = [] } = useQuery({ queryKey: ["products"], queryFn: issuesApi.products, staleTime: 60 * 60 * 1000 });
  const { data: reasons = [] } = useQuery({
    queryKey: ["reason-codes", "ISSUE_DAY"],
    queryFn: () => issuesApi.reasonCodes("ISSUE_DAY"),
    staleTime: 60 * 60 * 1000,
  });

  const destinationIsUnit = locations.find((l: Location) => l.id === destination)?.kind === "UNIT";

  const reset = (): void => {
    setSource("");
    setDestination("");
    setOffReason("");
    setLines([{ ...emptyLine }]);
  };

  const create = useMutation({
    mutationFn: (body: CreateIssueBody) => issuesApi.createIssue(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["issues"] });
      reset();
      setOpen(false);
      toast.success("Issue created");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not create issue"),
  });

  const post = useMutation({
    mutationFn: (id: string) => issuesApi.postIssue(id, crypto.randomUUID()),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["issues"] });
      void qc.invalidateQueries({ queryKey: ["stock"] });
      toast.success("Issue posted");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not post issue"),
  });

  const canSubmit = source && destination && toLines(lines).length > 0;

  return (
    <div>
      <div className="toolbar">
        <div className="grow" />
        <button className="btn btn-primary" onClick={() => setOpen(true)}>
          <Plus size={16} /> New issue
        </button>
      </div>

      <DocTable rows={docs} loading={isLoading} empty="No issues yet." onPost={(id) => post.mutate(id)} posting={post.isPending} />

      <Dialog open={open} onClose={() => setOpen(false)} title="New issue">
        <div className="form-grid">
          <div className="form-row">
            <label className="field">
              <span>Source</span>
              <select value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="">Select…</option>
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Destination</span>
              <select value={destination} onChange={(e) => setDestination(e.target.value)}>
                <option value="">Select…</option>
                {locations.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {destinationIsUnit && (
            <label className="field">
              <span>Off-schedule reason</span>
              <select value={offReason} onChange={(e) => setOffReason(e.target.value)}>
                <option value="">None (Tue/Thu schedule)</option>
                {reasons.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
          )}

          <LineRows lines={lines} products={products} onChange={setLines} />
        </div>

        <div className="dialog-actions">
          <button className="btn btn-ghost" onClick={() => setOpen(false)}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            disabled={!canSubmit || create.isPending}
            onClick={() =>
              create.mutate({
                source,
                destination,
                lines: toLines(lines),
                off_schedule_reason: offReason || undefined,
              })
            }
          >
            Create issue
          </button>
        </div>
      </Dialog>
    </div>
  );
}

function TransfersTab(): JSX.Element {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([{ ...emptyLine }]);

  const { data: docs = [], isLoading } = useQuery({ queryKey: ["transfers", "list"], queryFn: issuesApi.listTransfers });
  const { data: locations = [] } = useQuery({ queryKey: ["locations"], queryFn: stockApi.locations, staleTime: 60 * 60 * 1000 });
  const { data: products = [] } = useQuery({ queryKey: ["products"], queryFn: issuesApi.products, staleTime: 60 * 60 * 1000 });

  const transferable = locations.filter((l: Location) => l.kind === "KITCHEN" || l.kind === "UNIT");

  const reset = (): void => {
    setSource("");
    setDestination("");
    setLines([{ ...emptyLine }]);
  };

  const create = useMutation({
    mutationFn: (body: CreateTransferBody) => issuesApi.createTransfer(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["transfers"] });
      reset();
      setOpen(false);
      toast.success("Transfer created");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not create transfer"),
  });

  const post = useMutation({
    mutationFn: (id: string) => issuesApi.postTransfer(id, crypto.randomUUID()),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["transfers"] });
      void qc.invalidateQueries({ queryKey: ["stock"] });
      toast.success("Transfer posted");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not post transfer"),
  });

  const canSubmit = source && destination && source !== destination && toLines(lines).length > 0;

  return (
    <div>
      <div className="toolbar">
        <div className="grow" />
        <button className="btn btn-primary" onClick={() => setOpen(true)}>
          <Plus size={16} /> New transfer
        </button>
      </div>

      <DocTable rows={docs} loading={isLoading} empty="No transfers yet." onPost={(id) => post.mutate(id)} posting={post.isPending} />

      <Dialog open={open} onClose={() => setOpen(false)} title="New transfer">
        <div className="form-grid">
          <div className="form-row">
            <label className="field">
              <span>Source</span>
              <select value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="">Select…</option>
                {transferable.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Destination</span>
              <select value={destination} onChange={(e) => setDestination(e.target.value)}>
                <option value="">Select…</option>
                {transferable.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <LineRows lines={lines} products={products} onChange={setLines} />
        </div>

        <div className="dialog-actions">
          <button className="btn btn-ghost" onClick={() => setOpen(false)}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            disabled={!canSubmit || create.isPending}
            onClick={() => create.mutate({ source, destination, lines: toLines(lines) })}
          >
            Create transfer
          </button>
        </div>
      </Dialog>
    </div>
  );
}
