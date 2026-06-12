import { useMemo, useState } from "react";
import type { Product } from "../types";

type ReceiveStockFormProps = {
  products: Product[];
  onSubmit: (productId: number, qty: string, referenceId: string) => Promise<void>;
};

export function ReceiveStockForm({ products, onSubmit }: ReceiveStockFormProps) {
  const [productId, setProductId] = useState<string>("");
  const [qty, setQty] = useState<string>("1.00");
  const [referenceId, setReferenceId] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>("");

  const productOptions = useMemo(
    () => products.map((p) => ({ id: p.id, label: `${p.name} (#${p.id})` })),
    [products],
  );

  const submit = async () => {
    setError("");
    if (!productId) {
      setError("Select a product");
      return;
    }
    if (!/^\d+(\.\d{1,2})?$/.test(qty) || Number(qty) <= 0) {
      setError("Quantity must be a positive decimal");
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit(Number(productId), qty, referenceId);
      setQty("1.00");
      setReferenceId("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <h3 className="card-title">Receive stock</h3>
      <p className="card-subtitle">Create a stock_received movement and refresh running stock totals.</p>

      <div className="inline-form-grid">
        <label>
          Product
          <select value={productId} onChange={(e) => setProductId(e.target.value)}>
            <option value="">Select product</option>
            {productOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Quantity
          <input value={qty} onChange={(e) => setQty(e.target.value)} />
        </label>

        <label>
          Reference
          <input value={referenceId} onChange={(e) => setReferenceId(e.target.value)} placeholder="PO-1001" />
        </label>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="inline-form-actions">
        <button className="button-primary" onClick={submit} disabled={submitting} type="button">
          {submitting ? "Submitting..." : "Receive stock"}
        </button>
      </div>
    </div>
  );
}
