import { QueryClient } from "@tanstack/react-query";

/** Shared React Query client. Live boards override staleTime to 0 per query. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});
