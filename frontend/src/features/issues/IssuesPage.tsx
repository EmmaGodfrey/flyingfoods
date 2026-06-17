import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "../../lib/apiClient";
import { Column, DataTable, Dialog, PageHeader, StatusBadge } from "../../components/ui";
import { canIssue } from "../../app/permissions";
import { useAuthStore } from "../../store/authStore";
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
  available,
  onChange,
}: {
  lines: DraftLine[];
  products: { id: string; name: string; code: string }[];
  /** product id → quantity on hand at the chosen source, when a source is set. */
  available?: Record<string, number>;
  onChange: (lines: DraftLine[]) => void;
}): JSX.Element {
  const update = (index: number, patch: Partial<DraftLine>): void =>
    onChange(lines.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  const remove = (index: number): void => onChange(lines.filter((_, i) => i !== index));

  return (
    <div className="form-grid">
      {lines.map((line, index) => {
        const avail = available && line.product ? available[line.product] ?? 0 : undefined;
        const over = avail !== undefined && Number(line.qty) > avail;
        return (
          <div key={index}>
            <div className="form-row" style={{ gridTemplateColumns: "2fr 1fr auto", alignItems: "end" }}>
              <label className="field">
                <span>Product</span>
                <select value={line.product} onChange={(e) => update(index, { product: e.target.value })}>
                  <option value="">Select…</option>
                  {products.map((p) => {
                    const a = available ? available[p.id] ?? 0 : undefined;
                    return (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.code}){a !== undefined ? ` — ${a} on hand` : ""}
                      </option>
                    );
                  })}
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
            {over && (
              <div style={{ color: "var(--danger, #d22)", fontSize: 12, marginTop: 4 }}>
                Only {avail} on hand at the source — this won't post.
              </div>
            )}
          </div>
        );
      })}
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

/** Turn a post failure into a message that tells the user what to fix.
 *
 * Duck-types the error code rather than using `instanceof ApiError`, which can
 * fail across Vite hot-reload module boundaries. */
function postErrorMessage(error: unknown, kind: "issue" | "transfer"): string {
  const e = error as { code?: string; message?: string } | null;
  if (e?.code === "INSUFFICIENT_STOCK") {
    return "Not enough stock at the source — posting this would take a balance negative.";
  }
  if (e?.code === "OFF_SCHEDULE_REASON_REQUIRED") {
    return "Issues to the Unit outside Tue/Thu need an off-schedule reason.";
  }
  return e?.message || `Could not post ${kind}.`;
}

type DocLines = IssueDoc["lines"];

/** Product names, first two then "+N more". */
function summariseProducts(lines?: DocLines): string {
  if (!lines || lines.length === 0) return "—";
  const shown = lines.slice(0, 2).map((l) => l.product_name ?? l.product.slice(0, 8)).join(", ");
  return shown + (lines.length > 2 ? ` +${lines.length - 2} more` : "");
}

/** Matching quantities (trailing zeros trimmed), aligned with the products. */
function summariseQtys(lines?: DocLines): string {
  if (!lines || lines.length === 0) return "—";
  const shown = lines.slice(0, 2).map((l) => String(l.qty).replace(/\.?0+$/, "")).join(", ");
  return shown + (lines.length > 2 ? " …" : "");
}

function DocTable({
  rows,
  loading,
  empty,
  onPost,
  posting,
  canManage,
}: {
  rows: IssueDoc[];
  loading: boolean;
  empty: string;
  onPost: (id: string) => void;
  posting: boolean;
  canManage: boolean;
}): JSX.Element {
  const columns: Column<IssueDoc>[] = [
    { header: "Source", cell: (r) => <span className="muted">{r.source_name ?? r.source}</span> },
    { header: "Destination", cell: (r) => <span className="strong">{r.destination_name ?? r.destination}</span> },
    { header: "Items", cell: (r) => <span>{summariseProducts(r.lines)}</span> },
    { header: "Qty", align: "right", cell: (r) => <span className="mono">{summariseQtys(r.lines)}</span> },
    { header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
    {
      header: "",
      align: "right",
      cell: (r) =>
        r.status === "POSTED" ? null : (
          <button
            className="btn btn-success"
            disabled={posting || !canManage}
            title={canManage ? undefined : "Only storekeepers and issuers can post"}
            onClick={() => onPost(r.id)}
          >
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
  const { data: sourceStock = [] } = useQuery({
    queryKey: ["stock-balances", source],
    queryFn: () => stockApi.balances({ location: source }),
    enabled: !!source,
  });
  const available = Object.fromEntries(sourceStock.map((b) => [b.product, Number(b.qty_on_hand)]));

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
    onError: (error) => toast.error(postErrorMessage(error, "issue")),
  });

  const canManage = canIssue(useAuthStore((s) => s.user?.role));
  const canSubmit = source && destination && toLines(lines).length > 0;

  return (
    <div>
      <div className="toolbar">
        <div className="grow" />
        <button
          className="btn btn-primary"
          disabled={!canManage}
          title={canManage ? undefined : "Only storekeepers and issuers can create issues"}
          onClick={() => setOpen(true)}
        >
          <Plus size={16} /> New issue
        </button>
      </div>

      <DocTable rows={docs} loading={isLoading} empty="No issues yet." onPost={(id) => post.mutate(id)} posting={post.isPending} canManage={canManage} />

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

          <LineRows lines={lines} products={products} available={source ? available : undefined} onChange={setLines} />
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
  const { data: sourceStock = [] } = useQuery({
    queryKey: ["stock-balances", source],
    queryFn: () => stockApi.balances({ location: source }),
    enabled: !!source,
  });
  const available = Object.fromEntries(sourceStock.map((b) => [b.product, Number(b.qty_on_hand)]));

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
    onError: (error) => toast.error(postErrorMessage(error, "transfer")),
  });

  const canManage = canIssue(useAuthStore((s) => s.user?.role));
  const canSubmit = source && destination && source !== destination && toLines(lines).length > 0;

  return (
    <div>
      <div className="toolbar">
        <div className="grow" />
        <button
          className="btn btn-primary"
          disabled={!canManage}
          title={canManage ? undefined : "Only storekeepers and issuers can create transfers"}
          onClick={() => setOpen(true)}
        >
          <Plus size={16} /> New transfer
        </button>
      </div>

      <DocTable rows={docs} loading={isLoading} empty="No transfers yet." onPost={(id) => post.mutate(id)} posting={post.isPending} canManage={canManage} />

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

          <LineRows lines={lines} products={products} available={source ? available : undefined} onChange={setLines} />
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
