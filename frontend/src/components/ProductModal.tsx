import { useEffect, useState } from "react";
import type { Category, Product, ProductFormInput, Unit } from "../types";

type ProductModalProps = {
  open: boolean;
  product: Product | null;
  categories: Category[];
  units: Unit[];
  onClose: () => void;
  onSave: (input: ProductFormInput, productId?: number) => Promise<void>;
};

const EMPTY_FORM: ProductFormInput = {
  name: "",
  unit_id: "",
  category_id: "",
  supplier_id: "",
  sku: "",
  barcode: "",
  reorder_level: "0.00",
  cost_price: "0.00",
  selling_price: "0.00",
};

function decimalRegex(value: string) {
  return /^-?\d+(\.\d{1,2})?$/.test(value);
}

function validateProductForm(form: ProductFormInput) {
  const next: Record<string, string> = {};
  if (!form.name.trim()) {
    next.name = "Product name is required";
  }
  if (!form.category_id || Number.isNaN(Number(form.category_id)) || Number(form.category_id) <= 0) {
    next.category_id = "Category ID is required";
  }
  if (!form.unit_id || Number.isNaN(Number(form.unit_id)) || Number(form.unit_id) <= 0) {
    next.unit_id = "Unit ID is required";
  }
  if (!decimalRegex(form.reorder_level)) {
    next.reorder_level = "Use decimal format like 5.00";
  }
  if (!decimalRegex(form.cost_price)) {
    next.cost_price = "Use decimal format like 2.50";
  }
  if (!decimalRegex(form.selling_price)) {
    next.selling_price = "Use decimal format like 4.99";
  }
  return next;
}

export function ProductModal({ open, product, categories, units, onClose, onSave }: ProductModalProps) {
  const [form, setForm] = useState<ProductFormInput>(EMPTY_FORM);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (!product) {
      setForm(EMPTY_FORM);
      setErrors({});
      return;
    }

    setForm({
      name: product.name,
      unit_id: String(product.unit_id),
      category_id: product.category_id ? String(product.category_id) : "",
      supplier_id: product.supplier_id ? String(product.supplier_id) : "",
      sku: product.sku || "",
      barcode: product.barcode || "",
      reorder_level: product.reorder_level,
      cost_price: product.cost_price,
      selling_price: product.selling_price,
    });
    setErrors({});
  }, [open, product]);

  if (!open) {
    return null;
  }

  const updateField = (field: keyof ProductFormInput, value: string) => {
    const nextForm = { ...form, [field]: value };
    setForm(nextForm);
    setErrors((current) => {
      const next = { ...current };
      if (field === "name" || field === "category_id" || field === "unit_id" || field === "reorder_level" || field === "cost_price" || field === "selling_price") {
        const validation = validateProductForm(nextForm);
        if (validation[field]) {
          next[field] = validation[field];
        } else {
          delete next[field];
        }
      }
      return next;
    });
  };

  const blurField = () => {
    setErrors(validateProductForm(form));
  };

  const validate = () => {
    const next = validateProductForm(form);
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async () => {
    if (!validate()) {
      return;
    }
    onClose();
    void onSave(form, product?.id);
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <div className="modal-header">
          <h3>{product ? "Edit product" : "Add product"}</h3>
          <button className="text-button" onClick={onClose} type="button">
            Close
          </button>
        </div>

        <div className="form-grid">
          <label>
            Product name
            <input value={form.name} onChange={(e) => updateField("name", e.target.value)} onBlur={blurField} />
            {errors.name && <span className="field-error">{errors.name}</span>}
          </label>

          <label>
            Category
            <select value={form.category_id} onChange={(e) => updateField("category_id", e.target.value)} onBlur={blurField}>
              <option value="">Select category</option>
              {categories.map((category) => (
                <option key={category.id} value={String(category.id)}>
                  {category.name} (#{category.id})
                </option>
              ))}
            </select>
            {errors.category_id && <span className="field-error">{errors.category_id}</span>}
          </label>

          <label>
            Unit
            <select value={form.unit_id} onChange={(e) => updateField("unit_id", e.target.value)} onBlur={blurField}>
              <option value="">Select unit</option>
              {units.map((unit) => (
                <option key={unit.id} value={String(unit.id)}>
                  {unit.name} ({unit.symbol}) (#{unit.id})
                </option>
              ))}
            </select>
            {errors.unit_id && <span className="field-error">{errors.unit_id}</span>}
          </label>

          <label>
            Reorder level
            <input inputMode="decimal" value={form.reorder_level} onChange={(e) => updateField("reorder_level", e.target.value)} onBlur={blurField} />
            {errors.reorder_level && <span className="field-error">{errors.reorder_level}</span>}
          </label>

          <label>
            Cost price
            <input inputMode="decimal" value={form.cost_price} onChange={(e) => updateField("cost_price", e.target.value)} onBlur={blurField} />
            {errors.cost_price && <span className="field-error">{errors.cost_price}</span>}
          </label>

          <label>
            Selling price
            <input inputMode="decimal" value={form.selling_price} onChange={(e) => updateField("selling_price", e.target.value)} onBlur={blurField} />
            {errors.selling_price && <span className="field-error">{errors.selling_price}</span>}
          </label>
        </div>

        <div className="modal-actions">
          <button type="button" className="button-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="button-primary" disabled={saving} onClick={submit}>
            {saving ? "Saving..." : product ? "Save changes" : "Create product"}
          </button>
        </div>
      </div>
    </div>
  );
}
