import { useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, LogIn, Package, Receipt, Search, ShoppingCart, Truck } from "lucide-react";
import { toast } from "sonner";
import { useLocation, useNavigate } from "react-router-dom";

import { ApiClient } from "./api/client";
import { ProductModal } from "./components/ProductModal";
import {
  DashboardPage,
  MovementsPage,
  PosPage,
  ProcurementPage,
  ProductsPage,
  ReportsPage,
  SettingsPage,
} from "./pages/sections";
import type {
  Category,
  DailySalesSummary,
  GoodsReceivedNote,
  Product,
  ProductFormInput,
  ProcurementOrdersReportResponse,
  ProcurementSpendResponse,
  PurchaseOrder,
  SalePaymentIntentResult,
  SalePaymentReconcileJobStatusResult,
  SalePaymentReconcileResult,
  SaleReceipt,
  SearchResponse,
  StockMovement,
  StockSummary,
  Supplier,
  TokenPair,
  Unit,
} from "./types";

type TabKey = "dashboard" | "products" | "movements" | "pos" | "procurement" | "reports" | "settings";

type BasketItem = {
  product: Product;
  quantity: number;
};

type SplitTenderDraft = {
  payment_method: "cash" | "card" | "mobile";
  amount: string;
};

type LiveDashboardEvent = {
  id: string;
  type: string;
  message: string;
  occurredAt: string;
};

