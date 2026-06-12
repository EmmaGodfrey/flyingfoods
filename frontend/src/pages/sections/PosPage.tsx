import { BarChart3, Package, Receipt } from "lucide-react";

import type {
  DailySalesSummary,
  Product,
  SalePaymentIntentResult,
  SalePaymentReconcileJobStatusResult,
  SalePaymentReconcileResult,
  SaleReceipt,
} from "../../types";

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

type PosPageProps = {
  liveConnected: boolean;
  loadProductsAndStock: (offset: number) => Promise<void>;
  loadDailySummary: () => Promise<void>;
  summaryBusy: boolean;
  products: Product[];
  stockMap: Map<number, number>;
  toNumber: (value: string) => number;
  addToBasket: (product: Product) => void;
  basket: Array<{ product: Product; quantity: number }>;
  setBasketQuantity: (productId: number, quantity: number) => void;
  taxAmount: string;
  setTaxAmount: (value: string) => void;
  discountAmount: string;
  setDiscountAmount: (value: string) => void;
  paymentMethod: "cash" | "card" | "mobile" | "split";
  setPaymentMethod: (value: "cash" | "card" | "mobile" | "split") => void;
  splitTenderOne: SplitTenderDraft;
  setSplitTenderOne: (updater: (current: SplitTenderDraft) => SplitTenderDraft) => void;
  splitTenderTwo: SplitTenderDraft;
  setSplitTenderTwo: (updater: (current: SplitTenderDraft) => SplitTenderDraft) => void;
  splitTenderTotal: number;
  checkoutTotal: number;
  checkoutSale: () => Promise<void>;
  checkoutBusy: boolean;
  latestReceipt: SaleReceipt | null;
  latestSaleStatus: "completed" | "voided" | "refunded";
  authorizePaymentTenders: () => Promise<void>;
  paymentOpsBusy: boolean;
  reconcilePaymentTenders: () => Promise<void>;
  handleSaleAction: (action: "void" | "refund") => Promise<void>;
  saleActionBusy: boolean;
  paymentIntent: SalePaymentIntentResult | null;
  paymentReconcile: SalePaymentReconcileResult | null;
  paymentJobStatus: SalePaymentReconcileJobStatusResult | null;
  liveAnomalyAlert: string | null;
  dailySummary: DailySalesSummary | null;
  liveEvents: LiveDashboardEvent[];
  productNameById: Map<number, string>;
};

