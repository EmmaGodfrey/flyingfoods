import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, Plus, Send, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "../../lib/apiClient";
import { Column, DataTable, Dialog, PageHeader, StatusBadge } from "../../components/ui";
import {
  menuApi,
  type CreateMenuItemBody,
  type CreateRecipeVersionBody,
  type MenuItem,
  type RecipeVersion,
} from "./api";

interface DraftLine {
  product: string;
  qty: string;
}

const emptyLine: DraftLine = { product: "", qty: "" };

/** Menu items with a versioned draft-review-publish recipe workflow. */
export function MenuPage(): JSX.Element {
  const [selected, setSelected] = useState<MenuItem | null>(null);
  const [newItemOpen, setNewItemOpen] = useState(false);

  const { data: items = [], isLoading } = useQuery({ queryKey: ["menu-items"], queryFn: menuApi.listItems });

  const columns: Column<MenuItem>[] = [
    { header: "Item", cell: (r) => r.name, className: "strong" },
    { header: "POS code", cell: (r) => <span className="mono">{r.pos_code}</span> },
    { header: "Category", cell: (r) => <span className="muted">{r.category ?? "—"}</span> },
    {
      header: "",
      align: "right",
      cell: (r) => (
        <button className="btn btn-ghost" onClick={() => setSelected(r)}>
          Recipes <ChevronRight size={15} />
        </button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Menu & recipes"
        subtitle="Versioned recipes with a draft-review-publish workflow."
        actions={
          <button className="btn btn-primary" onClick={() => setNewItemOpen(true)}>
            <Plus size={16} /> New item
          </button>
        }
      />

      <DataTable columns={columns} rows={items} rowKey={(r) => r.id} loading={isLoading} empty="No menu items yet." />

      <NewItemDialog open={newItemOpen} onClose={() => setNewItemOpen(false)} />
      {selected && <RecipeVersionsDialog item={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function NewItemDialog({ open, onClose }: { open: boolean; onClose: () => void }): JSX.Element {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [posCode, setPosCode] = useState("");
  const [category, setCategory] = useState("");

  const create = useMutation({
    mutationFn: (body: CreateMenuItemBody) => menuApi.createItem(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["menu-items"] });
      setName("");
      setPosCode("");
      setCategory("");
      onClose();
      toast.success("Menu item created");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not create item"),
  });

  return (
    <Dialog open={open} onClose={onClose} title="New menu item">
      <div className="form-grid">
        <label className="field">
          <span>Name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <div className="form-row">
          <label className="field">
            <span>POS code</span>
            <input value={posCode} onChange={(e) => setPosCode(e.target.value)} />
          </label>
          <label className="field">
            <span>Category (optional)</span>
            <input value={category} onChange={(e) => setCategory(e.target.value)} />
          </label>
        </div>
      </div>
      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn btn-primary"
          disabled={!name.trim() || !posCode.trim() || create.isPending}
          onClick={() => create.mutate({ name, pos_code: posCode, category: category.trim() || undefined })}
        >
          Create item
        </button>
      </div>
    </Dialog>
  );
}

function RecipeVersionsDialog({ item, onClose }: { item: MenuItem; onClose: () => void }): JSX.Element {
  const qc = useQueryClient();
  const [newVersionOpen, setNewVersionOpen] = useState(false);
  const [publishing, setPublishing] = useState<RecipeVersion | null>(null);

  const { data: versions = [], isLoading } = useQuery({
    queryKey: ["recipe-versions", item.id],
    queryFn: () => menuApi.versions(item.id),
  });

  const invalidate = (): void => void qc.invalidateQueries({ queryKey: ["recipe-versions", item.id] });

  const submit = useMutation({
    mutationFn: (versionId: string) => menuApi.submitReview(versionId),
    onSuccess: () => {
      invalidate();
      toast.success("Submitted for review");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not submit"),
  });

  const columns: Column<RecipeVersion>[] = [
    { header: "Version", cell: (r) => <span className="mono">v{r.version_no}</span>, className: "strong" },
    { header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
    { header: "Price", align: "right", cell: (r) => (r.selling_price != null ? <span className="mono">{r.selling_price}</span> : "—") },
    { header: "Effective", cell: (r) => <span className="muted">{r.effective_from ?? "—"}</span> },
    {
      header: "",
      align: "right",
      cell: (r) => (
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          {(r.status === "DRAFT" || r.status === "REVISION_REQUESTED") && (
            <button className="btn btn-ghost" disabled={submit.isPending} onClick={() => submit.mutate(r.id)}>
              <Send size={15} /> Submit
            </button>
          )}
          {(r.status === "DRAFT" || r.status === "SUBMITTED" || r.status === "REVISION_REQUESTED") && (
            <button className="btn btn-success" onClick={() => setPublishing(r)}>
              <Upload size={15} /> Publish
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <Dialog open onClose={onClose} title={`Recipes — ${item.name}`}>
      <div className="toolbar">
        <div className="grow" />
        <button className="btn btn-primary" onClick={() => setNewVersionOpen(true)}>
          <Plus size={16} /> New version
        </button>
      </div>

      <DataTable columns={columns} rows={versions} rowKey={(r) => r.id} loading={isLoading} empty="No recipe versions yet." />

      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Close
        </button>
      </div>

      {newVersionOpen && (
        <NewVersionDialog
          item={item}
          onClose={() => setNewVersionOpen(false)}
          onCreated={() => {
            invalidate();
            setNewVersionOpen(false);
          }}
        />
      )}
      {publishing && (
        <PublishDialog
          version={publishing}
          onClose={() => setPublishing(null)}
          onPublished={() => {
            invalidate();
            setPublishing(null);
          }}
        />
      )}
    </Dialog>
  );
}

function NewVersionDialog({
  item,
  onClose,
  onCreated,
}: {
  item: MenuItem;
  onClose: () => void;
  onCreated: () => void;
}): JSX.Element {
  const [lines, setLines] = useState<DraftLine[]>([{ ...emptyLine }]);
  const [sellingPrice, setSellingPrice] = useState("");

  const { data: products = [] } = useQuery({ queryKey: ["products"], queryFn: menuApi.products, staleTime: 60 * 60 * 1000 });

  const update = (index: number, patch: Partial<DraftLine>): void =>
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  const remove = (index: number): void => setLines((prev) => prev.filter((_, i) => i !== index));

  const create = useMutation({
    mutationFn: (body: CreateRecipeVersionBody) => menuApi.createVersion(item.id, body),
    onSuccess: () => {
      onCreated();
      toast.success("Recipe version created");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not create version"),
  });

  const recipeLines = lines
    .filter((line) => line.product && Number(line.qty) > 0)
    .map((line) => ({ product: line.product, qty_per_serving: Number(line.qty) }));

  return (
    <Dialog open onClose={onClose} title="New recipe version">
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
              <span>Qty / serving</span>
              <input type="number" min={0} value={line.qty} onChange={(e) => update(index, { qty: e.target.value })} />
            </label>
            <button className="btn btn-ghost" disabled={lines.length === 1} onClick={() => remove(index)}>
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        <button className="btn btn-ghost" onClick={() => setLines([...lines, { ...emptyLine }])}>
          <Plus size={15} /> Add line
        </button>

        <label className="field">
          <span>Selling price (optional)</span>
          <input type="number" min={0} value={sellingPrice} onChange={(e) => setSellingPrice(e.target.value)} />
        </label>
      </div>

      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn btn-primary"
          disabled={recipeLines.length === 0 || create.isPending}
          onClick={() =>
            create.mutate({
              lines: recipeLines,
              selling_price: sellingPrice ? Number(sellingPrice) : undefined,
            })
          }
        >
          Create version
        </button>
      </div>
    </Dialog>
  );
}

function PublishDialog({
  version,
  onClose,
  onPublished,
}: {
  version: RecipeVersion;
  onClose: () => void;
  onPublished: () => void;
}): JSX.Element {
  const [effectiveFrom, setEffectiveFrom] = useState("");

  const publish = useMutation({
    mutationFn: () => menuApi.publish(version.id, effectiveFrom),
    onSuccess: () => {
      onPublished();
      toast.success("Recipe published");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not publish"),
  });

  return (
    <Dialog open onClose={onClose} title={`Publish v${version.version_no}`}>
      <label className="field">
        <span>Effective from</span>
        <input type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
      </label>
      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn btn-success" disabled={!effectiveFrom || publish.isPending} onClick={() => publish.mutate()}>
          Publish
        </button>
      </div>
    </Dialog>
  );
}
