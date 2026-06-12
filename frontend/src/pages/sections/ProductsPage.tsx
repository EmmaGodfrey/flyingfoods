import { Search } from "lucide-react";

import { ReceiveStockForm } from "../../components/ReceiveStockForm";
import type { Product, StockSummary } from "../../types";

type ProductsPageProps = {
  search: string;
  setSearch: (value: string) => void;
  loadProductsAndStock: (offset: number) => Promise<void>;
  setEditingProduct: (product: Product | null) => void;
  setModalOpen: (open: boolean) => void;
  products: Product[];
  stockMap: Map<number, number>;
  categoryNameById: Map<number, string>;
  unitLabelById: Map<number, string>;
  stockBadge: (product: Product, stockMap: Map<number, number>) => { label: string; className: string };
  productTotal: number;
  productOffset: number;
  busy: boolean;
  prevProductOffset: number;
  nextProductOffset: number;
  receiveStock: (productId: number, qty: string, referenceId: string) => Promise<void>;
};

export function ProductsPage({
  search,
  setSearch,
  loadProductsAndStock,
  setEditingProduct,
  setModalOpen,
  products,
  stockMap,
  categoryNameById,
  unitLabelById,
  stockBadge,
  productTotal,
  productOffset,
  busy,
  prevProductOffset,
  nextProductOffset,
  receiveStock,
}: ProductsPageProps) {
  return (
    <>
      <div className="section-head">
        <h2>Products list</h2>
        <div className="row-gap">
          <div className="search-wrap">
            <Search size={14} strokeWidth={1.8} />
            <input placeholder="Search product name" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <button type="button" className="button-secondary" onClick={() => void loadProductsAndStock(0)}>
            Search
          </button>
          <button
            type="button"
            className="button-primary"
            onClick={() => {
              setEditingProduct(null);
              setModalOpen(true);
            }}
          >
            Add product
          </button>
        </div>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Category</th>
            <th>Unit</th>
            <th>Current stock</th>
            <th>Reorder level</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => {
            const status = stockBadge(product, stockMap);
            const currentStock = stockMap.get(product.id) ?? 0;
            const categoryText = product.category_id
              ? `${categoryNameById.get(product.category_id) ?? "Unknown category"} (#${product.category_id})`
              : "-";
            const unitText = `${unitLabelById.get(product.unit_id) ?? "Unknown unit"} (#${product.unit_id})`;
            return (
              <tr key={product.id}>
                <td>{product.name}</td>
                <td>{categoryText}</td>
                <td>{unitText}</td>
                <td>{currentStock.toFixed(2)}</td>
                <td>{product.reorder_level}</td>
                <td>
                  <span className={status.className}>{status.label}</span>
                </td>
                <td>
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => {
                      setEditingProduct(product);
                      setModalOpen(true);
                    }}
                  >
                    Edit
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="pager-row">
        <div>
          Showing {products.length} of {productTotal}
        </div>
        <div className="row-gap">
          <button
            type="button"
            className="button-secondary"
            onClick={() => void loadProductsAndStock(prevProductOffset)}
            disabled={productOffset === 0 || busy}
          >
            Previous
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void loadProductsAndStock(nextProductOffset)}
            disabled={nextProductOffset >= productTotal || busy}
          >
            Next
          </button>
        </div>
      </div>

      <ReceiveStockForm products={products} onSubmit={receiveStock} />
    </>
  );
}