export function PosPage(props: PosPageProps) {
  return (
    <>
      <div className="section-head">
        <h2>POS checkout</h2>
        <div className="row-gap">
          <span className={props.liveConnected ? "status-pill success" : "status-pill warning"}>
            Live {props.liveConnected ? "connected" : "disconnected"}
          </span>
          <button type="button" className="button-secondary" onClick={() => void props.loadProductsAndStock(0)}>
            <Package size={14} strokeWidth={1.8} /> Reload catalog
          </button>
          <button type="button" className="button-secondary" onClick={() => void props.loadDailySummary()} disabled={props.summaryBusy}>
            <BarChart3 size={14} strokeWidth={1.8} /> Refresh summary
          </button>
        </div>
      </div>

      <div className="pos-layout">
        <section className="card">
          <h3 className="card-title">Product grid</h3>
          <p className="card-subtitle">Click add to basket and adjust quantities before checkout.</p>
          <div className="pos-grid">
            {props.products.map((product) => {
              const currentStock = props.stockMap.get(product.id) ?? 0;
              return (
                <article key={product.id} className="pos-product-card">
                  <div className="pos-product-meta">
                    <h4>{product.name}</h4>
                    <p>Unit price: ${props.toNumber(product.selling_price).toFixed(2)}</p>
                    <p>Stock: {currentStock.toFixed(2)}</p>
                  </div>
                  <button type="button" className="button-primary" onClick={() => props.addToBasket(product)} disabled={currentStock <= 0}>
                    Add to basket
                  </button>
                </article>
              );
            })}
          </div>
        </section>

        <section className="card">
          <h3 className="card-title">Basket</h3>
          <p className="card-subtitle">Review quantities, select payment, and checkout.</p>

          {props.basket.length === 0 && <p className="card-subtitle">No items in basket.</p>}

          {props.basket.length > 0 && (
            <table className="data-table basket-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Qty</th>
                  <th>Unit</th>
                  <th>Line total</th>
                </tr>
              </thead>
              <tbody>
                {props.basket.map((item) => (
                  <tr key={item.product.id}>
                    <td>{item.product.name}</td>
                    <td>
                      <input
                        type="number"
                        min={0}
                        step={1}
                        value={item.quantity}
                        onChange={(event) => {
                          const next = Number(event.target.value);
                          props.setBasketQuantity(item.product.id, Number.isFinite(next) ? next : 0);
                        }}
                      />
                    </td>
                    <td>${props.toNumber(item.product.selling_price).toFixed(2)}</td>
                    <td>${(props.toNumber(item.product.selling_price) * item.quantity).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div className="pos-actions">
            <label>
              Tax amount
              <input value={props.taxAmount} onChange={(event) => props.setTaxAmount(event.target.value)} inputMode="decimal" />
            </label>
            <label>
              Discount amount
              <input value={props.discountAmount} onChange={(event) => props.setDiscountAmount(event.target.value)} inputMode="decimal" />
            </label>
            <label>
              Payment method
              <select value={props.paymentMethod} onChange={(event) => props.setPaymentMethod(event.target.value as "cash" | "card" | "mobile" | "split")}>
                <option value="cash">Cash</option>
                <option value="card">Card</option>
                <option value="mobile">Mobile</option>
                <option value="split">Split</option>
              </select>
            </label>
            {props.paymentMethod === "split" && (
              <div className="split-tender-grid">
                <label>
                  Tender 1 method
                  <select
                    value={props.splitTenderOne.payment_method}
                    onChange={(event) =>
                      props.setSplitTenderOne((current) => ({
                        ...current,
                        payment_method: event.target.value as SplitTenderDraft["payment_method"],
                      }))
                    }
                  >
                    <option value="cash">Cash</option>
                    <option value="card">Card</option>
                    <option value="mobile">Mobile</option>
                  </select>
                </label>
                <label>
                  Tender 1 amount
                  <input
                    value={props.splitTenderOne.amount}
                    onChange={(event) => props.setSplitTenderOne((current) => ({ ...current, amount: event.target.value }))}
                    inputMode="decimal"
                  />
                </label>
                <label>
                  Tender 2 method
                  <select
                    value={props.splitTenderTwo.payment_method}
                    onChange={(event) =>
                      props.setSplitTenderTwo((current) => ({
                        ...current,
                        payment_method: event.target.value as SplitTenderDraft["payment_method"],
                      }))
                    }
                  >
                    <option value="cash">Cash</option>
                    <option value="card">Card</option>
                    <option value="mobile">Mobile</option>
                  </select>
                </label>
                <label>
                  Tender 2 amount
                  <input
                    value={props.splitTenderTwo.amount}
                    onChange={(event) => props.setSplitTenderTwo((current) => ({ ...current, amount: event.target.value }))}
                    inputMode="decimal"
                  />
                </label>
                <div className="split-tender-note">Split tender total: ${props.splitTenderTotal.toFixed(2)}</div>
              </div>
            )}
            <div className="pos-total">Total: ${props.checkoutTotal.toFixed(2)}</div>
            <button type="button" className="button-primary" onClick={() => void props.checkoutSale()} disabled={props.checkoutBusy || props.basket.length === 0}>
              {props.checkoutBusy ? "Processing..." : "Checkout"}
            </button>
          </div>
        </section>
      </div>

      <div className="pos-layout">
        <section className="card">
          <h3 className="card-title">Receipt</h3>
          <p className="card-subtitle">Latest completed sale receipt with print view support.</p>

          {!props.latestReceipt && <p className="card-subtitle">Complete a sale to display receipt details.</p>}

          {props.latestReceipt && (
            <div className="receipt-card">
              <div className="row-gap">
                <span className="status-pill neutral">Sale #{props.latestReceipt.sale_id}</span>
                <span>{new Date(props.latestReceipt.created_at).toLocaleString()}</span>
                <span className="status-pill success">{props.latestReceipt.payment_method}</span>
                <span className={props.latestSaleStatus === "completed" ? "status-pill success" : "status-pill warning"}>
                  {props.latestSaleStatus}
                </span>
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Qty</th>
                    <th>Unit</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {props.latestReceipt.line_items.map((line) => (
                    <tr key={`${props.latestReceipt?.sale_id}-${line.product_id}`}>
                      <td>{props.productNameById.get(line.product_id) ?? `Product #${line.product_id}`}</td>
                      <td>{line.quantity}</td>
                      <td>{line.unit_price}</td>
                      <td>{line.line_total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="summary-grid receipt-summary">
                <div className="summary-stat">
                  <span>Subtotal</span>
                  <strong>${props.latestReceipt.subtotal}</strong>
                </div>
                <div className="summary-stat">
                  <span>Tax</span>
                  <strong>${props.latestReceipt.tax_amount}</strong>
                </div>
                <div className="summary-stat">
                  <span>Discount</span>
                  <strong>${props.latestReceipt.discount_amount}</strong>
                </div>
                <div className="summary-stat summary-full">
                  <span>Payment tenders</span>
                  <div className="row-gap">
                    {props.latestReceipt.payment_tenders.map((tender, index) => (
                      <span key={`${props.latestReceipt?.sale_id}-${index}`} className="status-pill neutral">
                        {tender.payment_method}: ${tender.amount}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="pos-total">Total: ${props.latestReceipt.total}</div>
              <div className="receipt-actions">
                <button type="button" className="button-secondary" onClick={() => window.print()}>
                  <Receipt size={14} strokeWidth={1.8} /> Print receipt
                </button>
                <button type="button" className="button-secondary" onClick={() => void props.authorizePaymentTenders()} disabled={props.paymentOpsBusy || props.latestSaleStatus !== "completed"}>
                  Authorize payment
                </button>
                <button type="button" className="button-secondary" onClick={() => void props.reconcilePaymentTenders()} disabled={props.paymentOpsBusy || props.latestSaleStatus !== "completed"}>
                  Reconcile payment (async)
                </button>
                <button type="button" className="button-secondary" onClick={() => void props.handleSaleAction("void")} disabled={props.saleActionBusy || props.latestSaleStatus !== "completed"}>
                  Void sale
                </button>
                <button type="button" className="button-secondary" onClick={() => void props.handleSaleAction("refund")} disabled={props.saleActionBusy || props.latestSaleStatus !== "completed"}>
                  Refund sale
                </button>
              </div>
              {props.paymentIntent && (
                <div className="summary-grid receipt-summary">
                  <div className="summary-stat summary-full">
                    <span>Payment intent ({props.paymentIntent.provider})</span>
                    <div className="row-gap">
                      {props.paymentIntent.authorized_tenders.map((tender) => (
                        <span key={tender.provider_reference} className="status-pill neutral">
                          {tender.payment_method}: ${tender.amount} ({tender.status})
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              {props.paymentReconcile && (
                <div className="summary-grid receipt-summary">
                  <div className="summary-stat summary-full">
                    <span>Reconciliation</span>
                    <strong>
                      {props.paymentReconcile.status} ${props.paymentReconcile.reconciled_amount} ({props.paymentReconcile.provider})
                    </strong>
                  </div>
                </div>
              )}
              {props.paymentJobStatus && !props.paymentReconcile && (
                <div className="summary-grid receipt-summary">
                  <div className="summary-stat summary-full">
                    <span>Reconciliation job</span>
                    <strong>
                      {props.paymentJobStatus.status} ({props.paymentJobStatus.provider})
                    </strong>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="card">
          <h3 className="card-title">Daily summary</h3>
          <p className="card-subtitle">Auto-polls every 15 seconds while POS tab is open.</p>

          {props.liveAnomalyAlert && <div className="form-error">{props.liveAnomalyAlert}</div>}

          {!props.dailySummary && <p className="card-subtitle">No summary data loaded yet.</p>}

          {props.dailySummary && (
            <div className="summary-grid">
              <div className="summary-stat">
                <span>Business date</span>
                <strong>{props.dailySummary.business_date}</strong>
              </div>
              <div className="summary-stat">
                <span>Sales count</span>
                <strong>{props.dailySummary.sales_count}</strong>
              </div>
              <div className="summary-stat">
                <span>Gross total</span>
                <strong>${props.dailySummary.gross_total}</strong>
              </div>
              <div className="summary-stat summary-full">
                <span>Payment methods</span>
                <div className="row-gap">
                  {Object.entries(props.dailySummary.payment_method_totals).map(([method, total]) => (
                    <span key={method} className="status-pill neutral">
                      {method}: ${total}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="summary-grid" style={{ marginTop: 12 }}>
            <div className="summary-stat summary-full">
              <span>Live event stream</span>
              <div className="row-gap">
                {props.liveEvents.length === 0 && <span className="status-pill neutral">No events yet</span>}
                {props.liveEvents.map((entry) => (
                  <span key={entry.id} className={entry.type === "anomaly_alert" ? "status-pill warning" : "status-pill neutral"}>
                    {new Date(entry.occurredAt).toLocaleTimeString()} - {entry.message}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
