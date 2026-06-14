import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "../../../lib/apiClient";
import { Column, DataTable, Dialog } from "../../../components/ui";
import { adminApi, type AdminSupplier, type SupplierBody } from "../api";

const EMPTY: SupplierBody = { name: "", email: "", contact_name: "", phone: "" };

/** Supplier master data: list, create, and edit suppliers. */
export function SuppliersTab(): JSX.Element {
  const [editing, setEditing] = useState<AdminSupplier | null>(null);
  const [creating, setCreating] = useState(false);

  const { data: suppliers = [], isLoading } = useQuery({ queryKey: ["admin-suppliers"], queryFn: adminApi.listSuppliers });

  const columns: Column<AdminSupplier>[] = [
    { header: "Name", cell: (r) => r.name, className: "strong" },
    { header: "Contact", cell: (r) => <span className="muted">{r.contact_name || "—"}</span> },
    { header: "Email", cell: (r) => <span className="muted">{r.email || "—"}</span> },
    { header: "Phone", cell: (r) => <span className="mono">{r.phone || "—"}</span> },
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
          <Plus size={16} /> New supplier
        </button>
      </div>

      <DataTable columns={columns} rows={suppliers} rowKey={(r) => r.id} loading={isLoading} empty="No suppliers yet." />

      {creating && <SupplierDialog title="New supplier" onClose={() => setCreating(false)} />}
      {editing && <SupplierDialog title="Edit supplier" supplier={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function SupplierDialog({
  title,
  supplier,
  onClose,
}: {
  title: string;
  supplier?: AdminSupplier;
  onClose: () => void;
}): JSX.Element {
  const qc = useQueryClient();
  const [form, setForm] = useState<SupplierBody>(
    supplier
      ? { name: supplier.name, email: supplier.email, contact_name: supplier.contact_name, phone: supplier.phone }
      : { ...EMPTY },
  );

  const set = (patch: Partial<SupplierBody>): void => setForm((prev) => ({ ...prev, ...patch }));

  const save = useMutation({
    mutationFn: () => (supplier ? adminApi.updateSupplier(supplier.id, form) : adminApi.createSupplier(form)),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-suppliers"] });
      onClose();
      toast.success(supplier ? "Supplier updated" : "Supplier created");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not save supplier"),
  });

  return (
    <Dialog open onClose={onClose} title={title}>
      <div className="form-grid">
        <label className="field">
          <span>Name</span>
          <input value={form.name} onChange={(e) => set({ name: e.target.value })} />
        </label>
        <div className="form-row">
          <label className="field">
            <span>Contact name</span>
            <input value={form.contact_name} onChange={(e) => set({ contact_name: e.target.value })} />
          </label>
          <label className="field">
            <span>Phone</span>
            <input value={form.phone} onChange={(e) => set({ phone: e.target.value })} />
          </label>
        </div>
        <label className="field">
          <span>Email</span>
          <input type="email" value={form.email} onChange={(e) => set({ email: e.target.value })} />
        </label>
      </div>
      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn btn-primary" disabled={!form.name.trim() || save.isPending} onClick={() => save.mutate()}>
          Save
        </button>
      </div>
    </Dialog>
  );
}
