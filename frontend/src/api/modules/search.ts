import type { SearchResponse } from "../../types";

import type { ApiTransport } from "../transport";

export function createSearchApi(transport: ApiTransport) {
  return {
    globalSearch: (query: string) => {
      const params = new URLSearchParams({ q: query });
      return transport.request<SearchResponse>(`/search?${params.toString()}`);
    },
  };
}