type AppProps = {
  initialAccessToken?: string | null;
  initialRefreshToken?: string | null;
  onTokensChange?: (tokens: TokenPair) => void;
  onSignOut?: () => void;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const TAB_PATHS: Record<TabKey, string> = {
  dashboard: "/dashboard",
  products: "/products",
  movements: "/movements",
  pos: "/pos",
  procurement: "/procurement",
  reports: "/reports",
  settings: "/settings",
};

function tabFromPath(pathname: string): TabKey {
  const segment = pathname.split("/").filter(Boolean)[0];
  if (
    segment === "dashboard" ||
    segment === "products" ||
    segment === "movements" ||
    segment === "pos" ||
    segment === "procurement" ||
    segment === "reports" ||
    segment === "settings"
  ) {
    return segment;
  }
  return "dashboard";
}

function toNumber(value: string) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toOptionalInt(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const n = Number(trimmed);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

function wait(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function stockBadge(product: Product, stockMap: Map<number, number>) {
  const stock = stockMap.get(product.id) ?? 0;
  const reorder = toNumber(product.reorder_level);
  if (stock <= 0) {
    return { label: "Critical", className: "status-pill danger" };
  }
  if (stock < reorder) {
    return { label: "Low", className: "status-pill warning" };
  }
  return { label: "OK", className: "status-pill success" };
}

export default function App({ initialAccessToken = null, initialRefreshToken = null, onTokensChange, onSignOut }: AppProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const [accessToken, setAccessToken] = useState<string | null>(initialAccessToken);
  const [refreshToken, setRefreshToken] = useState<string | null>(initialRefreshToken);
  const [email, setEmail] = useState("manager@example.com");
  const [password, setPassword] = useState("password");
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);

  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [productTotal, setProductTotal] = useState(0);
  const [productOffset, setProductOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [stock, setStock] = useState<StockSummary[]>([]);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [movementTotal, setMovementTotal] = useState(0);
  const [movementType, setMovementType] = useState("all");
  const [occurredAfter, setOccurredAfter] = useState("");
  const [occurredBefore, setOccurredBefore] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);

  const [basket, setBasket] = useState<BasketItem[]>([]);
  const [paymentMethod, setPaymentMethod] = useState<"cash" | "card" | "mobile" | "split">("cash");
  const [taxAmount, setTaxAmount] = useState("0.00");
  const [discountAmount, setDiscountAmount] = useState("0.00");
  const [splitTenderOne, setSplitTenderOne] = useState<SplitTenderDraft>({ payment_method: "cash", amount: "0.00" });
  const [splitTenderTwo, setSplitTenderTwo] = useState<SplitTenderDraft>({ payment_method: "card", amount: "0.00" });
  const [checkoutBusy, setCheckoutBusy] = useState(false);

  const [latestReceipt, setLatestReceipt] = useState<SaleReceipt | null>(null);
  const [latestSaleStatus, setLatestSaleStatus] = useState<"completed" | "voided" | "refunded">("completed");
  const [paymentIntent, setPaymentIntent] = useState<SalePaymentIntentResult | null>(null);
  const [paymentReconcile, setPaymentReconcile] = useState<SalePaymentReconcileResult | null>(null);
  const [paymentJobStatus, setPaymentJobStatus] = useState<SalePaymentReconcileJobStatusResult | null>(null);
  const [paymentOpsBusy, setPaymentOpsBusy] = useState(false);
  const [saleActionBusy, setSaleActionBusy] = useState(false);

  const [liveConnected, setLiveConnected] = useState(false);
  const [liveEvents, setLiveEvents] = useState<LiveDashboardEvent[]>([]);
  const [liveAnomalyAlert, setLiveAnomalyAlert] = useState<string | null>(null);

  const [globalSearchQuery, setGlobalSearchQuery] = useState("");
  const [globalSearchResult, setGlobalSearchResult] = useState<SearchResponse | null>(null);
  const [globalSearchBusy, setGlobalSearchBusy] = useState(false);

  const [dailySummary, setDailySummary] = useState<DailySalesSummary | null>(null);
  const [summaryBusy, setSummaryBusy] = useState(false);

  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [purchaseOrderTotal, setPurchaseOrderTotal] = useState(0);
  const [procurementBusy, setProcurementBusy] = useState(false);

  const [poSupplierId, setPoSupplierId] = useState("1");
  const [poNotes, setPoNotes] = useState("");
  const [poProductId, setPoProductId] = useState("");
  const [poQuantity, setPoQuantity] = useState("1.00");
  const [poUnitPrice, setPoUnitPrice] = useState("1.00");

  const [grnPoId, setGrnPoId] = useState("");
  const [grnLineId, setGrnLineId] = useState("");
  const [grnQty, setGrnQty] = useState("1.00");
  const [grnReference, setGrnReference] = useState("");
  const [latestGrn, setLatestGrn] = useState<GoodsReceivedNote | null>(null);

  const [supplierSearch, setSupplierSearch] = useState("");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [supplierTotal, setSupplierTotal] = useState(0);
  const [editingSupplierId, setEditingSupplierId] = useState<number | null>(null);
  const [supplierName, setSupplierName] = useState("");
  const [supplierContact, setSupplierContact] = useState("");
  const [supplierPhone, setSupplierPhone] = useState("");
  const [supplierEmail, setSupplierEmail] = useState("");

  const [ordersReport, setOrdersReport] = useState<ProcurementOrdersReportResponse | null>(null);
  const [spendReport, setSpendReport] = useState<ProcurementSpendResponse | null>(null);

  useEffect(() => {
    if (!notice) {
      return;
    }
    toast.success(notice);
    const timer = window.setTimeout(() => setNotice(""), 2500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const activeTab = tabFromPath(location.pathname);

  const client = useMemo(
    () =>
      new ApiClient({
        baseUrl: API_BASE_URL,
        getAccessToken: () => accessToken,
        getRefreshToken: () => refreshToken,
        onTokens: (tokens: TokenPair) => {
          setAccessToken(tokens.access_token);
          setRefreshToken(tokens.refresh_token);
          onTokensChange?.(tokens);
        },
        onUnauthorized: () => {
          setAccessToken(null);
          setRefreshToken(null);
          onSignOut?.();
          navigate("/login");
        },
        onError: (message) => {
          toast.error(message);
        },
      }),
    [accessToken, navigate, onSignOut, onTokensChange, refreshToken],
  );

  const stockMap = useMemo(() => {
    const map = new Map<number, number>();
    for (const item of stock) {
      map.set(item.product_id, toNumber(item.computed_stock));
    }
    return map;
  }, [stock]);

  const categoryNameById = useMemo(() => {
    const map = new Map<number, string>();
    for (const category of categories) {
      map.set(category.id, category.name);
    }
    return map;
  }, [categories]);

  const unitLabelById = useMemo(() => {
    const map = new Map<number, string>();
    for (const unit of units) {
      map.set(unit.id, `${unit.name} (${unit.symbol})`);
    }
    return map;
  }, [units]);

  const productNameById = useMemo(() => {
    const map = new Map<number, string>();
    for (const product of products) {
      map.set(product.id, product.name);
    }
    return map;
  }, [products]);

  const splitTenderTotal = useMemo(() => toNumber(splitTenderOne.amount) + toNumber(splitTenderTwo.amount), [splitTenderOne.amount, splitTenderTwo.amount]);

  const checkoutTotal = useMemo(() => {
    const subtotal = basket.reduce((sum, item) => sum + toNumber(item.product.selling_price) * item.quantity, 0);
    return subtotal + toNumber(taxAmount) - toNumber(discountAmount);
  }, [basket, taxAmount, discountAmount]);

  const prevProductOffset = Math.max(0, productOffset - 20);
  const nextProductOffset = productOffset + 20;

  useEffect(() => {
    setAccessToken(initialAccessToken);
  }, [initialAccessToken]);

  useEffect(() => {
    setRefreshToken(initialRefreshToken);
  }, [initialRefreshToken]);

  const loadProductsAndStock = async (offset: number) => {
    setBusy(true);
    setError("");
    try {
      const [productResponse, stockResponse] = await Promise.all([
        client.listProducts({ limit: 20, offset, search }),
        client.listStockSummary(),
      ]);
      setProducts(productResponse.items);
      setProductTotal(productResponse.total);
      setProductOffset(productResponse.offset);
      setStock(stockResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load products");
    } finally {
      setBusy(false);
    }
  };

  const syncProductsQuietly = async (offset: number) => {
    try {
      const productResponse = await client.listProducts({ limit: 20, offset, search });
      setProducts(productResponse.items);
      setProductTotal(productResponse.total);
      setProductOffset(productResponse.offset);
    } catch {
      // Ignore background refresh failures; the visible state is already updated.
    }
  };

  const syncMovementsQuietly = async (offset: number) => {
    try {
      const response = await client.listMovements({
        limit: 20,
        offset,
        movementType: movementType === "all" ? undefined : movementType,
        occurredAfter: occurredAfter ? new Date(occurredAfter).toISOString() : undefined,
        occurredBefore: occurredBefore ? new Date(occurredBefore).toISOString() : undefined,
      });
      setMovements(response.items);
      setMovementTotal(response.total);
    } catch {
      // Ignore background refresh failures; the visible state is already updated.
    }
  };

  const syncDailySummaryQuietly = async () => {
    try {
      const summary = await client.getDailySalesSummary();
      setDailySummary(summary);
      setLiveConnected(true);
      setLiveAnomalyAlert(null);
    } catch {
      // Ignore background refresh failures; the visible state is already updated.
    }
  };

  const loadProductsPageOnly = async (offset: number) => {
    setBusy(true);
    setError("");
    try {
      const productResponse = await client.listProducts({ limit: 20, offset, search });
      setProducts(productResponse.items);
      setProductTotal(productResponse.total);
      setProductOffset(productResponse.offset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load products");
    } finally {
      setBusy(false);
    }
  };

  const refreshStockSummaryBackground = async () => {
    try {
      const stockResponse = await client.listStockSummary();
      setStock(stockResponse);
    } catch {
      // Avoid surfacing non-critical refresh errors during save flow.
    }
  };

  const loadProductLookups = async () => {
    setError("");
    try {
      const [categoryRows, unitRows] = await Promise.all([
        client.listCategories({ activeOnly: true }),
        client.listUnits({ activeOnly: true }),
      ]);
      setCategories(categoryRows);
      setUnits(unitRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load product lookups");
    }
  };

  const loadMovements = async (offset: number) => {
    setBusy(true);
    setError("");
    try {
      const response = await client.listMovements({
        limit: 20,
        offset,
        movementType: movementType === "all" ? undefined : movementType,
        occurredAfter: occurredAfter ? new Date(occurredAfter).toISOString() : undefined,
        occurredBefore: occurredBefore ? new Date(occurredBefore).toISOString() : undefined,
      });
      setMovements(response.items);
      setMovementTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load movements");
    } finally {
      setBusy(false);
    }
  };

  const loadDailySummary = async () => {
    setSummaryBusy(true);
    try {
      const summary = await client.getDailySalesSummary();
      setDailySummary(summary);
      setLiveConnected(true);
      setLiveAnomalyAlert(null);
    } catch (err) {
      setLiveConnected(false);
      setLiveAnomalyAlert(err instanceof Error ? err.message : "Live summary unavailable");
    } finally {
      setSummaryBusy(false);
    }
  };

  const loadProcurement = async () => {
    setProcurementBusy(true);
    setError("");
    try {
      const [supplierResponse, poResponse, orders, spend] = await Promise.all([
        client.listSuppliers({ limit: 50, offset: 0, search: supplierSearch || undefined, isActive: true }),
        client.listPurchaseOrders({ limit: 50, offset: 0 }),
        client.getProcurementOrdersReport({}),
        client.getProcurementSpendReport(),
      ]);
      setSuppliers(supplierResponse.items);
      setSupplierTotal(supplierResponse.total);
      setPurchaseOrders(poResponse.items);
      setPurchaseOrderTotal(poResponse.total);
      setOrdersReport(orders);
      setSpendReport(spend);
      if (supplierResponse.items.length > 0 && !poSupplierId) {
        setPoSupplierId(String(supplierResponse.items[0].supplier_id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load procurement");
    } finally {
      setProcurementBusy(false);
    }
  };

  const receiveStock = async (productId: number, qty: string, referenceId: string) => {
    await client.createMovement({ product_id: productId, qty, movement_type: "receive", reference_id: referenceId || undefined });
    void syncProductsQuietly(productOffset);
    void syncMovementsQuietly(0);
    setNotice("Stock movement recorded.");
  };

  const saveProduct = async (input: ProductFormInput, productId?: number) => {
    if (productId) {
      const updated = await client.updateProduct(productId, input);
      // Instantly swap the product in the list without a round-trip reload.
      setProducts((prev) => prev.map((p) => (p.id === productId ? updated : p)));
      setNotice("Product updated.");
    } else {
      const optimisticId = -Date.now();
      const optimisticProduct: Product = {
        id: optimisticId,
        branch_id: 1,
        name: input.name.trim() || "(new product)",
        unit_id: Math.max(0, Math.trunc(toNumber(input.unit_id))),
        category_id: toOptionalInt(input.category_id),
        supplier_id: toOptionalInt(input.supplier_id),
        sku: input.sku.trim() || null,
        barcode: input.barcode.trim() || null,
        reorder_level: input.reorder_level,
        cost_price: input.cost_price,
        selling_price: input.selling_price,
        is_active: true,
      };

      // Show the new row immediately, then reconcile with the server response.
      setProducts((prev) => [optimisticProduct, ...prev].slice(0, 20));
      setProductTotal((t) => t + 1);
      try {
        const created = await client.createProduct(input);
        setProducts((prev) => [created, ...prev.filter((p) => p.id !== optimisticId && p.id !== created.id)].slice(0, 20));
        setNotice("Product created.");
      } catch (error) {
        // Revert optimistic row if save fails.
        setProducts((prev) => prev.filter((p) => p.id !== optimisticId));
        setProductTotal((t) => Math.max(0, t - 1));
        throw error;
      }
    }
    // Refresh stock quietly; the product row is already updated optimistically.
    void refreshStockSummaryBackground();
  };

  const addToBasket = (product: Product) => {
    setBasket((current) => {
      const existing = current.find((item) => item.product.id === product.id);
      if (existing) {
        return current.map((item) => (item.product.id === product.id ? { ...item, quantity: item.quantity + 1 } : item));
      }
      return [...current, { product, quantity: 1 }];
    });
  };

  const setBasketQuantity = (productId: number, quantity: number) => {
    setBasket((current) =>
      current
        .map((item) => (item.product.id === productId ? { ...item, quantity: Math.max(0, quantity) } : item))
        .filter((item) => item.quantity > 0),
    );
  };

  const checkoutSale = async () => {
    if (basket.length === 0) {
      return;
    }
    setCheckoutBusy(true);
    setError("");
    try {
      const splitTenders =
        paymentMethod === "split"
          ? [
              { payment_method: splitTenderOne.payment_method, amount: splitTenderOne.amount },
              { payment_method: splitTenderTwo.payment_method, amount: splitTenderTwo.amount },
            ]
          : undefined;

      const receipt = await client.createSale({
        payment_method: paymentMethod,
        tax_amount: taxAmount,
        discount_amount: discountAmount,
        split_tenders: splitTenders,
        items: basket.map((item) => ({ product_id: item.product.id, quantity: String(item.quantity) })),
      });

      setLatestReceipt(receipt);
      setLatestSaleStatus("completed");
      setPaymentIntent(null);
      setPaymentReconcile(null);
      setPaymentJobStatus(null);
      setBasket([]);
      setLiveEvents((current) => [
        {
          id: `${Date.now()}`,
          type: "sale_completed",
          message: `Sale #${receipt.sale_id} completed for $${receipt.total}`,
          occurredAt: new Date().toISOString(),
        },
        ...current,
      ].slice(0, 20));
      void syncProductsQuietly(productOffset);
      void syncDailySummaryQuietly();
      setNotice("Sale completed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setCheckoutBusy(false);
    }
  };

  const handleSaleAction = async (action: "void" | "refund") => {
    if (!latestReceipt) {
      return;
    }
    setSaleActionBusy(true);
    try {
      if (action === "void") {
        await client.voidSale(latestReceipt.sale_id, "POS action");
        setLatestSaleStatus("voided");
        setNotice("Sale voided.");
      } else {
        await client.refundSale(latestReceipt.sale_id, "POS action");
        setLatestSaleStatus("refunded");
        setNotice("Sale refunded.");
      }
      void syncProductsQuietly(productOffset);
      void syncDailySummaryQuietly();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sale action failed");
    } finally {
      setSaleActionBusy(false);
    }
  };

  const authorizePaymentTenders = async () => {
    if (!latestReceipt) {
      return;
    }
    setPaymentOpsBusy(true);
    try {
      const intent = await client.createSalePaymentIntent(latestReceipt.sale_id, "simulated");
      setPaymentIntent(intent);
      setNotice("Payment authorization completed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment authorization failed");
    } finally {
      setPaymentOpsBusy(false);
    }
  };

  const reconcilePaymentTenders = async () => {
    if (!latestReceipt) {
      return;
    }
    const reference = paymentIntent?.authorized_tenders?.[0]?.provider_reference;
    if (!reference) {
      setError("Authorize payment first to create provider references.");
      return;
    }

    setPaymentOpsBusy(true);
    try {
      const enqueue = await client.enqueueSalePaymentReconcile(latestReceipt.sale_id, reference, "simulated");
      setPaymentJobStatus({
        job_id: enqueue.job_id,
        sale_id: enqueue.sale_id,
        branch_id: enqueue.branch_id,
        provider: enqueue.provider,
        provider_reference: enqueue.provider_reference,
        status: enqueue.status,
        queued_at: enqueue.queued_at,
        started_at: null,
        completed_at: null,
        result: null,
        error: null,
      });

      for (let i = 0; i < 10; i += 1) {
        await wait(800);
        const status = await client.getSalePaymentReconcileJobStatus(latestReceipt.sale_id, enqueue.job_id);
        setPaymentJobStatus(status);
        if (status.status === "succeeded" && status.result) {
          setPaymentReconcile(status.result);
          setNotice("Payment reconciliation succeeded.");
          break;
        }
        if (status.status === "failed") {
          setError(status.error || "Payment reconciliation failed");
          break;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reconciliation failed");
    } finally {
      setPaymentOpsBusy(false);
    }
  };

  const saveSupplier = async () => {
    if (!supplierName.trim()) {
      setError("Supplier name is required");
      return;
    }
    setProcurementBusy(true);
    try {
      if (editingSupplierId) {
        const updated = await client.updateSupplier(editingSupplierId, {
          name: supplierName,
          contact_name: supplierContact || undefined,
          phone: supplierPhone || undefined,
          email: supplierEmail || undefined,
        });
        setSuppliers((current) => current.map((supplier) => (supplier.supplier_id === editingSupplierId ? updated : supplier)));
        setNotice("Supplier updated.");
      } else {
        const created = await client.createSupplier({
          name: supplierName,
          contact_name: supplierContact || undefined,
          phone: supplierPhone || undefined,
          email: supplierEmail || undefined,
        });
        setSuppliers((current) => [created, ...current]);
        setSupplierTotal((current) => current + 1);
        setNotice("Supplier created.");
      }
      setEditingSupplierId(null);
      setSupplierName("");
      setSupplierContact("");
      setSupplierPhone("");
      setSupplierEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save supplier");
    } finally {
      setProcurementBusy(false);
    }
  };

  const editSupplier = (supplier: Supplier) => {
    setEditingSupplierId(supplier.supplier_id);
    setSupplierName(supplier.name);
    setSupplierContact(supplier.contact_name || "");
    setSupplierPhone(supplier.phone || "");
    setSupplierEmail(supplier.email || "");
  };

  const deleteSupplierById = async (supplierId: number) => {
    setProcurementBusy(true);
    try {
      await client.deleteSupplier(supplierId);
      setSuppliers((current) => current.filter((supplier) => supplier.supplier_id !== supplierId));
      setSupplierTotal((current) => Math.max(0, current - 1));
      setNotice("Supplier deleted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete supplier");
    } finally {
      setProcurementBusy(false);
    }
  };

  const createPurchaseOrder = async () => {
    const supplierId = Number(poSupplierId);
    const productId = Number(poProductId);
    if (!Number.isFinite(supplierId) || !Number.isFinite(productId)) {
      setError("Supplier ID and Product ID are required.");
      return;
    }
    setProcurementBusy(true);
    try {
      const product = products.find((item) => item.id === productId);
      const supplier = suppliers.find((item) => item.supplier_id === supplierId);
      const created = await client.createPurchaseOrder({
        supplier_id: supplierId,
        notes: poNotes || undefined,
        line_items: [{ product_id: productId, quantity: poQuantity, unit_price: poUnitPrice }],
      });
      setPurchaseOrders((current) => [created, ...current]);
      setPurchaseOrderTotal((current) => current + 1);
      setNotice("Purchase order created.");
      void Promise.resolve().then(() => {
        if (product && supplier) {
          setPoSupplierId(String(supplier.supplier_id));
          setPoProductId(String(product.id));
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create purchase order");
    } finally {
      setProcurementBusy(false);
    }
  };

  const submitPurchaseOrderById = async (purchaseOrderId: number) => {
    setProcurementBusy(true);
    try {
      await client.submitPurchaseOrder(purchaseOrderId);
      const now = new Date().toISOString();
      setPurchaseOrders((current) =>
        current.map((order) =>
          order.purchase_order_id === purchaseOrderId
            ? { ...order, status: "submitted", submitted_at: now }
            : order,
        ),
      );
      setNotice("Purchase order submitted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit purchase order");
    } finally {
      setProcurementBusy(false);
    }
  };

  const approvePurchaseOrderById = async (purchaseOrderId: number) => {
    setProcurementBusy(true);
    try {
      await client.approvePurchaseOrder(purchaseOrderId);
      const now = new Date().toISOString();
      setPurchaseOrders((current) =>
        current.map((order) =>
          order.purchase_order_id === purchaseOrderId
            ? { ...order, status: "approved", approved_at: now }
            : order,
        ),
      );
      setNotice("Purchase order approved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve purchase order");
    } finally {
      setProcurementBusy(false);
    }
  };

  const createGrn = async () => {
    const purchaseOrderId = Number(grnPoId);
    const lineItemId = Number(grnLineId);
    if (!Number.isFinite(purchaseOrderId) || !Number.isFinite(lineItemId)) {
      setError("GRN purchase order and line item are required.");
      return;
    }
    setProcurementBusy(true);
    try {
      const grn = await client.createGoodsReceivedNote({
        purchase_order_id: purchaseOrderId,
        reference: grnReference || undefined,
        line_items: [{ purchase_order_line_item_id: lineItemId, quantity_received: grnQty }],
      });
      setLatestGrn(grn);
      setPurchaseOrders((current) =>
        current.map((order) =>
          order.purchase_order_id === purchaseOrderId
            ? {
                ...order,
                status: grn.status_after_receipt,
                received_at: grn.created_at,
                line_items: order.line_items.map((lineItem) =>
                  lineItem.line_item_id === lineItemId
                    ? { ...lineItem, received_quantity: grn.line_items[0]?.quantity_received ?? lineItem.received_quantity }
                    : lineItem,
                ),
              }
            : order,
        ),
      );
      setNotice("Goods received note recorded.");
      void syncProductsQuietly(productOffset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create GRN");
    } finally {
      setProcurementBusy(false);
    }
  };

  const runGlobalSearch = async () => {
    if (!globalSearchQuery.trim()) {
      setGlobalSearchResult(null);
      return;
    }
    setGlobalSearchBusy(true);
    try {
      const result = await client.globalSearch(globalSearchQuery.trim());
      setGlobalSearchResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setGlobalSearchBusy(false);
    }
  };

  useEffect(() => {
    setError("");
  }, [activeTab]);

  useEffect(() => {
    if (!accessToken) {
      return;
    }

    if (activeTab === "dashboard") {
      void loadProductsAndStock(0);
      void loadMovements(0);
      return;
    }

    if (activeTab === "products") {
      void loadProductLookups();
      void loadProductsAndStock(0);
      return;
    }

    if (activeTab === "movements") {
      void loadMovements(0);
      return;
    }

    if (activeTab === "procurement") {
      void loadProductLookups();
      void loadProcurement();
      return;
    }

    if (activeTab === "pos") {
      void loadProductsAndStock(0);
      void loadDailySummary();
    }
  }, [accessToken, activeTab]);

  useEffect(() => {
    if (activeTab !== "pos" || !accessToken) {
      return;
    }
    const id = window.setInterval(() => {
      void loadDailySummary();
    }, 15000);
    return () => window.clearInterval(id);
  }, [activeTab, accessToken]);

  const signIn = async () => {
    setAuthBusy(true);
    setAuthError("");
    try {
      const tokens = await client.login(email, password);
      setAccessToken(tokens.access_token);
      setRefreshToken(tokens.refresh_token);
      onTokensChange?.(tokens);
      navigate("/dashboard");
      setNotice("Signed in. Open POS to start checkout or browse inventory.");
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setAuthBusy(false);
    }
  };

  if (!accessToken) {
    return (
      <div className="app-shell login-shell">
        <section className="card login-card">
          <h2>ERP Sign in</h2>
          <p className="card-subtitle">Use seeded credentials to access inventory, POS, procurement, and reports.</p>
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          {authError && <div className="form-error">{authError}</div>}
          <button type="button" className="button-primary" onClick={signIn} disabled={authBusy}>
            <LogIn size={14} strokeWidth={1.8} /> {authBusy ? "Signing in..." : "Sign in"}
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>ERP Console</h1>
        <p className="card-subtitle">Week 8 architecture shell with modular routes.</p>
        <nav className="nav-menu">
          <button type="button" className={activeTab === "dashboard" ? "nav-item active" : "nav-item"} onClick={() => navigate(TAB_PATHS.dashboard)}>
            <BarChart3 size={16} strokeWidth={1.8} /> Dashboard
          </button>
          <button type="button" className={activeTab === "products" ? "nav-item active" : "nav-item"} onClick={() => navigate(TAB_PATHS.products)}>
            <Package size={16} strokeWidth={1.8} /> Products
          </button>
          <button type="button" className={activeTab === "movements" ? "nav-item active" : "nav-item"} onClick={() => navigate(TAB_PATHS.movements)}>
            <Activity size={16} strokeWidth={1.8} /> Movements
          </button>
          <button type="button" className={activeTab === "pos" ? "nav-item active" : "nav-item"} onClick={() => navigate(TAB_PATHS.pos)}>
            <ShoppingCart size={16} strokeWidth={1.8} /> POS
          </button>
          <button type="button" className={activeTab === "procurement" ? "nav-item active" : "nav-item"} onClick={() => navigate(TAB_PATHS.procurement)}>
            <Truck size={16} strokeWidth={1.8} /> Procurement
          </button>
          <button type="button" className={activeTab === "reports" ? "nav-item active" : "nav-item"} onClick={() => navigate(TAB_PATHS.reports)}>
            <Receipt size={16} strokeWidth={1.8} /> Reports
          </button>
          <button type="button" className={activeTab === "settings" ? "nav-item active" : "nav-item"} onClick={() => navigate(TAB_PATHS.settings)}>
            <Activity size={16} strokeWidth={1.8} /> Settings
          </button>
        </nav>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div className="search-wrap">
            <Search size={14} strokeWidth={1.8} />
            <input
              placeholder="Global search products, suppliers, invoices"
              value={globalSearchQuery}
              onChange={(event) => setGlobalSearchQuery(event.target.value)}
            />
          </div>
          <button type="button" className="button-secondary" onClick={runGlobalSearch} disabled={globalSearchBusy}>
            Search
          </button>
          <button
            className="button-secondary"
            type="button"
            onClick={() => {
              setAccessToken(null);
              setRefreshToken(null);
              onSignOut?.();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </header>

        {globalSearchResult && (
          <section className="card" style={{ marginTop: 12 }}>
            <h3 className="card-title">Search results ({globalSearchResult.total})</h3>
            <div className="row-gap">
              {[...globalSearchResult.products, ...globalSearchResult.suppliers, ...globalSearchResult.invoices].slice(0, 8).map((item) => (
                <span key={`${item.item_type}-${item.item_id}`} className="status-pill neutral">
                  {item.item_type}: {item.title}
                </span>
              ))}
            </div>
          </section>
        )}

        <main className="panel">
          {error && <div className="form-error">{error}</div>}

          {activeTab === "dashboard" && (
            <DashboardPage
              productTotal={productTotal}
              movementTotal={movementTotal}
              purchaseOrderTotal={purchaseOrderTotal}
              onLoadInventory={() => void loadProductsAndStock(0)}
              onLoadHistory={() => void loadMovements(0)}
              onLoadSummary={() => void loadDailySummary()}
              busy={busy}
              summaryBusy={summaryBusy}
              />
          )}

          {activeTab === "products" && (
            <ProductsPage
              search={search}
              setSearch={setSearch}
              loadProductsAndStock={loadProductsAndStock}
              setEditingProduct={setEditingProduct}
              setModalOpen={setModalOpen}
              products={products}
              stockMap={stockMap}
              categoryNameById={categoryNameById}
              unitLabelById={unitLabelById}
              stockBadge={stockBadge}
              productTotal={productTotal}
              productOffset={productOffset}
              busy={busy}
              prevProductOffset={prevProductOffset}
              nextProductOffset={nextProductOffset}
              receiveStock={receiveStock}
            />
          )}

          {activeTab === "movements" && (
            <MovementsPage
              movementType={movementType}
              setMovementType={setMovementType}
              occurredAfter={occurredAfter}
              setOccurredAfter={setOccurredAfter}
              occurredBefore={occurredBefore}
              setOccurredBefore={setOccurredBefore}
              loadMovements={loadMovements}
              movements={movements}
              movementTotal={movementTotal}
                productNameById={productNameById}
            />
          )}

          {activeTab === "procurement" && (
            <ProcurementPage
              supplierSearch={supplierSearch}
              setSupplierSearch={setSupplierSearch}
              loadProcurement={loadProcurement}
              procurementBusy={procurementBusy}
              supplierName={supplierName}
              setSupplierName={setSupplierName}
              supplierContact={supplierContact}
              setSupplierContact={setSupplierContact}
              supplierPhone={supplierPhone}
              setSupplierPhone={setSupplierPhone}
              supplierEmail={supplierEmail}
              setSupplierEmail={setSupplierEmail}
              saveSupplier={saveSupplier}
              editingSupplierId={editingSupplierId}
              setEditingSupplierId={setEditingSupplierId}
              suppliers={suppliers}
              products={products}
              deleteSupplierById={deleteSupplierById}
              editSupplier={editSupplier}
              supplierTotal={supplierTotal}
              poSupplierId={poSupplierId}
              setPoSupplierId={setPoSupplierId}
              poProductId={poProductId}
              setPoProductId={setPoProductId}
              poQuantity={poQuantity}
              setPoQuantity={setPoQuantity}
              poUnitPrice={poUnitPrice}
              setPoUnitPrice={setPoUnitPrice}
              poNotes={poNotes}
              setPoNotes={setPoNotes}
              createPurchaseOrder={createPurchaseOrder}
              grnPoId={grnPoId}
              setGrnPoId={setGrnPoId}
              grnLineId={grnLineId}
              setGrnLineId={setGrnLineId}
              grnQty={grnQty}
              setGrnQty={setGrnQty}
              grnReference={grnReference}
              setGrnReference={setGrnReference}
              createGrn={createGrn}
              latestGrn={latestGrn}
              purchaseOrders={purchaseOrders}
              submitPurchaseOrderById={submitPurchaseOrderById}
              approvePurchaseOrderById={approvePurchaseOrderById}
              purchaseOrderTotal={purchaseOrderTotal}
              ordersReport={ordersReport}
              spendReport={spendReport}
            />
          )}

          {activeTab === "reports" && <ReportsPage />}
          {activeTab === "settings" && <SettingsPage />}

          {activeTab === "pos" && (
            <PosPage
              liveConnected={liveConnected}
              loadProductsAndStock={loadProductsAndStock}
              loadDailySummary={loadDailySummary}
              summaryBusy={summaryBusy}
              products={products}
              stockMap={stockMap}
              toNumber={toNumber}
              addToBasket={addToBasket}
              basket={basket}
              setBasketQuantity={setBasketQuantity}
              taxAmount={taxAmount}
              setTaxAmount={setTaxAmount}
              discountAmount={discountAmount}
              setDiscountAmount={setDiscountAmount}
              paymentMethod={paymentMethod}
              setPaymentMethod={setPaymentMethod}
              splitTenderOne={splitTenderOne}
              setSplitTenderOne={setSplitTenderOne}
              splitTenderTwo={splitTenderTwo}
              setSplitTenderTwo={setSplitTenderTwo}
              splitTenderTotal={splitTenderTotal}
              checkoutTotal={checkoutTotal}
              checkoutSale={checkoutSale}
              checkoutBusy={checkoutBusy}
              latestReceipt={latestReceipt}
              latestSaleStatus={latestSaleStatus}
              authorizePaymentTenders={authorizePaymentTenders}
              paymentOpsBusy={paymentOpsBusy}
              reconcilePaymentTenders={reconcilePaymentTenders}
              handleSaleAction={handleSaleAction}
              saleActionBusy={saleActionBusy}
              paymentIntent={paymentIntent}
              paymentReconcile={paymentReconcile}
              paymentJobStatus={paymentJobStatus}
              liveAnomalyAlert={liveAnomalyAlert}
              dailySummary={dailySummary}
              liveEvents={liveEvents}
              productNameById={productNameById}
            />
          )}
        </main>
      </div>

      <ProductModal
        open={modalOpen}
        product={editingProduct}
        categories={categories}
        units={units}
        onClose={() => setModalOpen(false)}
        onSave={saveProduct}
      />
    </div>
  );
}
