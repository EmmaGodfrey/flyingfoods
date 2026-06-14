import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "../../../lib/apiClient";
import type { Order, Paginated } from "../../../types";
import { kitchenApi } from "../api";

const KEY = ["kitchen", "orders"];

/** Live list of active kitchen orders. Kept fresh by the socket + a slow poll. */
export function useKitchenOrders() {
  return useQuery({
    queryKey: KEY,
    queryFn: kitchenApi.listActive,
    staleTime: 0,
    refetchInterval: 20_000,
    select: (page: Paginated<Order>) => page.results,
  });
}

/** Start / ready transitions with optimistic UI and error surfacing. */
export function useOrderTransition() {
  const qc = useQueryClient();

  const start = useMutation({
    mutationFn: (id: string) => kitchenApi.start(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: KEY }),
    onError: (error) => toast.error(error instanceof ApiError ? error.message : "Could not start order"),
  });

  const ready = useMutation({
    mutationFn: (id: string) => kitchenApi.ready(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: KEY }),
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Could not mark ready"),
  });

  return { start, ready };
}
