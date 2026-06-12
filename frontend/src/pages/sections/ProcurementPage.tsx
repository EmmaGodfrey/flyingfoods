import { RefreshCw, Search } from "lucide-react";

import type {
  Product,
  GoodsReceivedNote,
  ProcurementOrdersReportResponse,
  ProcurementSpendResponse,
  PurchaseOrder,
  Supplier,
} from "../../types";

type ProcurementPageProps = {
  supplierSearch: string;
  setSupplierSearch: (value: string) => void;
  loadProcurement: () => Promise<void>;
  procurementBusy: boolean;
  supplierName: string;
  setSupplierName: (value: string) => void;
  supplierContact: string;
  setSupplierContact: (value: string) => void;
  supplierPhone: string;
  setSupplierPhone: (value: string) => void;
  supplierEmail: string;
  setSupplierEmail: (value: string) => void;
  saveSupplier: () => Promise<void>;
  editingSupplierId: number | null;
  setEditingSupplierId: (value: number | null) => void;
  suppliers: Supplier[];
  products: Product[];
  deleteSupplierById: (supplierId: number) => Promise<void>;
  editSupplier: (supplier: Supplier) => void;
  supplierTotal: number;
  poSupplierId: string;
  setPoSupplierId: (value: string) => void;
  poProductId: string;
  setPoProductId: (value: string) => void;
  poQuantity: string;
  setPoQuantity: (value: string) => void;
  poUnitPrice: string;
  setPoUnitPrice: (value: string) => void;
  poNotes: string;
  setPoNotes: (value: string) => void;
  createPurchaseOrder: () => Promise<void>;
  grnPoId: string;
  setGrnPoId: (value: string) => void;
  grnLineId: string;
  setGrnLineId: (value: string) => void;
  grnQty: string;
  setGrnQty: (value: string) => void;
  grnReference: string;
  setGrnReference: (value: string) => void;
  createGrn: () => Promise<void>;
  latestGrn: GoodsReceivedNote | null;
  purchaseOrders: PurchaseOrder[];
  submitPurchaseOrderById: (purchaseOrderId: number) => Promise<void>;
  approvePurchaseOrderById: (purchaseOrderId: number) => Promise<void>;
  purchaseOrderTotal: number;
  ordersReport: ProcurementOrdersReportResponse | null;
  spendReport: ProcurementSpendResponse | null;
};

