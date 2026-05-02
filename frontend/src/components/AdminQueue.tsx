/**
 * AdminQueue — live queue management UI.
 * Shows pending items, skip current, delete pending, insert jingles.
 */

import { useCallback, useEffect, useState } from "react";
import type { QueueItem, Jingle } from "../api/client";
import {
  fetchQueue,
  skipCurrentTrack,
  deleteQueueItem,
  insertJingle,
  fetchJingles,
} from "../api/client";

export default function AdminQueue() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [jingles, setJingles] = useState<Jingle[]>([]);
  const [loading, setLoading] = useState(true);
  const [skipping, setSkipping] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [queueData, jingleData] = await Promise.all([
        fetchQueue(),
        fetchJingles(),
      ]);
      setItems(queueData.items);
      setJingles(jingleData);
    } catch {
      // Auth errors handled by client
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  const handleSkip = useCallback(async () => {
    setSkipping(true);
    try {
      await skipCurrentTrack();
      setToast("Skipped current track");
      setTimeout(load, 1000);
    } catch {
      setToast("Failed to skip");
    } finally {
      setSkipping(false);
      setTimeout(() => setToast(null), 3000);
    }
  }, [load]);

  const handleDelete = useCallback(
    async (itemId: number) => {
      try {
        await deleteQueueItem(itemId);
        setItems((prev) => prev.filter((i) => i.id !== itemId));
      } catch {
        // ignore
      }
    },
    [],
  );

  const handleInsertJingle = useCallback(async (jingleId: number) => {
    try {
      await insertJingle(jingleId);
      setToast("Jingle inserted!");
    } catch {
      setToast("Failed to insert jingle");
    } finally {
      setTimeout(() => setToast(null), 3000);
    }
  }, []);

  const current = items.find((i) => i.state === "playing");
  const pending = items.filter((i) => i.state === "pending");
  const played = items.filter(
    (i) => i.state === "played" || i.state === "skipped",
  );

  if (loading) {
    return (
      <div style={{ padding: "1.5rem" }}>
        <h2 style={{ marginBottom: "1.5rem" }}>Queue</h2>
        <div style={{ color: "#666" }}>Loading…</div>
      </div>
    );
  }

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
        <h2 style={{ margin: 0 }}>Queue</h2>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            onClick={handleSkip}
            disabled={skipping || !current}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "0.75rem",
              fontWeight: 600,
              border: current ? "1px solid #ef4444" : "1px solid #333",
              borderRadius: "0.375rem",
              backgroundColor: "transparent",
              color: current ? "#ef4444" : "#555",
              cursor: current ? "pointer" : "not-allowed",
            }}
          >
            {skipping ? "Skipping…" : "⏭ Skip Current"}
          </button>

          {jingles.length > 0 && (
            <select
              defaultValue=""
              onChange={(e) => {
                if (e.target.value) {
                  handleInsertJingle(parseInt(e.target.value, 10));
                  e.target.value = "";
                }
              }}
              style={{
                padding: "0.5rem 0.75rem",
                fontSize: "0.75rem",
                backgroundColor: "#111",
                border: "1px solid #333",
                borderRadius: "0.375rem",
                color: "#fafafa",
                cursor: "pointer",
              }}
            >
              <option value="" disabled>
                🔔 Insert Jingle…
              </option>
              {jingles.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title || j.path}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Currently playing */}
      {current && (
        <div
          style={{
            padding: "1rem",
            marginBottom: "1rem",
            backgroundColor: "rgba(34, 197, 94, 0.05)",
            border: "1px solid rgba(34, 197, 94, 0.2)",
            borderRadius: "0.75rem",
          }}
        >
          <div
            style={{
              fontSize: "0.625rem",
              textTransform: "uppercase",
              color: "#22c55e",
              fontWeight: 600,
              marginBottom: "0.375rem",
            }}
          >
            ▶ Now Playing
          </div>
          <div style={{ color: "#fafafa", fontWeight: 500 }}>
            {current.title || "Unknown"}
          </div>
          <div style={{ fontSize: "0.8125rem", color: "#888" }}>
            {current.artist || ""}
            {current.owner_label ? ` · via ${current.owner_label}` : ""}
          </div>
        </div>
      )}

      {/* Pending queue */}
      {pending.length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <h3
            style={{
              fontSize: "0.75rem",
              textTransform: "uppercase",
              color: "#666",
              fontWeight: 600,
              marginBottom: "0.75rem",
            }}
          >
            Up Next ({pending.length})
          </h3>
          {pending.map((item) => (
            <div
              key={item.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                padding: "0.5rem 0.75rem",
                borderBottom: "1px solid #1a1a1a",
                fontSize: "0.8125rem",
              }}
            >
              <div style={{ flex: 1, overflow: "hidden" }}>
                <div
                  style={{
                    color: "#ccc",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {item.title || "—"}
                </div>
                <div
                  style={{
                    fontSize: "0.6875rem",
                    color: "#666",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {item.artist || ""}
                  {item.owner_label ? ` · via ${item.owner_label}` : ""}
                </div>
              </div>
              {item.duration_ms && (
                <span style={{ color: "#555", fontSize: "0.75rem", flexShrink: 0 }}>
                  {Math.floor(item.duration_ms / 60000)}:
                  {String(Math.floor((item.duration_ms % 60000) / 1000)).padStart(2, "0")}
                </span>
              )}
              <button
                onClick={() => handleDelete(item.id)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#666",
                  cursor: "pointer",
                  fontSize: "1rem",
                  padding: "0 0.25rem",
                  flexShrink: 0,
                }}
                title="Remove from queue"
                aria-label="Remove from queue"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {items.length === 0 && (
        <div style={{ textAlign: "center", padding: "2rem", color: "#444" }}>
          <p>Queue is empty</p>
          <p style={{ fontSize: "0.75rem" }}>
            Submit playlists from the Create page or let the idle behavior play
          </p>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: "1.5rem",
            left: "50%",
            transform: "translateX(-50%)",
            padding: "0.75rem 1.5rem",
            backgroundColor: "#22c55e",
            color: "#0f0f0f",
            borderRadius: "0.5rem",
            fontSize: "0.875rem",
            fontWeight: 600,
            zIndex: 100,
          }}
        >
          {toast}
        </div>
      )}
    </div>
  );
}
