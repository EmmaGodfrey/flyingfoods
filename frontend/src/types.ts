export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type Product = {
  id: number;
  branch_id: number;
  name: string;
  unit_id: number;
  category_id: number | null;
  supplier_id: number | null;
  sku: string | null;
  barcode: string | null;
  reorder_level: string;
  cost_price: string;
  selling_price: string;
  is_active: boolean;
};

export type ProductListResponse = {
  items: Product[];
  total: number;
  limit: number;
  offset: number;
};

export type StockSummary = {
  product_id: number;
  computed_stock: string;
};

export type StockMovement = {
  id: number;
  product_id: number;
  branch_id: number;
  qty: string;
  movement_type: "receive" | "sale" | "waste" | "adjustment";
  reference_id: string | null;
  created_by: number | null;
  created_at: string;
};

export type StockMovementListResponse = {
  items: StockMovement[];
  total: number;
  limit: number;
  offset: number;
};

export type ProductFormInput = {
  name: string;
  unit_id: string;
  category_id: string;
  supplier_id: string;
  sku: string;
  barcode: string;
  reorder_level: string;
  cost_price: string;
  selling_price: string;
};

export type Category = {
  id: number;
  branch_id: number;
  name: string;
  is_active: boolean;
};

export type Unit = {
  id: number;
  branch_id: number;
  name: string;
  symbol: string;
  is_active: boolean;
};

export type MovementCreateInput = {
  product_id: number;
  qty: string;
  movement_type: "receive" | "sale" | "waste" | "adjustment";
  reference_id?: string;
};

export type SaleCreateInput = {
  payment_method: "cash" | "card" | "mobile" | "split";
  tax_amount?: string;
  discount_amount?: string;
  split_tenders?: Array<{
    payment_method: "cash" | "card" | "mobile";
    amount: string;
  }>;
  items: Array<{
    product_id: number;
    quantity: string;
  }>;
};

export type SaleTender = {
  payment_method: "cash" | "card" | "mobile";
  amount: string;
};

export type SaleReceiptLineItem = {
  product_id: number;
  quantity: string;
  unit_price: string;
  line_total: string;
};

export type SaleReceipt = {
  sale_id: number;
  branch_id: number;
  cashier_user_id: number | null;
  payment_method: "cash" | "card" | "mobile" | "split";
  subtotal: string;
  tax_amount: string;
  discount_amount: string;
  total: string;
  payment_tenders: SaleTender[];
  created_at: string;
  line_items: SaleReceiptLineItem[];
};

export type DailySalesSummary = {
  business_date: string;
  branch_id: number;
  sales_count: number;
  gross_total: string;
  payment_method_totals: Record<string, string>;
};

export type SaleVoidResult = {
  sale_id: number;
  status: "voided";
  voided_at: string;
  voided_by_user_id: number | null;
  reason: string | null;
};

export type SaleRefundResult = {
  sale_id: number;
  status: "refunded";
  refunded_at: string;
  refunded_by_user_id: number | null;
  reason: string | null;
};

export type PaymentProvider = "simulated";

export type PaymentAuthorization = {
  tender_index: number;
  payment_method: "card" | "mobile";
  amount: string;
  provider: PaymentProvider;
  provider_reference: string;
  status: "authorized";
};

export type SalePaymentIntentResult = {
  sale_id: number;
  branch_id: number;
  provider: PaymentProvider;
  authorized_tenders: PaymentAuthorization[];
};

export type SalePaymentReconcileResult = {
  sale_id: number;
  branch_id: number;
  provider: PaymentProvider;
  provider_reference: string;
  status: "reconciled";
  reconciled_amount: string;
  reconciled_at: string;
};

export type ReconciliationJobStatus = "queued" | "running" | "succeeded" | "failed";

export type SalePaymentReconcileJobEnqueueResult = {
  job_id: string;
  sale_id: number;
  branch_id: number;
  provider: PaymentProvider;
  provider_reference: string;
  status: ReconciliationJobStatus;
  queued_at: string;
};

