import { api } from "../../lib/apiClient";
import type { Paginated } from "../../types";
import type { Product } from "../wastage/api";

export interface MenuItem {
  id: string;
  name: string;
  pos_code: string;
  category?: string | null;
  created_at: string;
}

export interface RecipeVersionLine {
  product: string;
  product_name?: string;
  qty_per_serving: string;
}

export interface RecipeVersion {
  id: string;
  version_no: number;
  status: string;
  selling_price?: string | null;
  effective_from?: string | null;
  lines?: RecipeVersionLine[];
}

export interface CreateMenuItemBody {
  name: string;
  pos_code: string;
  category?: string;
}

export interface CreateRecipeVersionBody {
  lines: { product: string; qty_per_serving: number }[];
  selling_price?: number;
}

/** Menu items and versioned recipe workflow API surface. */
export const menuApi = {
  listItems: () =>
    api.get<Paginated<MenuItem>>("/menu-items/?page_size=200").then((p) => p.results),
  createItem: (body: CreateMenuItemBody) => api.post<MenuItem>("/menu-items/", body),
  versions: (itemId: string) =>
    api
      .get<Paginated<RecipeVersion>>(`/menu-items/${itemId}/recipe-versions/`)
      .then((p) => p.results),
  createVersion: (itemId: string, body: CreateRecipeVersionBody) =>
    api.post<RecipeVersion>(`/menu-items/${itemId}/recipe-versions/`, body),
  submitReview: (versionId: string) =>
    api.post<RecipeVersion>(`/recipe-versions/${versionId}/submit-review/`),
  publish: (versionId: string, effectiveFrom: string) =>
    api.post<RecipeVersion>(`/recipe-versions/${versionId}/publish/`, { effective_from: effectiveFrom }),
  products: () =>
    api.get<Paginated<Product>>("/products/?page_size=500").then((p) => p.results),
};
