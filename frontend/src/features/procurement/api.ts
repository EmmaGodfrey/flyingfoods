import { api } from "../../lib/apiClient";
import type { Paginated } from "../../types";
import type { Product } from "../wastage/api";

export interface BudgetLine {
  product: string;
  qty: number;
  est_unit_cost: number;
}

export interface Budget {
  id: string;
  reference?: string;
  status: string;
  total?: string | null;
  created_at: string;
}

export interface Supplier {
  id: string;
  name: string;
  email?: string | null;
  contact_name?: string | null;
  phone?: string | null;
}

export interface PurchaseOrderLine {
  id: string;
  product: string;
  product_name?: string;
  qty: string;
  unit_price: string;
}

export interface PurchaseOrder {
  id: string;
  reference?: string;
  supplier: string;
  supplier_name?: string;
  status: string;
  total?: string | null;
  lines?: PurchaseOrderLine[];
  created_at: string;
}

export interface CreateBudgetBody {
  lines: BudgetLine[];
}

export interface CreatePurchaseOrderBody {
  budget: string;
  supplier: string;
  lines: { product: string; qty: number; unit_price: number }[];
}

export interface GrnLine {
  po_line: string;
  qty_received: number;
  unit_cost: number;
  condition?: string;
  variance_reason?: string;
}

/** Procurement: budgets, purchase orders, goods received. */
export const procurementApi = {
  listBudgets: () =>
    api.get<Paginated<Budget>>("/budgets/?page_size=100").then((p) => p.results),
  createBudget: (body: CreateBudgetBody) => api.post<Budget>("/budgets/", body),
  submitBudget: (id: string) => api.post<Budget>(`/budgets/${id}/submit/`),
  listPurchaseOrders: () =>
    api.get<Paginated<PurchaseOrder>>("/purchase-orders/?page_size=100").then((p) => p.results),
  getPurchaseOrder: (id: string) => api.get<PurchaseOrder>(`/purchase-orders/${id}/`),
  createPurchaseOrder: (body: CreatePurchaseOrderBody) =>
    api.post<PurchaseOrder>("/purchase-orders/", body),
  sendPurchaseOrder: (id: string) => api.post<PurchaseOrder>(`/purchase-orders/${id}/send/`),
  createGrn: (id: string, lines: GrnLine[]) =>
    api.post<PurchaseOrder>(`/purchase-orders/${id}/grns/`, { lines }),
  createInvoice: (id: string, body: { invoice_ref: string; amount: number }) =>
    api.post(`/purchase-orders/${id}/invoices/`, body),
  suppliers: () =>
    api.get<Paginated<Supplier>>("/suppliers/?page_size=200").then((p) => p.results),
  products: () =>
    api.get<Paginated<Product>>("/products/?page_size=500").then((p) => p.results),
};
