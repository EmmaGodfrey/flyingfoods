import type {
  Category,
  DailySalesSummary,
  GoodsReceivedNote,
  GoodsReceivedNoteCreateInput,
  MovementCreateInput,
  ProcurementOrdersReportResponse,
  ProcurementSpendResponse,
  Product,
  ProductFormInput,
  ProductListResponse,
  PurchaseOrder,
  PurchaseOrderCreateInput,
  PurchaseOrderListResponse,
  SaleCreateInput,
  SalePaymentIntentResult,
  SalePaymentReconcileJobEnqueueResult,
  SalePaymentReconcileJobStatusResult,
  SalePaymentReconcileResult,
  SaleReceipt,
  SaleRefundResult,
  SaleVoidResult,
  SearchResponse,
  StockMovement,
  StockMovementListResponse,
  StockSummary,
  Supplier,
  SupplierCreateInput,
  SupplierListResponse,
  SupplierUpdateInput,
  TokenPair,
  Unit,
} from "../types";
import { login as loginWithCredentials } from "./modules/auth";
import { createProcurementApi, createInventoryApi, createSalesApi, createSearchApi, createApiTransport } from "./index";

type ApiClientOptions = {
  baseUrl: string;
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  onTokens: (tokens: TokenPair) => void;
  onUnauthorized: () => void;
  onError?: (message: string) => void;
};

export class ApiClient {
  private readonly baseUrl: string;
  private readonly inventoryApi;
  private readonly salesApi;
  private readonly procurementApi;
  private readonly searchApi;

  constructor(options: ApiClientOptions) {
    this.baseUrl = options.baseUrl;
    const transport = createApiTransport(options);
    this.inventoryApi = createInventoryApi(transport);
    this.salesApi = createSalesApi(transport);
    this.procurementApi = createProcurementApi(transport);
    this.searchApi = createSearchApi(transport);
  }

  async login(email: string, password: string): Promise<TokenPair> {
    return loginWithCredentials({ baseUrl: this.baseUrl, email, password });
  }

  async listProducts(params: { limit: number; offset: number; search: string }): Promise<ProductListResponse> {
    return this.inventoryApi.listProducts(params);
  }

  async listCategories(params?: { activeOnly?: boolean }): Promise<Category[]> {
    return this.inventoryApi.listCategories(params);
  }

  async listUnits(params?: { activeOnly?: boolean }): Promise<Unit[]> {
    return this.inventoryApi.listUnits(params);
  }

  async createProduct(input: ProductFormInput): Promise<Product> {
    return this.inventoryApi.createProduct(input);
  }

  async updateProduct(productId: number, input: ProductFormInput): Promise<Product> {
    return this.inventoryApi.updateProduct(productId, input);
  }

  async listStockSummary(): Promise<StockSummary[]> {
    return this.inventoryApi.listStockSummary();
  }

  async listMovements(params: {
    limit: number;
    offset: number;
    movementType?: string;
    occurredAfter?: string;
    occurredBefore?: string;
  }): Promise<StockMovementListResponse> {
    return this.inventoryApi.listMovements(params);
  }

  async createMovement(input: MovementCreateInput): Promise<StockMovement> {
    return this.inventoryApi.createMovement(input);
  }

  async createSale(input: SaleCreateInput): Promise<SaleReceipt> {
    return this.salesApi.createSale(input);
  }

  async getSaleReceipt(saleId: number): Promise<SaleReceipt> {
    return this.salesApi.getSaleReceipt(saleId);
  }

  async getDailySalesSummary(businessDate?: string): Promise<DailySalesSummary> {
    return this.salesApi.getDailySalesSummary(businessDate);
  }

  async voidSale(saleId: number, reason: string): Promise<SaleVoidResult> {
    return this.salesApi.voidSale(saleId, reason);
  }

  async refundSale(saleId: number, reason: string): Promise<SaleRefundResult> {
    return this.salesApi.refundSale(saleId, reason);
  }

  async createSalePaymentIntent(saleId: number, provider: "simulated" = "simulated"): Promise<SalePaymentIntentResult> {
    return this.salesApi.createSalePaymentIntent(saleId, provider);
  }

  async reconcileSalePayment(
    saleId: number,
    providerReference: string,
    provider: "simulated" = "simulated",
  ): Promise<SalePaymentReconcileResult> {
    return this.salesApi.reconcileSalePayment(saleId, providerReference, provider);
  }

  async enqueueSalePaymentReconcile(
    saleId: number,
    providerReference: string,
    provider: "simulated" = "simulated",
  ): Promise<SalePaymentReconcileJobEnqueueResult> {
    return this.salesApi.enqueueSalePaymentReconcile(saleId, providerReference, provider);
  }

  async getSalePaymentReconcileJobStatus(saleId: number, jobId: string): Promise<SalePaymentReconcileJobStatusResult> {
    return this.salesApi.getSalePaymentReconcileJobStatus(saleId, jobId);
  }

  async globalSearch(query: string): Promise<SearchResponse> {
    return this.searchApi.globalSearch(query);
  }

  async createPurchaseOrder(input: PurchaseOrderCreateInput): Promise<PurchaseOrder> {
    return this.procurementApi.createPurchaseOrder(input);
  }

  async listPurchaseOrders(params: {
    limit?: number;
    offset?: number;
    status?: string;
    supplierId?: number;
  }): Promise<PurchaseOrderListResponse> {
    return this.procurementApi.listPurchaseOrders(params);
  }

  async submitPurchaseOrder(purchaseOrderId: number): Promise<PurchaseOrder> {
    return this.procurementApi.submitPurchaseOrder(purchaseOrderId);
  }

  async approvePurchaseOrder(purchaseOrderId: number): Promise<PurchaseOrder> {
    return this.procurementApi.approvePurchaseOrder(purchaseOrderId);
  }

  async createGoodsReceivedNote(input: GoodsReceivedNoteCreateInput): Promise<GoodsReceivedNote> {
    return this.procurementApi.createGoodsReceivedNote(input);
  }

  async getProcurementOrdersReport(params: { status?: string }): Promise<ProcurementOrdersReportResponse> {
    return this.procurementApi.getProcurementOrdersReport(params);
  }

  async getProcurementSpendReport(): Promise<ProcurementSpendResponse> {
    return this.procurementApi.getProcurementSpendReport();
  }

  async listSuppliers(params: { limit?: number; offset?: number; search?: string; isActive?: boolean }): Promise<SupplierListResponse> {
    return this.procurementApi.listSuppliers(params);
  }

  async createSupplier(input: SupplierCreateInput): Promise<Supplier> {
    return this.procurementApi.createSupplier(input);
  }

  async updateSupplier(supplierId: number, input: SupplierUpdateInput): Promise<Supplier> {
    return this.procurementApi.updateSupplier(supplierId, input);
  }

  async deleteSupplier(supplierId: number): Promise<void> {
    return this.procurementApi.deleteSupplier(supplierId);
  }
}
