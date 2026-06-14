import { Navigate, Route, Routes } from "react-router-dom";

import { AdminPage } from "../features/admin/AdminPage";
import { ApprovalsPage } from "../features/approvals/ApprovalsPage";
import { LoginPage } from "../features/auth/LoginPage";
import { IssuesPage } from "../features/issues/IssuesPage";
import { KitchenBoard } from "../features/kitchen/KitchenBoard";
import { MenuPage } from "../features/menu/MenuPage";
import { ProcurementPage } from "../features/procurement/ProcurementPage";
import { ReportsPage } from "../features/reports/ReportsPage";
import { StockPage } from "../features/stock/StockPage";
import { WaiterBoard } from "../features/waiter/WaiterBoard";
import { WastagePage } from "../features/wastage/WastagePage";
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
          <Route path="/stock" element={<StockPage />} />
          <Route path="/issues" element={<IssuesPage />} />
          <Route path="/procurement" element={<ProcurementPage />} />
          <Route path="/wastage" element={<WastagePage />} />
          <Route path="/menu" element={<MenuPage />} />
          <Route path="/approvals" element={<ApprovalsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Route>

        <Route path="/" element={<RoleLanding />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
