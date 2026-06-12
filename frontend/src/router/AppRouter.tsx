import { Navigate, Route, Routes } from "react-router-dom";

import App from "../App";
import { useAuth } from "../auth/AuthContext";
import { LoginPage } from "../pages/LoginPage";
import { PrivateRoute } from "./PrivateRoute";

export function AppRouter() {
  const { accessToken, refreshToken, setTokens, clearTokens } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<PrivateRoute />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route
          path="/:section"
          element={
            <App
              initialAccessToken={accessToken}
              initialRefreshToken={refreshToken}
              onTokensChange={setTokens}
              onSignOut={clearTokens}
            />
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
