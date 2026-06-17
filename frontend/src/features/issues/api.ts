import { api } from "../../lib/apiClient";
import type { Paginated, ReasonCode } from "../../types";
import type { Product } from "../wastage/api";

export interface MovementLine {
  product: string;
  qty: number;
}

export interface IssueLine {
  id: string;
  product: string;
  product_name?: string;
  qty: string;
}

export interface IssueDoc {
  id: string;
  source: string;
  source_name?: string;
  destination: string;
  destination_name?: string;
  status: string;
  off_schedule_reason?: string | null;
  lines?: IssueLine[];
  created_at: string;
}

export interface CreateIssueBody {
  source: string;
  destination: string;
  lines: MovementLine[];
  off_schedule_reason?: string;
}

export interface CreateTransferBody {
  source: string;
  destination: string;
  lines: MovementLine[];
}

/** Issues and inter-location transfers API surface. */
export const issuesApi = {
  listIssues: () =>
    api.get<Paginated<IssueDoc>>("/issues/?page_size=100").then((p) => p.results),
  createIssue: (body: CreateIssueBody) => api.post<IssueDoc>("/issues/", body),
  postIssue: (id: string, idempotencyKey: string) =>
    api.post<IssueDoc>(`/issues/${id}/post/`, {}, idempotencyKey),
  listTransfers: () =>
    api.get<Paginated<IssueDoc>>("/transfers/?page_size=100").then((p) => p.results),
  createTransfer: (body: CreateTransferBody) => api.post<IssueDoc>("/transfers/", body),
  postTransfer: (id: string, idempotencyKey: string) =>
    api.post<IssueDoc>(`/transfers/${id}/post/`, {}, idempotencyKey),
  products: () =>
    api.get<Paginated<Product>>("/products/?page_size=500").then((p) => p.results),
  reasonCodes: (category: string) =>
    api
      .get<Paginated<ReasonCode>>(`/reason-codes/?category=${category}`)
      .then((p) => p.results),
};
