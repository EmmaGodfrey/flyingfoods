import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuthStore } from "../store/authStore";

/** Gate protected routes; trigger the one-time silent refresh on first mount. */
export function RequireAuth(): JSX.Element | null {
  const status = useAuthStore((state) => state.status);
  const bootstrap = useAuthStore((state) => state.bootstrap);
  const location = useLocation();

  useEffect(() => {
    if (status === "loading") void bootstrap();
  }, [status, bootstrap]);

  if (status === "loading") {
    return (
      <div className="empty" style={{ minHeight: "100vh" }}>
        <span className="spin" style={{ display: "inline-block", width: 22, height: 22, border: "3px solid var(--ink-200)", borderTopColor: "var(--brand-500)", borderRadius: "50%" }} />
      </div>
    );
  }
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
