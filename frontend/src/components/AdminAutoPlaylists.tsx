/**
 * AdminAutoPlaylists — CRUD for auto-playlists.
 */

import { useCallback, useEffect, useState } from "react";
import type { AutoPlaylist, AutoPlaylistDetail } from "../api/client";
import {
  fetchAutoPlaylists,
  fetchAutoPlaylist,
  createAutoPlaylist,
  updateAutoPlaylist,
  deleteAutoPlaylist,
} from "../api/client";

export default function AdminAutoPlaylists() {
  const [playlists, setPlaylists] = useState<AutoPlaylist[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<AutoPlaylistDetail | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchAutoPlaylists();
      setPlaylists(data);
    } catch {
      // Auth handled by client
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSelect = useCallback(async (id: number) => {
    setSelectedId(id);
    try {
      const d = await fetchAutoPlaylist(id);
      setDetail(d);
    } catch {
      setDetail(null);
    }
  }, []);

  const handleSetDefault = useCallback(
    async (id: number, isDefault: boolean) => {
      try {
        await updateAutoPlaylist(id, { is_default: !isDefault });
        await load();
        if (selectedId === id) {
          const d = await fetchAutoPlaylist(id);
          setDetail(d);
        }
        setToast(isDefault ? "Removed as default" : "Set as default");
      } catch {
        // ignore
      } finally {
        setTimeout(() => setToast(null), 3000);
      }
    },
    [load, selectedId],
  );

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await deleteAutoPlaylist(id);
        setPlaylists((prev) => prev.filter((p) => p.id !== id));
        if (selectedId === id) {
          setSelectedId(null);
          setDetail(null);
        }
      } catch {
        // ignore
      }
    },
    [selectedId],
  );

  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await createAutoPlaylist({ name: newName.trim(), items: [] });
      setNewName("");
      setShowCreate(false);
      await load();
      setToast("Auto-playlist created");
    } catch {
      setToast("Failed to create");
    } finally {
      setCreating(false);
      setTimeout(() => setToast(null), 3000);
    }
  }, [newName, load]);

  if (loading) {
    return (
      <div style={{ padding: "1.5rem" }}>
        <h2 style={{ marginBottom: "1.5rem" }}>Auto-Playlists</h2>
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
        <h2 style={{ margin: 0 }}>Auto-Playlists</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{
            padding: "0.5rem 1rem",
            fontSize: "0.75rem",
            fontWeight: 600,
            border: "1px solid #fafafa",
            borderRadius: "0.375rem",
            backgroundColor: "transparent",
            color: "#fafafa",
            cursor: "pointer",
          }}
        >
          + New
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div
          style={{
            padding: "1rem",
            marginBottom: "1rem",
            backgroundColor: "#141414",
            border: "1px solid #222",
            borderRadius: "0.75rem",
            display: "flex",
            gap: "0.5rem",
          }}
        >
          <input
            type="text"
            placeholder="Playlist name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            style={{
              flex: 1,
              padding: "0.5rem 0.75rem",
              fontSize: "0.8125rem",
              backgroundColor: "#111",
              border: "1px solid #333",
              borderRadius: "0.375rem",
              color: "#fafafa",
              outline: "none",
            }}
          />
          <button
            onClick={handleCreate}
            disabled={!newName.trim() || creating}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "0.75rem",
              fontWeight: 600,
              border: "none",
              borderRadius: "0.375rem",
              backgroundColor: newName.trim() ? "#fafafa" : "#333",
              color: newName.trim() ? "#0f0f0f" : "#666",
              cursor: newName.trim() ? "pointer" : "not-allowed",
            }}
          >
            {creating ? "Creating…" : "Create"}
          </button>
        </div>
      )}

      {/* Playlist list */}
      {playlists.length === 0 && !showCreate ? (
        <div style={{ textAlign: "center", padding: "2rem", color: "#444" }}>
          <p>No auto-playlists yet</p>
          <p style={{ fontSize: "0.75rem" }}>
            Create one to use as the default idle behavior
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {playlists.map((pl) => (
            <div
              key={pl.id}
              onClick={() => handleSelect(pl.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                padding: "0.75rem 1rem",
                backgroundColor:
                  selectedId === pl.id ? "#1a1a2e" : "#141414",
                border: `1px solid ${selectedId === pl.id ? "#333" : "#222"}`,
                borderRadius: "0.5rem",
                cursor: "pointer",
              }}
            >
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    color: "#fafafa",
                    fontWeight: 500,
                    fontSize: "0.875rem",
                  }}
                >
                  {pl.name}
                  {pl.is_default && (
                    <span
                      style={{
                        marginLeft: "0.5rem",
                        fontSize: "0.625rem",
                        padding: "0.125rem 0.5rem",
                        backgroundColor: "rgba(34, 197, 94, 0.15)",
                        color: "#22c55e",
                        borderRadius: "1rem",
                        fontWeight: 600,
                      }}
                    >
                      DEFAULT
                    </span>
                  )}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "#666" }}>
                  {pl.item_count} track{pl.item_count !== 1 ? "s" : ""}
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleSetDefault(pl.id, pl.is_default);
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: pl.is_default ? "#22c55e" : "#555",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  padding: "0.25rem 0.5rem",
                }}
                title={pl.is_default ? "Remove as default" : "Set as default"}
              >
                {pl.is_default ? "★" : "☆"}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(pl.id);
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#666",
                  cursor: "pointer",
                  fontSize: "1rem",
                  padding: "0 0.25rem",
                }}
                title="Delete"
                aria-label="Delete playlist"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Detail panel */}
      {detail && (
        <div
          style={{
            marginTop: "1.5rem",
            padding: "1rem",
            backgroundColor: "#141414",
            border: "1px solid #222",
            borderRadius: "0.75rem",
          }}
        >
          <h3
            style={{
              fontSize: "0.875rem",
              fontWeight: 600,
              color: "#ccc",
              marginBottom: "0.75rem",
            }}
          >
            {detail.name} — {detail.item_count} items
          </h3>
          {detail.items.length === 0 ? (
            <p style={{ fontSize: "0.75rem", color: "#555" }}>
              Empty playlist. Add tracks via the playlist creator or API.
            </p>
          ) : (
            <div>
              {detail.items.map((item, idx) => (
                <div
                  key={item.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    padding: "0.375rem 0.5rem",
                    borderBottom: "1px solid #1a1a1a",
                    fontSize: "0.75rem",
                  }}
                >
                  <span style={{ color: "#555", minWidth: "1.5rem" }}>
                    {idx + 1}.
                  </span>
                  <span style={{ color: "#888" }}>
                    Track #{item.track_id || "—"}
                  </span>
                  {item.jingle_id && (
                    <span style={{ color: "#f59e0b" }}>
                      Jingle #{item.jingle_id}
                    </span>
                  )}
                  {item.overlay_at_ms && (
                    <span style={{ color: "#555" }}>
                      @ {item.overlay_at_ms}ms
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
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
