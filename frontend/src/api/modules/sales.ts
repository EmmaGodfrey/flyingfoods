import type {
  DailySalesSummary,
  SaleCreateInput,
  SalePaymentIntentResult,
  SalePaymentReconcileJobEnqueueResult,
  SalePaymentReconcileJobStatusResult,
  SalePaymentReconcileResult,
  SaleReceipt,
  SaleRefundResult,
  SaleVoidResult,
} from "../../types";

import type { ApiTransport } from "../transport";

export function createSalesApi(transport: ApiTransport) {
  return {
    createSale: (input: SaleCreateInput) =>
      transport.request<SaleReceipt>("/sales", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      }),

    getSaleReceipt: (saleId: number) => transport.request<SaleReceipt>(`/sales/${saleId}/receipt`),

    getDailySalesSummary: (businessDate?: string) => {
      const query = new URLSearchParams();
      if (businessDate) {
        query.set("business_date", businessDate);
      }
      const suffix = query.toString() ? `?${query.toString()}` : "";
      return transport.request<DailySalesSummary>(`/sales/summary/daily${suffix}`);
    },

    voidSale: (saleId: number, reason: string) =>
      transport.request<SaleVoidResult>(`/sales/${saleId}/void`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      }),

    refundSale: (saleId: number, reason: string) =>
      transport.request<SaleRefundResult>(`/sales/${saleId}/refund`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      }),

    createSalePaymentIntent: (saleId: number, provider: "simulated" = "simulated") =>
      transport.request<SalePaymentIntentResult>(`/sales/${saleId}/payments/intent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider }),
      }),

    reconcileSalePayment: (saleId: number, providerReference: string, provider: "simulated" = "simulated") =>
      transport.request<SalePaymentReconcileResult>(`/sales/${saleId}/payments/reconcile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, provider_reference: providerReference }),
      }),

    enqueueSalePaymentReconcile: (saleId: number, providerReference: string, provider: "simulated" = "simulated") =>
      transport.request<SalePaymentReconcileJobEnqueueResult>(`/sales/${saleId}/payments/reconcile/async`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, provider_reference: providerReference }),
      }),

    getSalePaymentReconcileJobStatus: (saleId: number, jobId: string) =>
      transport.request<SalePaymentReconcileJobStatusResult>(`/sales/${saleId}/payments/reconcile/jobs/${jobId}`),
  };
}
