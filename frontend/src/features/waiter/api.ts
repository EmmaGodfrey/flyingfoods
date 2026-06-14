import { api } from "../../lib/apiClient";
import type { Order, Paginated, ReasonCode } from "../../types";

/** Waiter service API surface. */
export const waiterApi = {
  listReady: () => api.get<Paginated<Order>>("/waiter/orders/"),
  served: (id: string, idempotencyKey: string) =>
    api.post<Order>(`/waiter/orders/${id}/served/`, {}, idempotencyKey),
  returnOrder: (id: string, reasonCode: string, idempotencyKey: string) =>
    api.post<Order>(`/waiter/orders/${id}/return/`, { reason_code: reasonCode }, idempotencyKey),
  returnReasons: () =>
    api.get<Paginated<ReasonCode>>("/reason-codes/?category=RETURN").then((page) => page.results),
};
