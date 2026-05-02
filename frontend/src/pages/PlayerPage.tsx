/**
 * Player page — shows audio player and now-playing.
 */
import PlayerAudio from "../components/PlayerAudio";

export default function PlayerPage() {
  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f0f0f", color: "#fafafa", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "2rem" }}>
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

      <h1 style={{ fontSize: "3rem", fontWeight: 700, letterSpacing: "-0.02em" }}>
        Raidio
      </h1>

      <PlayerAudio />
    </div>
  );
}
