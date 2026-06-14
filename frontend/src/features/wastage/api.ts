import { api } from "../../lib/apiClient";
import type { Paginated, ReasonCode } from "../../types";

export type WastageEntryType = "BREAKAGE" | "SPOILAGE";

export interface Product {
  id: string;
  code: string;
  name: string;
  category: string;
  stock_uom: string;
  reorder_level: string;
}

export interface WastageEntry {
  id: string;
  entry_type: WastageEntryType;
  product: string;
  product_name?: string;
  location: string;
  location_name?: string;
  qty: string;
  reason_code: string;
  status: string;
  note?: string;
  created_at: string;
}

export interface CreateWastageBody {
  entry_type: WastageEntryType;
  product: string;
  location: string;
  qty: number;
  reason_code: string;
  note?: string;
}

export interface StockTakeLine {
  id: string;
  product: string;
  product_name?: string;
  system_qty: string;
  counted_qty: string | null;
  value: string | null;
  variance: string | null;
}

export interface StockTake {
  id: string;
  location: string;
  status: string;
  lines: StockTakeLine[];
}

export interface StockTakeCount {
  product: string;
  counted_qty: number;
}

/** Wastage logging and stock-take counting API surface. */
export const wastageApi = {
  list: () =>
    api.get<Paginated<WastageEntry>>("/wastage/?page_size=100").then((p) => p.results),
  create: (body: CreateWastageBody) => api.post<WastageEntry>("/wastage/", body),
  products: () =>
    api.get<Paginated<Product>>("/products/?page_size=500").then((p) => p.results),
  reasonCodes: (category: string) =>
    api
      .get<Paginated<ReasonCode>>(`/reason-codes/?category=${category}`)
      .then((p) => p.results),
  openStockTake: (location: string) =>
    api.post<StockTake>("/stock-takes/", { location }),
  getStockTake: (id: string) => api.get<StockTake>(`/stock-takes/${id}/`),
  saveCounts: (id: string, counts: StockTakeCount[]) =>
    api.put<StockTake>(`/stock-takes/${id}/lines/`, { counts }),
  postStockTake: (id: string) => api.post<StockTake>(`/stock-takes/${id}/post/`),
};
