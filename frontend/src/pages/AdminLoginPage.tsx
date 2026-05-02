/**
 * Admin login page — form to authenticate and get JWT.
 */

import { useCallback, useState } from "react";
import { adminLogin } from "../api/client";
import { useAdminAuthStore } from "../stores/adminAuthStore";

export default function AdminLoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const setJwt = useAdminAuthStore((s) => s.setJwt);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);
      setLoading(true);

      try {
        const { access_token } = await adminLogin(email, password);
        setJwt(access_token);
        window.location.href = "/admin";
      } catch (err) {
        setError(err instanceof Error ? err.message : "Login failed");
      } finally {
        setLoading(false);
      }
    },
    [email, password, setJwt],
  );

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#0f0f0f",
        color: "#fafafa",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "360px",
          padding: "2.5rem",
          border: "1px solid #222",
          borderRadius: "1rem",
          backgroundColor: "#141414",
        }}
      >
        <h1
          style={{
            fontSize: "1.5rem",
            fontWeight: 700,
            marginBottom: "0.5rem",
            textAlign: "center",
          }}
        >
          🔒 Admin Login
        </h1>
        <p
          style={{
            fontSize: "0.8125rem",
            color: "#666",
            textAlign: "center",
            marginBottom: "2rem",
          }}
        >
          Raidio admin console
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label
              style={{
                display: "block",
                fontSize: "0.75rem",
                color: "#888",
                marginBottom: "0.375rem",
                textTransform: "uppercase",
                fontWeight: 600,
              }}
            >
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              style={inputStyle}
              placeholder="admin@raidio.local"
            />
          </div>

          <div style={{ marginBottom: "1.5rem" }}>
            <label
              style={{
                display: "block",
                fontSize: "0.75rem",
                color: "#888",
                marginBottom: "0.375rem",
                textTransform: "uppercase",
                fontWeight: 600,
              }}
            >
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={inputStyle}
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div
              style={{
                padding: "0.625rem 0.75rem",
                backgroundColor: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "0.5rem",
                color: "#ef4444",
                fontSize: "0.8125rem",
                marginBottom: "1rem",
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !email || !password}
            style={{
              width: "100%",
              padding: "0.75rem",
              fontSize: "0.875rem",
              fontWeight: 600,
              border: "none",
              borderRadius: "0.5rem",
              backgroundColor: loading || !email || !password ? "#333" : "#fafafa",
              color: loading || !email || !password ? "#666" : "#0f0f0f",
              cursor: loading || !email || !password ? "not-allowed" : "pointer",
              transition: "all 0.2s ease",
            }}
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.625rem 0.75rem",
  fontSize: "0.875rem",
  backgroundColor: "#111",
  border: "1px solid #333",
  borderRadius: "0.5rem",
  color: "#fafafa",
  outline: "none",
  boxSizing: "border-box",
};
