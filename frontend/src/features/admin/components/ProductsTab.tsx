import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "../../../lib/apiClient";
import { Column, DataTable, Dialog } from "../../../components/ui";
import { adminApi, type AdminProduct, type ProductBody } from "../api";

const EMPTY: ProductBody = {
  code: "",
  name: "",
  category: "",
  stock_uom: "",
  purchase_uom: "",
  recipe_uom: "",
  reorder_level: "",
};

/** Product master data: list, create, and edit products. */
export function ProductsTab(): JSX.Element {
  const [editing, setEditing] = useState<AdminProduct | null>(null);
  const [creating, setCreating] = useState(false);

  const { data: products = [], isLoading } = useQuery({ queryKey: ["admin-products"], queryFn: adminApi.listProducts });

  const columns: Column<AdminProduct>[] = [
    { header: "Code", cell: (r) => <span className="mono">{r.code}</span> },
    { header: "Name", cell: (r) => r.name, className: "strong" },
    { header: "Category", cell: (r) => <span className="muted">{r.category}</span> },
    { header: "Stock UoM", cell: (r) => r.stock_uom },
    { header: "Reorder", align: "right", cell: (r) => <span className="mono">{r.reorder_level}</span> },
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
      <div className="toolbar">
        <div className="grow" />
        <button className="btn btn-primary" onClick={() => setCreating(true)}>
          <Plus size={16} /> New product
        </button>
      </div>

      <DataTable columns={columns} rows={products} rowKey={(r) => r.id} loading={isLoading} empty="No products yet." />

      {creating && <ProductDialog title="New product" onClose={() => setCreating(false)} />}
      {editing && <ProductDialog title="Edit product" product={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function ProductDialog({
  title,
  product,
  onClose,
}: {
  title: string;
  product?: AdminProduct;
  onClose: () => void;
}): JSX.Element {
  const qc = useQueryClient();
  const [form, setForm] = useState<ProductBody>(
    product
      ? {
          code: product.code,
          name: product.name,
          category: product.category,
          stock_uom: product.stock_uom,
          purchase_uom: product.purchase_uom,
          recipe_uom: product.recipe_uom,
          reorder_level: product.reorder_level,
        }
      : { ...EMPTY },
  );

  const set = (patch: Partial<ProductBody>): void => setForm((prev) => ({ ...prev, ...patch }));

  const save = useMutation({
    mutationFn: () => (product ? adminApi.updateProduct(product.id, form) : adminApi.createProduct(form)),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-products"] });
      onClose();
      toast.success(product ? "Product updated" : "Product created");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not save product"),
  });

  const canSubmit = form.code.trim() && form.name.trim();

  return (
    <Dialog open onClose={onClose} title={title}>
      <div className="form-grid">
        <div className="form-row">
          <label className="field">
            <span>Code</span>
            <input value={form.code} onChange={(e) => set({ code: e.target.value })} />
          </label>
          <label className="field">
            <span>Name</span>
            <input value={form.name} onChange={(e) => set({ name: e.target.value })} />
          </label>
        </div>
        <div className="form-row">
          <label className="field">
            <span>Category</span>
            <input value={form.category} onChange={(e) => set({ category: e.target.value })} />
          </label>
          <label className="field">
            <span>Reorder level</span>
            <input type="number" min={0} value={form.reorder_level} onChange={(e) => set({ reorder_level: e.target.value })} />
          </label>
        </div>
        <div className="form-row" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
          <label className="field">
            <span>Stock UoM</span>
            <input value={form.stock_uom} onChange={(e) => set({ stock_uom: e.target.value })} />
          </label>
          <label className="field">
            <span>Purchase UoM</span>
            <input value={form.purchase_uom} onChange={(e) => set({ purchase_uom: e.target.value })} />
          </label>
          <label className="field">
            <span>Recipe UoM</span>
            <input value={form.recipe_uom} onChange={(e) => set({ recipe_uom: e.target.value })} />
          </label>
        </div>
      </div>
      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn btn-primary" disabled={!canSubmit || save.isPending} onClick={() => save.mutate()}>
          Save
        </button>
      </div>
    </Dialog>
  );
}
