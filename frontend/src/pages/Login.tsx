import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiError, BACKEND_URL } from "../api";
import { useAuth } from "../auth";
import type { User } from "../types";

export default function Login() {
  const { setToken } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleEnabled, setGoogleEnabled] = useState(false);

  useEffect(() => {
    api.get("/api/auth/config").then(({ data }) => setGoogleEnabled(!!data.google_enabled));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const body = mode === "login" ? { email, password } : { email, password, name };
      const { data } = await api.post<{ access_token: string; user: User }>(path, body);
      await setToken(data.access_token);
      navigate("/");
    } catch (err) {
      setError(apiError(err, "Authentication failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="brand">
          Portfolio<span>XIRR</span>
        </div>
        <p style={{ color: "var(--muted)", marginTop: 0 }}>
          Track MF, Stocks, FD, Bonds, NPS, PF, Crypto, Policies &amp; Gratuity — all in one place.
        </p>

        {googleEnabled && (
          <>
            <a className="btn google-btn" href={`${BACKEND_URL}/api/auth/google/login`}>
              Continue with Google
            </a>
            <div className="divider">or</div>
          </>
        )}

        <form onSubmit={submit}>
          {mode === "register" && (
            <div className="field">
              <label>Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
            </div>
          )}
          <div className="field">
            <label>Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          {error && <div className="error-msg">{error}</div>}
          <button className="btn btn-primary btn-block" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <div style={{ marginTop: "1rem", fontSize: "0.88rem", color: "var(--muted)" }}>
          {mode === "login" ? "New here? " : "Already have an account? "}
          <button
            className="link-btn"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
          >
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
