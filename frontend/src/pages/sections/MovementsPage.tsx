import type { StockMovement } from "../../types";

type MovementsPageProps = {
  movementType: string;
  setMovementType: (value: string) => void;
  occurredAfter: string;
  setOccurredAfter: (value: string) => void;
  occurredBefore: string;
  setOccurredBefore: (value: string) => void;
  loadMovements: (offset: number) => Promise<void>;
  movements: StockMovement[];
  movementTotal: number;
  productNameById: Map<number, string>;
};

export function MovementsPage({
  movementType,
  setMovementType,
  occurredAfter,
  setOccurredAfter,
  occurredBefore,
  setOccurredBefore,
  loadMovements,
  movements,
  movementTotal,
  productNameById,
}: MovementsPageProps) {
  return (
    <>
      <div className="section-head">
        <h2>Stock movement history</h2>
      </div>

      <section className="movement-filters">
        <div className="movement-filters-grid">
          <label>
            Type
            <select value={movementType} onChange={(e) => setMovementType(e.target.value)}>
              <option value="all">All types</option>
              <option value="receive">Receive</option>
              <option value="sale">Sale</option>
              <option value="waste">Waste</option>
              <option value="adjustment">Adjustment</option>
            </select>
          </label>
          <label>
            From
            <input type="datetime-local" value={occurredAfter} onChange={(e) => setOccurredAfter(e.target.value)} />
          </label>
          <label>
            To
            <input type="datetime-local" value={occurredBefore} onChange={(e) => setOccurredBefore(e.target.value)} />
          </label>
        </div>
        <div className="inline-form-actions">
          <button type="button" className="button-secondary" onClick={() => void loadMovements(0)}>
            Apply filters
          </button>
        </div>
      </section>

      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Type</th>
            <th>Product</th>
            <th>Qty</th>
            <th>Reference</th>
            <th>Created by</th>
          </tr>
        </thead>
        <tbody>
          {movements.map((movement) => (
            <tr key={movement.id}>
              <td>{new Date(movement.created_at).toLocaleString()}</td>
              <td>
                <span className="status-pill neutral">{movement.movement_type}</span>
              </td>
              <td>{productNameById.get(movement.product_id) ?? `Product #${movement.product_id}`}</td>
              <td>{movement.qty}</td>
              <td>{movement.reference_id || "-"}</td>
              <td>{movement.created_by ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pager-row">Total movements: {movementTotal}</div>
    </>
  );
}
