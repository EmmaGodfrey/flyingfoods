/** Shared types mirroring the Django API contracts. */

export type Role =
  | "CHEF"
  | "WAITER"
  | "STOREKEEPER"
  | "RECEIVING_OFFICER"
  | "UNIT_ISSUER"
  | "RESTAURANT_ISSUER"
  | "MANAGER"
  | "ADMIN";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type OrderStatus =
  | "INGESTED"
  | "IN_PREPARATION"
  | "READY"
  | "SERVED"
  | "RETURNED";

export interface OrderItem {
  id: string;
  pos_code: string;
  menu_item_name: string | null;
  qty: string;
  modifiers: unknown[];
  price: string | null;
}

export interface Order {
  id: string;
  sale_event: string;
  table_ref: string;
  status: OrderStatus;
  flagged_insufficient_stock: boolean;
  items: OrderItem[];
  created_at: string;
  seconds_since_created: number;
}

export interface ReasonCode {
  id: string;
  category: string;
  label: string;
  is_active: boolean;
}
