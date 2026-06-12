import type {
  GoodsReceivedNote,
  GoodsReceivedNoteCreateInput,
  ProcurementOrdersReportResponse,
  ProcurementSpendResponse,
  PurchaseOrder,
  PurchaseOrderCreateInput,
  PurchaseOrderListResponse,
  Supplier,
  SupplierCreateInput,
  SupplierListResponse,
  SupplierUpdateInput,
} from "../../types";

import type { ApiTransport } from "../transport";

export function createProcurementApi(transport: ApiTransport) {
  return {
    createPurchaseOrder: (input: PurchaseOrderCreateInput) =>
      transport.request<PurchaseOrder>("/procurement/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      }),

    listPurchaseOrders: (params: { limit?: number; offset?: number; status?: string; supplierId?: number }) => {
      const query = new URLSearchParams({
        limit: String(params.limit ?? 20),
        offset: String(params.offset ?? 0),
      });
      if (params.status) {
        query.set("status", params.status);
      }
      if (params.supplierId) {
        query.set("supplier_id", String(params.supplierId));
      }
      return transport.request<PurchaseOrderListResponse>(`/procurement/orders?${query.toString()}`);
    },

    submitPurchaseOrder: (purchaseOrderId: number) =>
      transport.request<PurchaseOrder>(`/procurement/orders/${purchaseOrderId}/submit`, { method: "PUT" }),

    approvePurchaseOrder: (purchaseOrderId: number) =>
      transport.request<PurchaseOrder>(`/procurement/orders/${purchaseOrderId}/approve`, { method: "PUT" }),

    createGoodsReceivedNote: (input: GoodsReceivedNoteCreateInput) =>
      transport.request<GoodsReceivedNote>("/procurement/grn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      }),

    getProcurementOrdersReport: (params: { status?: string }) => {
      const query = new URLSearchParams({ limit: "20", offset: "0" });
      if (params.status) {
        query.set("status", params.status);
      }
      return transport.request<ProcurementOrdersReportResponse>(`/procurement/reports/orders?${query.toString()}`);
    },

    getProcurementSpendReport: () => transport.request<ProcurementSpendResponse>("/procurement/reports/spend"),

    listSuppliers: (params: { limit?: number; offset?: number; search?: string; isActive?: boolean }) => {
      const query = new URLSearchParams({
        limit: String(params.limit ?? 20),
        offset: String(params.offset ?? 0),
      });
      if (params.search?.trim()) {
        query.set("search", params.search.trim());
      }
      if (typeof params.isActive === "boolean") {
        query.set("is_active", String(params.isActive));
      }
      return transport.request<SupplierListResponse>(`/procurement/suppliers?${query.toString()}`);
    },

    createSupplier: (input: SupplierCreateInput) =>
      transport.request<Supplier>("/procurement/suppliers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      }),

    updateSupplier: (supplierId: number, input: SupplierUpdateInput) =>
      transport.request<Supplier>(`/procurement/suppliers/${supplierId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      }),

    deleteSupplier: (supplierId: number) =>
      transport.request<void>(`/procurement/suppliers/${supplierId}`, {
        method: "DELETE",
      }),
  };
}
