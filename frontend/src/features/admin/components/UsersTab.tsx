import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, UserX } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "../../../lib/apiClient";
import { Column, DataTable, Dialog, StatusBadge } from "../../../components/ui";
import type { Role } from "../../../types";
import { adminApi, ROLES, type AdminUser, type CreateUserBody } from "../api";

/** User administration: list, create, and deactivate accounts. */
export function UsersTab(): JSX.Element {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  const { data: users = [], isLoading } = useQuery({ queryKey: ["users"], queryFn: adminApi.listUsers });

  const deactivate = useMutation({
    mutationFn: (id: string) => adminApi.setUserActive(id, false),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("User deactivated");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not deactivate user"),
  });

  const columns: Column<AdminUser>[] = [
    { header: "Name", cell: (r) => r.full_name, className: "strong" },
    { header: "Email", cell: (r) => <span className="muted">{r.email}</span> },
    { header: "Role", cell: (r) => <span className="mono">{r.role.replaceAll("_", " ").toLowerCase()}</span> },
    { header: "Status", cell: (r) => <StatusBadge status={r.is_active ? "ACTIVE" : "INACTIVE"} /> },
    {
      header: "",
      align: "right",
      cell: (r) =>
        r.is_active ? (
          <button className="btn btn-ghost" disabled={deactivate.isPending} onClick={() => deactivate.mutate(r.id)}>
            <UserX size={15} /> Deactivate
          </button>
        ) : null,
    },
  ];

  return (
    <div>
      <div className="toolbar">
        <div className="grow" />
        <button className="btn btn-primary" onClick={() => setOpen(true)}>
          <Plus size={16} /> New user
        </button>
      </div>

      <DataTable columns={columns} rows={users} rowKey={(r) => r.id} loading={isLoading} empty="No users yet." />

      <NewUserDialog open={open} onClose={() => setOpen(false)} />
    </div>
  );
}

function NewUserDialog({ open, onClose }: { open: boolean; onClose: () => void }): JSX.Element {
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Role>("CHEF");
  const [password, setPassword] = useState("");

  const create = useMutation({
    mutationFn: (body: CreateUserBody) => adminApi.createUser(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["users"] });
      setEmail("");
      setFullName("");
      setRole("CHEF");
      setPassword("");
      onClose();
      toast.success("User created");
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not create user"),
  });

  const canSubmit = email.trim() && fullName.trim() && password.trim();

  return (
    <Dialog open={open} onClose={onClose} title="New user">
      <div className="form-grid">
        <div className="form-row">
          <label className="field">
            <span>Email</span>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="field">
            <span>Full name</span>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </label>
        </div>
        <div className="form-row">
          <label className="field">
            <span>Role</span>
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r.replaceAll("_", " ").toLowerCase()}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
        </div>
      </div>
      <div className="dialog-actions">
        <button className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn btn-primary"
          disabled={!canSubmit || create.isPending}
          onClick={() => create.mutate({ email, full_name: fullName, role, password })}
        >
          Create user
        </button>
      </div>
    </Dialog>
  );
}
