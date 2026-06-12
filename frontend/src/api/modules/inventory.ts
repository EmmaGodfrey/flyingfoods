import type {
  Category,
  MovementCreateInput,
  Product,
  ProductFormInput,
  ProductListResponse,
  StockMovement,
  StockMovementListResponse,
  StockSummary,
  Unit,
} from "../../types";

import type { ApiTransport } from "../transport";

export function createInventoryApi(transport: ApiTransport) {
  return {
    listCategories: (params?: { activeOnly?: boolean }) => {
      const query = new URLSearchParams();
      if (params?.activeOnly !== undefined) {
        query.set("active_only", String(params.activeOnly));
      }
      const suffix = query.toString();
      return transport.request<Category[]>(`/inventory/categories${suffix ? `?${suffix}` : ""}`);
    },

    listUnits: (params?: { activeOnly?: boolean }) => {
      const query = new URLSearchParams();
      if (params?.activeOnly !== undefined) {
        query.set("active_only", String(params.activeOnly));
      }
      const suffix = query.toString();
      return transport.request<Unit[]>(`/inventory/units${suffix ? `?${suffix}` : ""}`);
    },

    listProducts: (params: { limit: number; offset: number; search: string }) => {
      const query = new URLSearchParams({
        limit: String(params.limit),
        offset: String(params.offset),
      });
      if (params.search.trim()) {
        query.set("search", params.search.trim());
      }
      return transport.request<ProductListResponse>(`/inventory/products?${query.toString()}`);
    },

    createProduct: (input: ProductFormInput) =>
      transport.request<Product>("/inventory/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: input.name,
          unit_id: Number(input.unit_id),
          category_id: input.category_id ? Number(input.category_id) : null,
          supplier_id: input.supplier_id ? Number(input.supplier_id) : null,
          sku: input.sku || null,
          barcode: input.barcode || null,
          reorder_level: input.reorder_level,
          cost_price: input.cost_price,
          selling_price: input.selling_price,
        }),
      }),

    updateProduct: (productId: number, input: ProductFormInput) =>
      transport.request<Product>(`/inventory/products/${productId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: input.name,
          unit_id: Number(input.unit_id),
          category_id: input.category_id ? Number(input.category_id) : null,
          supplier_id: input.supplier_id ? Number(input.supplier_id) : null,
          sku: input.sku || null,
          barcode: input.barcode || null,
          reorder_level: input.reorder_level,
          cost_price: input.cost_price,
          selling_price: input.selling_price,
        }),
      }),

    listStockSummary: () => transport.request<StockSummary[]>("/inventory/stock/current"),

    listMovements: (params: {
      limit: number;
      offset: number;
      movementType?: string;
      occurredAfter?: string;
      occurredBefore?: string;
    }) => {
      const query = new URLSearchParams({
        limit: String(params.limit),
        offset: String(params.offset),
      });
      if (params.movementType && params.movementType !== "all") {
        query.set("movement_type", params.movementType);
      }
      if (params.occurredAfter) {
        query.set("occurred_after", params.occurredAfter);
      }
      if (params.occurredBefore) {
        query.set("occurred_before", params.occurredBefore);
      }
      return transport.request<StockMovementListResponse>(`/inventory/movements?${query.toString()}`);
    },

    createMovement: (input: MovementCreateInput) =>
      transport.request<StockMovement>("/inventory/movements", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: input.product_id,
          qty: input.qty,
          movement_type: input.movement_type,
          reference_id: input.reference_id || null,
        }),
      }),
  };
}
