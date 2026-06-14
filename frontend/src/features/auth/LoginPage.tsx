import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { toast } from "sonner";

import { ApiError } from "../../lib/apiClient";
import { easeOut } from "../../lib/motion";
import { useAuthStore } from "../../store/authStore";
import { landingPathForRole } from "../../app/navigation";

/** Sign-in screen. Access token goes to memory; refresh is set as a cookie. */
export function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const [email, setEmail] = useState("manager@ff.local");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setBusy(true);
    try {
      await login(email, password);
      const role = useAuthStore.getState().user?.role;
      toast.success("Signed in");
      navigate(role ? landingPathForRole(role) : "/", { replace: true });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Sign-in failed.";
      toast.error(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <aside className="auth-aside">
        <motion.div
          className="brand"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0, transition: { duration: 0.3, ease: easeOut } }}
          style={{ color: "#fff", padding: 0 }}
        >
          <span className="brand-mark">FF</span>
          Flying Foods
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0, transition: { delay: 0.05, duration: 0.4, ease: easeOut } }}
        >
          <h2>The kitchen, the stores and the books, speaking in real time.</h2>
          <p style={{ marginTop: 16 }}>
            Orders land on the line the moment a sale clears. Stock moves itself. Every
            gram is traceable from the supplier to the plate.
          </p>
        </motion.div>
        <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)" }}>
          Restaurant &amp; Inventory Management System
        </div>
        <div className="auth-orb" style={{ width: 320, height: 320, right: -80, bottom: -90 }} />
        <div className="auth-orb" style={{ width: 160, height: 160, right: 120, top: 60 }} />
      </aside>

      <section className="auth-panel">
        <motion.form
          className="auth-card"
          onSubmit={onSubmit}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0, transition: { duration: 0.3, ease: easeOut } }}
        >
          <h1>Welcome back</h1>
          <p className="auth-sub">Sign in to your station.</p>

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              autoComplete="username"
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          <button className="btn btn-primary btn-lg btn-block" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>

          <p className="seed-hint">
            Demo build: log in as <strong>chef@ff.local</strong>, <strong>waiter@ff.local</strong>,
            <strong> manager@ff.local</strong> … (one per role) with the password printed by
            <code> seed_demo</code>.
          </p>
        </motion.form>
      </section>
    </div>
  );
}
