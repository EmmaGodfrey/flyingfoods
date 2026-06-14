import { api } from "../../lib/apiClient";
import type { Paginated, Role } from "../../types";

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface CreateUserBody {
  email: string;
  full_name: string;
  role: Role;
  password: string;
}

export interface AdminProduct {
  id: string;
  code: string;
  name: string;
  category: string;
  stock_uom: string;
  purchase_uom: string;
  recipe_uom: string;
  reorder_level: string;
}

export type ProductBody = Omit<AdminProduct, "id">;

export interface AdminSupplier {
  id: string;
  name: string;
  email: string;
  contact_name: string;
  phone: string;
}

export type SupplierBody = Omit<AdminSupplier, "id">;

export interface Threshold {
  id: string;
  scope: string;
  amount: string;
}

export interface IntegrationHealth {
  key: string;
  label: string;
  status: string;
  detail?: string | null;
  failure_count?: number;
  last_run_at?: string | null;
}

/** Administration: users, products, suppliers, thresholds, integration health. */
export const adminApi = {
  listUsers: () => api.get<Paginated<AdminUser>>("/users/?page_size=200").then((p) => p.results),
  createUser: (body: CreateUserBody) => api.post<AdminUser>("/users/", body),
  setUserActive: (id: string, isActive: boolean) =>
    api.patch<AdminUser>(`/users/${id}/`, { is_active: isActive }),

  listProducts: () => api.get<Paginated<AdminProduct>>("/products/?page_size=500").then((p) => p.results),
  createProduct: (body: ProductBody) => api.post<AdminProduct>("/products/", body),
  updateProduct: (id: string, body: ProductBody) => api.patch<AdminProduct>(`/products/${id}/`, body),

  listSuppliers: () => api.get<Paginated<AdminSupplier>>("/suppliers/?page_size=200").then((p) => p.results),
  createSupplier: (body: SupplierBody) => api.post<AdminSupplier>("/suppliers/", body),
  updateSupplier: (id: string, body: SupplierBody) => api.patch<AdminSupplier>(`/suppliers/${id}/`, body),

  listThresholds: () => api.get<Paginated<Threshold>>("/thresholds/?page_size=100").then((p) => p.results),
  updateThreshold: (id: string, amount: number) =>
    api.patch<Threshold>(`/thresholds/${id}/`, { amount }),

  integrationHealth: () => api.get<IntegrationHealth[]>("/integration-health/"),
};

export const ROLES: Role[] = [
  "CHEF",
  "WAITER",
  "STOREKEEPER",
  "RECEIVING_OFFICER",
  "UNIT_ISSUER",
  "RESTAURANT_ISSUER",
  "MANAGER",
  "ADMIN",
];
