/**
 * AdminDashboard — stats overview for the admin console.
 */

import { useQuery } from "@tanstack/react-query";
import type { AdminStats } from "../api/client";
import { fetchAdminStats } from "../api/client";

function formatDuration(ms: number): string {
  const hours = Math.floor(ms / 3_600_000);
  const minutes = Math.floor((ms % 3_600_000) / 60_000);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export default function AdminDashboard() {
  const { data, isLoading, error, refetch } = useQuery<AdminStats>({
    queryKey: ["admin-stats"],
    queryFn: fetchAdminStats,
    refetchInterval: 10000,
  });

  if (isLoading) {
    return (
      <div style={{ padding: "1.5rem" }}>
        <h2 style={{ marginBottom: "1.5rem" }}>Dashboard</h2>
        <div style={{ color: "#666" }}>Loading stats…</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: "1.5rem" }}>
        <h2 style={{ marginBottom: "1.5rem" }}>Dashboard</h2>
        <div style={{ color: "#ef4444" }}>
          Failed to load stats
          <button
            onClick={() => refetch()}
            style={{
              marginLeft: "1rem",
              background: "none",
              border: "1px solid #ef4444",
              color: "#ef4444",
              padding: "0.25rem 0.75rem",
              borderRadius: "0.375rem",
              cursor: "pointer",
              fontSize: "0.75rem",
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const statusColor =
    data.broadcast_status === "playing" ? "#22c55e" : "#666";
  const statusLabel =
    data.broadcast_status === "playing" ? "● On Air" : "○ Idle";

  return (
    <div style={{ padding: "1.5rem", maxWidth: "800px", margin: "0 auto" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "1.5rem",
        }}
      >
        <h2 style={{ margin: 0 }}>Dashboard</h2>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            fontSize: "0.875rem",
            color: statusColor,
            fontWeight: 600,
          }}
        >
          {statusLabel}
        </span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: "1rem",
        }}
      >
        <StatCard label="Tracks" value={data.track_count.toLocaleString()} />
        <StatCard label="Artists" value={data.artist_count.toLocaleString()} />
        <StatCard label="Albums" value={data.album_count.toLocaleString()} />
        <StatCard label="Genres" value={data.genre_count.toLocaleString()} />
        <StatCard label="Total Playtime" value={formatDuration(data.total_playtime_ms)} />
        <StatCard label="Queue Length" value={String(data.queue_length)} />
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        padding: "1rem",
        backgroundColor: "#141414",
        border: "1px solid #222",
        borderRadius: "0.75rem",
      }}
    >
      <div
        style={{
          fontSize: "0.6875rem",
          textTransform: "uppercase",
          color: "#666",
          fontWeight: 600,
          letterSpacing: "0.05em",
          marginBottom: "0.375rem",
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{value}</div>
    </div>
  );
}
