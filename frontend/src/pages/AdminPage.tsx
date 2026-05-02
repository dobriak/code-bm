/**
 * Admin page — shows scan panel (auth gating in Phase 4).
 */
import AdminScanPanel from "../components/AdminScanPanel";

export default function AdminPage() {
  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f0f0f", color: "#fafafa" }}>
      <nav
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1.5rem",
          padding: "0.75rem 1.5rem",
          borderBottom: "1px solid #1a1a1a",
        }}
      >
        <a href="/" style={{ color: "#fafafa", textDecoration: "none", fontWeight: 700, fontSize: "1.125rem" }}>
          Raidio
        </a>
        <a href="/" style={{ color: "#888", textDecoration: "none", fontSize: "0.875rem" }}>
          Player
        </a>
        <a href="/create" style={{ color: "#888", textDecoration: "none", fontSize: "0.875rem" }}>
          Create
        </a>
        <a href="/admin" style={{ color: "#fafafa", textDecoration: "none", fontSize: "0.875rem" }}>
          Admin
        </a>
      </nav>
      <AdminScanPanel />
    </div>
  );
}
