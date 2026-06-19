/**
 * Offline-tolerant action queue for the waiter view.
 *
 * Tapping Served/Return enqueues an action with a stable idempotency key and
 * optimistically hides the order. A flusher drains the queue whenever the
 * device is online; the backend's idempotency guard makes replays safe, so a
 * brief outage never loses or double-applies a tap.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

import { randomUuid } from "../../../lib/id";

export type PendingAction =
  | { id: string; kind: "served"; orderId: string }
  | { id: string; kind: "return"; orderId: string; reasonCode: string };

interface QueueState {
  pending: PendingAction[];
  enqueue: (action: PendingAction) => void;
  remove: (id: string) => void;
}

export const useActionQueue = create<QueueState>()(
  persist(
    (set) => ({
      pending: [],
      enqueue: (action) => set((state) => ({ pending: [...state.pending, action] })),
      remove: (id) => set((state) => ({ pending: state.pending.filter((a) => a.id !== id) })),
    }),
    { name: "ff-waiter-queue" },
  ),
);

/** Crypto-strong idempotency key for an enqueued action. */
export function newActionId(): string {
  return randomUuid();
}
