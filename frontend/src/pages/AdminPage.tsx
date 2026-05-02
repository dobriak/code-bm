/**
 * Admin page — tabbed admin console with auth gating.
 * Tabs: Dashboard, Scanner, Queue, Settings, Auto-Playlists.
 * Requires admin JWT; redirects to /admin/login if not authenticated.
 */

import { useCallback, useState } from "react";
import { useAdminAuthStore } from "../stores/adminAuthStore";
import AdminScanPanel from "../components/AdminScanPanel";
import AdminDashboard from "../components/AdminDashboard";
import AdminSettings from "../components/AdminSettings";
import AdminQueue from "../components/AdminQueue";
import AdminAutoPlaylists from "../components/AdminAutoPlaylists";

type Tab = "dashboard" | "scanner" | "queue" | "settings" | "auto-playlists";

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: "dashboard", label: "Dashboard", icon: "📊" },
  { key: "scanner", label: "Scanner", icon: "📀" },
  { key: "queue", label: "Queue", icon: "📋" },
  { key: "settings", label: "Settings", icon: "⚙️" },
  { key: "auto-playlists", label: "Auto-Playlists", icon: "🎵" },
];

export default function AdminPage() {
  const jwt = useAdminAuthStore((s) => s.jwt);
  const clearJwt = useAdminAuthStore((s) => s.clearJwt);
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  // Auth gate: if no JWT, redirect to login
  if (!jwt) {
    // Use window.location for redirect
    if (typeof window !== "undefined") {
      window.location.href = "/admin/login";
    }
    return (
      <div style={{ minHeight: "100vh", backgroundColor: "#0f0f0f", color: "#fafafa", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: "#666" }}>Redirecting to login…</p>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f0f0f", color: "#fafafa" }}>
      {/* Nav */}
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
        <div style={{ flex: 1 }} />
        <button
          onClick={() => {
            clearJwt();
            window.location.href = "/admin/login";
          }}
          style={{
            background: "none",
            border: "1px solid #333",
            borderRadius: "0.375rem",
            color: "#888",
            fontSize: "0.75rem",
            padding: "0.375rem 0.75rem",
            cursor: "pointer",
          }}
        >
          Logout
        </button>
      </nav>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: "0",
          borderBottom: "1px solid #1a1a1a",
          padding: "0 1.5rem",
        }}
      >
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: "0.75rem 1rem",
              fontSize: "0.8125rem",
              fontWeight: 500,
              border: "none",
              borderBottom:
                activeTab === tab.key ? "2px solid #fafafa" : "2px solid transparent",
              backgroundColor: "transparent",
              color: activeTab === tab.key ? "#fafafa" : "#666",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ overflow: "auto" }}>
        {activeTab === "dashboard" && <AdminDashboard />}
        {activeTab === "scanner" && <AdminScanPanel />}
        {activeTab === "queue" && <AdminQueue />}
        {activeTab === "settings" && <AdminSettings />}
        {activeTab === "auto-playlists" && <AdminAutoPlaylists />}
      </div>
    </div>
  );
}
