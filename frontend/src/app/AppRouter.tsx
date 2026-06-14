import {
  BarChart3,
  Boxes,
  ClipboardList,
  FileText,
  PackageSearch,
  Settings,
  ShoppingCart,
  Trash2,
} from "lucide-react";
import { Navigate, Route, Routes } from "react-router-dom";

import { Placeholder } from "../components/Placeholder";
import { LoginPage } from "../features/auth/LoginPage";
import { KitchenBoard } from "../features/kitchen/KitchenBoard";
import { WaiterBoard } from "../features/waiter/WaiterBoard";
import { useAuthStore } from "../store/authStore";
import { AppShell } from "./AppShell";
import { landingPathForRole } from "./navigation";
import { RequireAuth } from "./RequireAuth";

/** Send the signed-in user to their role's first permitted section. */
function RoleLanding(): JSX.Element {
  const user = useAuthStore((state) => state.user);
  return <Navigate to={user ? landingPathForRole(user.role) : "/login"} replace />;
}

export function AppRouter(): JSX.Element {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        {/* Full-bleed live boards render their own chrome. */}
        <Route path="/kitchen" element={<KitchenBoard />} />
        <Route path="/waiter" element={<WaiterBoard />} />

        {/* Standard sections live inside the app shell. */}
        <Route element={<AppShell />}>
          <Route path="/stock" element={<Placeholder icon={Boxes} title="Stock on hand" description="Live balances across Stores, Kitchen, and Unit, with reorder-level flags." />} />
          <Route path="/issues" element={<Placeholder icon={ClipboardList} title="Issues & transfers" description="Daily issues to the kitchen, Tue/Thu unit orders, and inter-unit transfers." />} />
          <Route path="/procurement" element={<Placeholder icon={ShoppingCart} title="Procurement" description="Budgets, purchase orders, goods received, and three-way invoice matching." />} />
          <Route path="/wastage" element={<Placeholder icon={Trash2} title="Wastage & stock-take" description="Log breakage and spoilage, run stock-takes, and review variance." />} />
          <Route path="/menu" element={<Placeholder icon={PackageSearch} title="Menu & recipes" description="Versioned recipes with a draft-review-publish workflow." />} />
          <Route path="/approvals" element={<Placeholder icon={FileText} title="Approvals" description="One queue for budgets, large wastage, transfers, and stock overrides." />} />
          <Route path="/reports" element={<Placeholder icon={BarChart3} title="Reports" description="Stock, budget-vs-actual, wastage, service time, and the leakage report." />} />
          <Route path="/admin" element={<Placeholder icon={Settings} title="Administration" description="Users, products, suppliers, thresholds, and integration settings." />} />
        </Route>

        <Route path="/" element={<RoleLanding />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
