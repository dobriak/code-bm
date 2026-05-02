import { useAdminStats } from "../api/admin";

export function AdminDashboard() {
  const { data, isLoading, error } = useAdminStats();

  if (isLoading) return <div className="loading">Loading stats...</div>;
  if (error) return <div className="error">Failed to load stats</div>;
  if (!data) return null;

  const playtimeHours = Math.round((data.total_playtime_ms || 0) / 1000 / 60 / 60 * 10) / 10;

  return (
    <div className="admin-dashboard">
      <h2>Dashboard</h2>
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{data.tracks ?? 0}</span>
          <span className="stat-label">Tracks</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{data.artists ?? 0}</span>
          <span className="stat-label">Artists</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{data.albums ?? 0}</span>
          <span className="stat-label">Albums</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{data.genres ?? 0}</span>
          <span className="stat-label">Genres</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{playtimeHours}</span>
          <span className="stat-label">Hours Playtime</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{data.jingles ?? 0}</span>
          <span className="stat-label">Jingles</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{data.queue_length ?? 0}</span>
          <span className="stat-label">Queue Length</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{data.broadcast_status}</span>
          <span className="stat-label">Broadcast</span>
        </div>
      </div>
    </div>
  );
}
