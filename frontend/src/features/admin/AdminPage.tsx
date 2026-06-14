import { useState } from "react";

import { PageHeader } from "../../components/ui";
import { IntegrationTab } from "./components/IntegrationTab";
import { ProductsTab } from "./components/ProductsTab";
import { SuppliersTab } from "./components/SuppliersTab";
import { ThresholdsTab } from "./components/ThresholdsTab";
import { UsersTab } from "./components/UsersTab";

type Tab = "USERS" | "PRODUCTS" | "SUPPLIERS" | "THRESHOLDS" | "INTEGRATION";

const TABS: { key: Tab; label: string }[] = [
  { key: "USERS", label: "Users" },
  { key: "PRODUCTS", label: "Products" },
  { key: "SUPPLIERS", label: "Suppliers" },
  { key: "THRESHOLDS", label: "Thresholds" },
  { key: "INTEGRATION", label: "Integration" },
];

/** Administration: users, products, suppliers, thresholds, and integration settings. */
export function AdminPage(): JSX.Element {
  const [tab, setTab] = useState<Tab>("USERS");

  return (
    <div>
      <PageHeader
        title="Administration"
        subtitle="Users, products, suppliers, thresholds, and integration settings."
      />

      <div className="toolbar">
        <div className="seg">
          {TABS.map((t) => (
            <button key={t.key} className={tab === t.key ? "active" : ""} onClick={() => setTab(t.key)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === "USERS" && <UsersTab />}
      {tab === "PRODUCTS" && <ProductsTab />}
      {tab === "SUPPLIERS" && <SuppliersTab />}
      {tab === "THRESHOLDS" && <ThresholdsTab />}
      {tab === "INTEGRATION" && <IntegrationTab />}
    </div>
  );
}
