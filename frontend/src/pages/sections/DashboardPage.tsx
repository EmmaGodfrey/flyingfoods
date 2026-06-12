import { Activity, BarChart3, Truck } from "lucide-react";

type DashboardPageProps = {
  productTotal: number;
  movementTotal: number;
  purchaseOrderTotal: number;
  onLoadInventory: () => void;
  onLoadHistory: () => void;
  onLoadSummary: () => void;
  busy: boolean;
  summaryBusy: boolean;
};

export function DashboardPage({
  productTotal,
  movementTotal,
  purchaseOrderTotal,
  onLoadInventory,
  onLoadHistory,
  onLoadSummary,
  busy,
  summaryBusy,
}: DashboardPageProps) {
  return (
    <section className="card" style={{ marginTop: 0 }}>
      <h3 className="card-title">Dashboard</h3>
      <p className="card-subtitle">Week 8 layout shell route. Use navigation to access Inventory, POS, Procurement, Reports, and Settings.</p>
      <div className="dashboard-actions">
        <button className="button-secondary" type="button" onClick={onLoadInventory} disabled={busy}>
          <Truck size={14} strokeWidth={1.8} /> Load inventory
        </button>
        <button className="button-secondary" type="button" onClick={onLoadHistory} disabled={busy}>
          <Activity size={14} strokeWidth={1.8} /> Load history
        </button>
        <button className="button-secondary" type="button" onClick={onLoadSummary} disabled={summaryBusy}>
          <BarChart3 size={14} strokeWidth={1.8} /> Load summary
        </button>
      </div>
      <div className="summary-grid">
        <div className="summary-stat">
          <span>Products loaded</span>
          <strong>{productTotal}</strong>
        </div>
        <div className="summary-stat">
          <span>Movements loaded</span>
          <strong>{movementTotal}</strong>
        </div>
        <div className="summary-stat">
          <span>POs loaded</span>
          <strong>{purchaseOrderTotal}</strong>
        </div>
      </div>
    </section>
  );
}