export type SalePaymentReconcileJobStatusResult = {
  job_id: string;
  sale_id: number;
  branch_id: number;
  provider: PaymentProvider;
  provider_reference: string;
  status: ReconciliationJobStatus;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  result: SalePaymentReconcileResult | null;
  error: string | null;
};

export type SearchResultItem = {
  item_type: "product" | "supplier" | "invoice";
  item_id: string;
  title: string;
  subtitle: string | null;
  route: string | null;
  highlights: string[];
};

export type SearchResponse = {
  query: string;
  branch_id: number;
  total: number;
  products: SearchResultItem[];
  suppliers: SearchResultItem[];
  invoices: SearchResultItem[];
};

export type PurchaseOrderLineItemCreateInput = {
  product_id: number;
  quantity: string;
  unit_price: string;
};

export type PurchaseOrderCreateInput = {
  supplier_id: number;
  notes?: string;
  line_items: PurchaseOrderLineItemCreateInput[];
};

export type PurchaseOrderLineItem = {
  line_item_id: number;
  product_id: number;
  product_name: string;
  quantity: string;
  unit_price: string;
  received_quantity: string;
};

export type PurchaseOrder = {
  purchase_order_id: number;
  branch_id: number;
  supplier_id: number;
  supplier_name: string;
  status: string;
  notes: string | null;
  created_by_user_id: number | null;
  submitted_by_user_id: number | null;
  approved_by_user_id: number | null;
  submitted_at: string | null;
  approved_at: string | null;
  received_at: string | null;
  closed_at: string | null;
  created_at: string;
  line_items: PurchaseOrderLineItem[];
};

export type PurchaseOrderListResponse = {
  items: PurchaseOrder[];
  total: number;
  limit: number;
  offset: number;
};

export type GoodsReceivedNoteCreateInput = {
  purchase_order_id: number;
  reference?: string;
  notes?: string;
  line_items: Array<{
    purchase_order_line_item_id: number;
    quantity_received: string;
  }>;
};

export type GoodsReceivedNote = {
  goods_received_note_id: number;
  purchase_order_id: number;
  branch_id: number;
  status_after_receipt: string;
  reference: string | null;
  notes: string | null;
  received_by_user_id: number | null;
  created_at: string;
  line_items: Array<{
    goods_received_note_line_item_id: number;
    purchase_order_line_item_id: number;
    product_id: number;
    product_name: string;
    quantity_received: string;
  }>;
};

export type ProcurementOrdersReportLine = {
  purchase_order_id: number;
  created_at: string;
  supplier_id: number;
  supplier_name: string;
  status: string;
  line_count: number;
  ordered_total: string;
  received_total: string;
};

export type ProcurementOrdersReportResponse = {
  branch_id: number;
  total: number;
  limit: number;
  offset: number;
  status: string | null;
  supplier_id: number | null;
  date_from: string | null;
  date_to: string | null;
  items: ProcurementOrdersReportLine[];
};

export type ProcurementSpendLine = {
  month: string;
  supplier_id: number | null;
  supplier_name: string;
  total_spend: string;
};

export type ProcurementSpendResponse = {
  branch_id: number;
  date_from: string | null;
  date_to: string | null;
  rows: ProcurementSpendLine[];
};

export type Supplier = {
  supplier_id: number;
  branch_id: number;
  name: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  is_active: boolean;
  created_at: string;
};

export type SupplierListResponse = {
  items: Supplier[];
  total: number;
  limit: number;
  offset: number;
};

export type SupplierCreateInput = {
  name: string;
  contact_name?: string;
  phone?: string;
  email?: string;
  is_active?: boolean;
};

export type SupplierUpdateInput = {
  name?: string;
  contact_name?: string;
  phone?: string;
  email?: string;
  is_active?: boolean;
};
