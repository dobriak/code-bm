/**
 * NowPlaying — full-bleed album art with prev/next strip and controls.
 * Subscribes to /ws/now-playing WebSocket for live updates.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { QueueTrack } from "../stores/nowPlayingStore";
import { useNowPlayingStore } from "../stores/nowPlayingStore";

const STREAM_URL = "http://localhost:8000/raidio.mp3";

function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "";
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

function formatRemainingTime(
  startedAt: string | null,
  durationMs: number | null,
  bufferOffsetMs: number,
): string | null {
  if (!startedAt || !durationMs) return null;

  const started = new Date(startedAt).getTime();
  const elapsed = Date.now() - started - bufferOffsetMs;
  const remaining = durationMs - elapsed;

  if (remaining <= 0) return null;

  const sec = Math.ceil(remaining / 1000);
  const min = Math.floor(sec / 60);
  const remSec = sec % 60;
  return `${min}:${remSec.toString().padStart(2, "0")}`;
}

function TrackChip({ track, label }: { track: QueueTrack; label: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        padding: "0.5rem 0.75rem",
        backgroundColor: "#1a1a1a",
        borderRadius: "0.5rem",
        minWidth: "200px",
        maxWidth: "300px",
      }}
    >
      <span style={{ fontSize: "0.625rem", color: "#555", textTransform: "uppercase", fontWeight: 600, flexShrink: 0 }}>
        {label}
      </span>
      <div style={{ overflow: "hidden" }}>
        <div style={{ fontSize: "0.8125rem", color: "#ccc", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {track.title || "Unknown"}
        </div>
        <div style={{ fontSize: "0.6875rem", color: "#666", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {track.artist || ""}
          {track.owner_label ? ` · ${track.owner_label}` : ""}
        </div>
      </div>
      {track.duration_ms && (
        <span style={{ fontSize: "0.6875rem", color: "#555", marginLeft: "auto", flexShrink: 0 }}>
          {formatDuration(track.duration_ms)}
        </span>
      )}
    </div>
  );
}

export default function NowPlaying() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [started, setStarted] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolume] = useState(0.75);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);

  const { current, prev, next, bufferOffsetMs, connected, setNowPlaying, setConnected } =
    useNowPlayingStore();

  // Remaining time computed every second
  const remainingTime = useMemo(() => {
    return formatRemainingTime(
      current?.started_at ?? null,
      current?.duration_ms ?? null,
      bufferOffsetMs,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.started_at, current?.duration_ms, bufferOffsetMs, now]);

  // Tick every second for remaining time countdown
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket connection for now-playing updates
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/now-playing`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setNowPlaying(data);
      } catch {
        // ignore parse errors
      }
    };

    return () => {
      ws.close();
    };
  }, [setNowPlaying, setConnected]);

  // Sync volume
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  const handleStart = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.play().then(() => {
      setStarted(true);
      setPlaying(true);
      setError(null);
    }).catch((err) => {
      setError(`Playback failed: ${err instanceof Error ? err.message : String(err)}`);
    });
  }, []);

  const handlePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (audio.paused) {
      audio.play().then(() => setPlaying(true)).catch(() => {});
    } else {
      audio.pause();
      setPlaying(false);
    }
  }, []);

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setVolume(parseFloat(e.target.value));
  }, []);

  const coverUrl = current?.cover_art_path
    ? `/api/v1/tracks/${current.track_id}/cover`
    : null;

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#0f0f0f",
        color: "#fafafa",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "1.5rem",
        position: "relative",
      }}
    >
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={STREAM_URL}
        crossOrigin="anonymous"
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onError={() => setError("Lost connection to stream")}
      />

      {/* Click-to-start overlay */}
      {!started && (
        <button
          onClick={handleStart}
          style={{
            padding: "1rem 2.5rem",
            fontSize: "1.25rem",
            fontWeight: 600,
            border: "2px solid #fafafa",
            borderRadius: "0.75rem",
            backgroundColor: "transparent",
            color: "#fafafa",
            cursor: "pointer",
            transition: "all 0.2s ease",
            zIndex: 10,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "#fafafa";
            e.currentTarget.style.color = "#0f0f0f";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "transparent";
            e.currentTarget.style.color = "#fafafa";
          }}
        >
          ▶ Click to Start Listening
        </button>
      )}

      {/* Error display */}
      {error && (
        <span style={{ color: "#ef4444", fontSize: "0.875rem" }}>{error}</span>
      )}

      {/* Album art */}
      <div
        style={{
          width: "min(80vw, 80vh, 500px)",
          height: "min(80vw, 80vh, 500px)",
          borderRadius: "1rem",
          overflow: "hidden",
          backgroundColor: "#1a1a1a",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
        }}
      >
        {coverUrl ? (
          <img
            src={coverUrl}
            alt="Album art"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <span style={{ fontSize: "4rem", opacity: 0.2 }}>♪</span>
        )}
      </div>

      {/* Track info */}
      {current ? (
        <div style={{ textAlign: "center", maxWidth: "500px" }}>
          <h2
            style={{
              margin: 0,
              fontSize: "1.5rem",
              fontWeight: 700,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {current.title || "Unknown Track"}
          </h2>
          <p style={{ margin: "0.25rem 0 0", color: "#888", fontSize: "1rem" }}>
            {current.artist || "Unknown Artist"}
            {current.album ? ` — ${current.album}` : ""}
          </p>
          {current.owner_label && (
            <p style={{ margin: "0.25rem 0 0", color: "#555", fontSize: "0.75rem" }}>
              via {current.owner_label}
            </p>
          )}
          {remainingTime && (
            <p style={{ margin: "0.5rem 0 0", color: "#555", fontSize: "0.875rem", fontVariantNumeric: "tabular-nums" }}>
              -{remainingTime}
            </p>
          )}
        </div>
      ) : (
        <div style={{ textAlign: "center" }}>
          <p style={{ color: "#555", fontSize: "1.125rem" }}>Nothing playing</p>
          <p style={{ color: "#333", fontSize: "0.8125rem" }}>
            Submit a playlist from the Create page
          </p>
        </div>
      )}

      {/* Prev strip */}
      {prev.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: "0.5rem",
            overflowX: "auto",
            maxWidth: "90vw",
            padding: "0.5rem 0",
          }}
        >
          {prev.map((t) => (
            <TrackChip key={t.id} track={t} label="prev" />
          ))}
        </div>
      )}

      {/* Next strip */}
      {next.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: "0.5rem",
            overflowX: "auto",
            maxWidth: "90vw",
            padding: "0.5rem 0",
          }}
        >
          {next.map((t) => (
            <TrackChip key={t.id} track={t} label="next" />
          ))}
        </div>
      )}

      {/* Local controls */}
      {started && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            padding: "0.75rem 1.5rem",
            backgroundColor: "#1a1a1a",
            borderRadius: "2rem",
          }}
        >
          <button
            onClick={handlePlayPause}
            aria-label={playing ? "Pause" : "Play"}
            title="Local pause only — does not affect broadcast"
            style={{
              width: "2.5rem",
              height: "2.5rem",
              borderRadius: "50%",
              border: "2px solid #fafafa",
              backgroundColor: "transparent",
              color: "#fafafa",
              cursor: "pointer",
              fontSize: "1rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {playing ? "⏸" : "▶"}
          </button>

          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              fontSize: "0.875rem",
              color: "#fafafa",
              opacity: 0.7,
            }}
            title="Local volume only — does not affect broadcast"
          >
            🔊
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={volume}
              onChange={handleVolumeChange}
              aria-label="Volume"
              style={{ width: "100px", accentColor: "#fafafa" }}
            />
          </label>

          {/* Connection indicator */}
          <span
            title={connected ? "Connected to server" : "Disconnected"}
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: connected ? "#22c55e" : "#ef4444",
            }}
          />
        </div>
      )}
    </div>
  );
}
