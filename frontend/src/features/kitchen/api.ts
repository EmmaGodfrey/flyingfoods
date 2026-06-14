import { api } from "../../lib/apiClient";
import type { Order, Paginated } from "../../types";

/** Kitchen Display API surface. */
export const kitchenApi = {
  listActive: () => api.get<Paginated<Order>>("/kitchen/orders/"),
  start: (id: string) => api.post<Order>(`/kitchen/orders/${id}/start/`),
  ready: (id: string) => api.post<Order>(`/kitchen/orders/${id}/ready/`),
  extraUsage: (id: string, payload: { product: string; qty: string; reason_code: string }) =>
    api.post(`/kitchen/orders/${id}/extra-usage/`, payload),
};
