import { useState } from "react";

import { PageHeader } from "../../components/ui";
import { BudgetsTab } from "./components/BudgetsTab";
import { PurchaseOrdersTab } from "./components/PurchaseOrdersTab";

type Tab = "BUDGETS" | "PURCHASE_ORDERS";

/** Budgets, purchase orders, goods received, and three-way invoice matching. */
export function ProcurementPage(): JSX.Element {
  const [tab, setTab] = useState<Tab>("BUDGETS");

  return (
    <div>
      <PageHeader
        title="Procurement"
        subtitle="Budgets, purchase orders, goods received, and three-way invoice matching."
      />

      <div className="toolbar">
        <div className="seg">
          <button className={tab === "BUDGETS" ? "active" : ""} onClick={() => setTab("BUDGETS")}>
            Budgets
          </button>
          <button className={tab === "PURCHASE_ORDERS" ? "active" : ""} onClick={() => setTab("PURCHASE_ORDERS")}>
            Purchase orders
          </button>
        </div>
      </div>

      {tab === "BUDGETS" ? <BudgetsTab /> : <PurchaseOrdersTab />}
    </div>
  );
}