export function ProcurementPage(props: ProcurementPageProps) {
  return (
    <>
      <div className="section-head">
        <h2>Procurement workflow</h2>
        <div className="row-gap">
          <div className="search-wrap">
            <Search size={14} strokeWidth={1.8} />
            <input
              placeholder="Search suppliers"
              value={props.supplierSearch}
              onChange={(event) => props.setSupplierSearch(event.target.value)}
            />
          </div>
          <button type="button" className="button-secondary" onClick={() => void props.loadProcurement()} disabled={props.procurementBusy}>
            <RefreshCw size={14} strokeWidth={1.8} /> Reload procurement
          </button>
        </div>
      </div>

      <section className="card">
        <h3 className="card-title">Suppliers management</h3>
        <p className="card-subtitle">Create, edit, search, and remove suppliers for PO workflows.</p>
        <div className="inline-form-grid">
          <label>
            Name
            <input value={props.supplierName} onChange={(event) => props.setSupplierName(event.target.value)} />
          </label>
          <label>
            Contact name
            <input value={props.supplierContact} onChange={(event) => props.setSupplierContact(event.target.value)} />
          </label>
          <label>
            Phone
            <input value={props.supplierPhone} onChange={(event) => props.setSupplierPhone(event.target.value)} />
          </label>
          <label className="summary-full">
            Email
            <input value={props.supplierEmail} onChange={(event) => props.setSupplierEmail(event.target.value)} />
          </label>
        </div>
        <div className="inline-form-actions row-gap">
          <button type="button" className="button-primary" onClick={() => void props.saveSupplier()} disabled={props.procurementBusy}>
            {props.editingSupplierId ? "Update supplier" : "Create supplier"}
          </button>
          {props.editingSupplierId && (
            <button
              type="button"
              className="button-secondary"
              onClick={() => {
                props.setEditingSupplierId(null);
                props.setSupplierName("");
                props.setSupplierContact("");
                props.setSupplierPhone("");
                props.setSupplierEmail("");
              }}
            >
              Cancel edit
            </button>
          )}
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Contact</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {props.suppliers.map((supplier) => (
              <tr key={supplier.supplier_id}>
                <td>#{supplier.supplier_id}</td>
                <td>{supplier.name}</td>
                <td>{supplier.contact_name || "-"}</td>
                <td>{supplier.email || "-"}</td>
                <td>{supplier.phone || "-"}</td>
                <td>
                  <div className="row-gap">
                    <button type="button" className="text-button" onClick={() => props.editSupplier(supplier)}>
                      Edit
                    </button>
                    <button type="button" className="text-button" onClick={() => void props.deleteSupplierById(supplier.supplier_id)}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="pager-row">Total suppliers: {props.supplierTotal}</div>
      </section>

      <div className="pos-layout">
        <section className="card">
          <h3 className="card-title">Create purchase order</h3>
          <p className="card-subtitle">Week 11 UI for supplier orders and branch-scoped workflow actions.</p>
          <div className="inline-form-grid">
            <label>
              Supplier
              <select value={props.poSupplierId} onChange={(event) => props.setPoSupplierId(event.target.value)}>
                {props.suppliers.map((supplier) => (
                  <option key={supplier.supplier_id} value={supplier.supplier_id}>
                    {supplier.name} (#{supplier.supplier_id})
                  </option>
                ))}
              </select>
            </label>
            <label>
              Product
              <select value={props.poProductId} onChange={(event) => props.setPoProductId(event.target.value)}>
                <option value="">Select a product</option>
                {props.products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name} (#{product.id})
                  </option>
                ))}
              </select>
            </label>
            <label>
              Quantity
              <input value={props.poQuantity} onChange={(event) => props.setPoQuantity(event.target.value)} inputMode="decimal" />
            </label>
            <label>
              Unit price
              <input value={props.poUnitPrice} onChange={(event) => props.setPoUnitPrice(event.target.value)} inputMode="decimal" />
            </label>
            <label className="summary-full">
              Notes
              <input value={props.poNotes} onChange={(event) => props.setPoNotes(event.target.value)} />
            </label>
          </div>
          <div className="inline-form-actions">
            <button type="button" className="button-primary" onClick={() => void props.createPurchaseOrder()} disabled={props.procurementBusy}>
              Create PO
            </button>
          </div>
        </section>

        <section className="card">
          <h3 className="card-title">Goods received note</h3>
          <p className="card-subtitle">Receive against approved POs and post stock.received movements.</p>
          <div className="inline-form-grid">
            <label>
              Purchase order
              <select value={props.grnPoId} onChange={(event) => props.setGrnPoId(event.target.value)}>
                <option value="">Select a purchase order</option>
                {props.purchaseOrders.map((order) => (
                  <option key={order.purchase_order_id} value={order.purchase_order_id}>
                    PO #{order.purchase_order_id} - {order.supplier_name} ({order.status})
                  </option>
                ))}
              </select>
            </label>
            <label>
              PO line item
              <select value={props.grnLineId} onChange={(event) => props.setGrnLineId(event.target.value)}>
                <option value="">Select a purchase order line</option>
                {props.purchaseOrders
                  .find((order) => String(order.purchase_order_id) === props.grnPoId)
                  ?.line_items.map((lineItem) => (
                    <option key={lineItem.line_item_id} value={lineItem.line_item_id}>
                      {lineItem.product_name} - ordered {lineItem.quantity}, received {lineItem.received_quantity}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Received quantity
              <input value={props.grnQty} onChange={(event) => props.setGrnQty(event.target.value)} inputMode="decimal" />
            </label>
            <label className="summary-full">
              Reference
              <input value={props.grnReference} onChange={(event) => props.setGrnReference(event.target.value)} />
            </label>
          </div>
          <div className="inline-form-actions">
            <button type="button" className="button-primary" onClick={() => void props.createGrn()} disabled={props.procurementBusy}>
              Record GRN
            </button>
          </div>
          {props.latestGrn && (
            <div className="summary-grid" style={{ marginTop: 12 }}>
              <div className="summary-stat summary-full">
                <span>Latest GRN</span>
                <strong>
                  #{props.latestGrn.goods_received_note_id} status {props.latestGrn.status_after_receipt}
                </strong>
              </div>
            </div>
          )}
        </section>
      </div>

      <section className="card">
        <h3 className="card-title">Purchase orders</h3>
        <p className="card-subtitle">Submit and approve from the list.</p>
        <table className="data-table">
          <thead>
            <tr>
              <th>PO</th>
              <th>Supplier</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {props.purchaseOrders.map((order) => (
              <tr key={order.purchase_order_id}>
                <td>#{order.purchase_order_id}</td>
                <td>{order.supplier_name}</td>
                <td>
                  <span className="status-pill neutral">{order.status}</span>
                </td>
                <td>{new Date(order.created_at).toLocaleString()}</td>
                <td>
                  <div className="row-gap">
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => void props.submitPurchaseOrderById(order.purchase_order_id)}
                      disabled={order.status !== "draft" || props.procurementBusy}
                    >
                      Submit
                    </button>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => void props.approvePurchaseOrderById(order.purchase_order_id)}
                      disabled={order.status !== "submitted" || props.procurementBusy}
                    >
                      Approve
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="pager-row">Total purchase orders: {props.purchaseOrderTotal}</div>
      </section>

      <div className="pos-layout">
        <section className="card">
          <h3 className="card-title">Orders report</h3>
          <p className="card-subtitle">Server aggregate by status and supplier.</p>
          {!props.ordersReport && <p className="card-subtitle">No report loaded yet.</p>}
          {props.ordersReport && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>PO</th>
                  <th>Supplier</th>
                  <th>Status</th>
                  <th>Ordered</th>
                  <th>Received</th>
                </tr>
              </thead>
              <tbody>
                {props.ordersReport.items.map((row) => (
                  <tr key={`report-${row.purchase_order_id}`}>
                    <td>#{row.purchase_order_id}</td>
                    <td>{row.supplier_name}</td>
                    <td>{row.status}</td>
                    <td>${row.ordered_total}</td>
                    <td>${row.received_total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="card">
          <h3 className="card-title">Spend report</h3>
          <p className="card-subtitle">GRN/PO based supplier spend by month.</p>
          {!props.spendReport && <p className="card-subtitle">No spend report loaded yet.</p>}
          {props.spendReport && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Supplier</th>
                  <th>Total spend</th>
                </tr>
              </thead>
              <tbody>
                {props.spendReport.rows.map((row) => (
                  <tr key={`${row.month}-${row.supplier_name}`}>
                    <td>{row.month}</td>
                    <td>{row.supplier_name}</td>
                    <td>${row.total_spend}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </>
  );
}
