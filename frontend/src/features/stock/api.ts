import { api } from "../../lib/apiClient";
import type { Paginated } from "../../types";

export interface Location {
  id: string;
  name: string;
  kind: "STORES" | "KITCHEN" | "UNIT";
}

export interface StockBalance {
  id: string;
  product: string;
  product_code: string;
  product_name: string;
  location: string;
  location_name: string;
  qty_on_hand: string;
  last_movement_at: string | null;
}

export interface StockMovement {
  id: string;
  product: string;
  location: string;
  qty_delta: string;
  movement_type: string;
  document_type: string;
  unit_cost: string | null;
  posted_at: string;
}

export const stockApi = {
  locations: () => api.get<Paginated<Location>>("/locations/").then((p) => p.results),
  balances: (params: { location?: string; below_reorder?: boolean }) => {
    const qs = new URLSearchParams();
    if (params.location) qs.set("location", params.location);
    if (params.below_reorder) qs.set("below_reorder", "true");
    qs.set("page_size", "200");
    return api.get<Paginated<StockBalance>>(`/stock/balances/?${qs}`).then((p) => p.results);
  },
};
