/**
 * Player page — full-bleed album art, now-playing, controls.
 */
import NowPlaying from "../components/NowPlaying";

export default function PlayerPage() {
  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f0f0f", color: "#fafafa" }}>
      <nav
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          display: "flex",
          alignItems: "center",
          gap: "1.5rem",
          padding: "0.75rem 1.5rem",
          borderBottom: "1px solid #1a1a1a",
          zIndex: 50,
        }}
      >
        <a href="/" style={{ color: "#fafafa", textDecoration: "none", fontWeight: 700, fontSize: "1.125rem" }}>
          Raidio
        </a>
        <a href="/" style={{ color: "#fafafa", textDecoration: "none", fontSize: "0.875rem" }}>
          Player
        </a>
        <a href="/create" style={{ color: "#888", textDecoration: "none", fontSize: "0.875rem" }}>
          Create
        </a>
        <a href="/admin" style={{ color: "#888", textDecoration: "none", fontSize: "0.875rem" }}>
          Admin
        </a>
      </nav>

      <NowPlaying />
    </div>
  );
}
