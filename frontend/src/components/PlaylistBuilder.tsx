/**
 * PlaylistBuilder — right pane of the /create page.
 * Two-pane drag-and-drop layout: left (track browser) → right (playlist).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useUserStore } from "../stores/userStore";
import { useTracks } from "../api/hooks";
import type { Track } from "../api/client";
import {
  fetchRandomTrack,
  submitPlaylist,
} from "../api/client";
import type { TracksQuery } from "../api/client";
import FilterSidebar from "./FilterSidebar";
import { TrackRow } from "./TrackTable";

// ── Types ─────────────────────────────────────────────────────────

interface PlaylistEntry {
  /** Unique key for dnd-kit */
  id: string;
  track_id: number | null;
  jingle_id: number | null;
  artist: string | null;
  title: string | null;
  album: string | null;
  duration_ms: number | null;
  overlay_at_ms: number | null;
}

// ── Sortable playlist item ────────────────────────────────────────

function SortablePlaylistItem({
  entry,
  onRemove,
}: {
  entry: PlaylistEntry;
  onRemove: (id: string) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: entry.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
    padding: "0.5rem 1rem",
    borderBottom: "1px solid #222",
    fontSize: "0.8125rem",
    cursor: "default",
    backgroundColor: "#111",
    borderRadius: "0.25rem",
    marginBottom: "0.25rem",
  };

  return (
    <div ref={setNodeRef} style={style}>
      <span
        {...attributes}
        {...listeners}
        style={{ cursor: "grab", color: "#555", fontSize: "0.75rem", flexShrink: 0 }}
      >
        ⠿
      </span>
      <div style={{ flex: 1, overflow: "hidden" }}>
        <div style={{ color: "#fafafa", fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {entry.title || "—"}
        </div>
        <div style={{ color: "#888", fontSize: "0.75rem", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {entry.artist || ""}{entry.album ? ` — ${entry.album}` : ""}
        </div>
      </div>
      {entry.duration_ms && (
        <span style={{ color: "#666", fontSize: "0.75rem", flexShrink: 0 }}>
          {Math.floor(entry.duration_ms / 60000)}:{String(Math.floor((entry.duration_ms % 60000) / 1000)).padStart(2, "0")}
        </span>
      )}
      <button
        onClick={() => onRemove(entry.id)}
        style={{
          background: "none",
          border: "none",
          color: "#ef4444",
          cursor: "pointer",
          fontSize: "1rem",
          padding: "0 0.25rem",
          flexShrink: 0,
        }}
        aria-label="Remove from playlist"
      >
        ×
      </button>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────

export default function PlaylistBuilder() {
  const label = useUserStore((s) => s.label);
  const [playlist, setPlaylist] = useState<PlaylistEntry[]>([]);
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Track browser state
  const [search, setSearch] = useState("");
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);
  const [selectedArtist, setSelectedArtist] = useState<string | null>(null);
  const [selectedAlbum, setSelectedAlbum] = useState<string | null>(null);
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");

  const query: TracksQuery = useMemo(
    () => ({
      q: search || undefined,
      genre: selectedGenre || undefined,
      artist: selectedArtist || undefined,
      album: selectedAlbum || undefined,
      year_from: yearFrom ? parseInt(yearFrom, 10) : undefined,
      year_to: yearTo ? parseInt(yearTo, 10) : undefined,
      limit: 50,
    }),
    [search, selectedGenre, selectedArtist, selectedAlbum, yearFrom, yearTo],
  );

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useTracks(query);

  const tracks = useMemo(() => {
    if (!data) return [];
    return data.pages.flatMap((page) => page.items);
  }, [data]);

  const total = data?.pages[0]?.total ?? 0;

  const clearFilters = useCallback(() => {
    setSelectedGenre(null);
    setSelectedArtist(null);
    setSelectedAlbum(null);
    setYearFrom("");
    setYearTo("");
  }, []);

  // dnd-kit sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );

  // IDs of tracks already in playlist (to dim them)
  const playlistTrackIds = useMemo(
    () => new Set(playlist.filter((e) => e.track_id).map((e) => e.track_id)),
    [playlist],
  );

  // Add a track from the browser
  const handleAddTrack = useCallback((track: Track) => {
    if (playlistTrackIds.has(track.id)) return;

    const entry: PlaylistEntry = {
      id: `track-${track.id}-${Date.now()}`,
      track_id: track.id,
      jingle_id: null,
      artist: track.artist,
      title: track.title,
      album: track.album,
      duration_ms: track.duration_ms,
      overlay_at_ms: null,
    };
    setPlaylist((prev) => [...prev, entry]);
  }, [playlistTrackIds]);

  // Remove an entry
  const handleRemove = useCallback((id: string) => {
    setPlaylist((prev) => prev.filter((e) => e.id !== id));
  }, []);

  // Reorder within playlist
  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    setPlaylist((prev) => {
      const oldIdx = prev.findIndex((e) => e.id === active.id);
      const newIdx = prev.findIndex((e) => e.id === over.id);
      if (oldIdx === -1 || newIdx === -1) return prev;
      return arrayMove(prev, oldIdx, newIdx);
    });
  }, []);

  // Feeling lucky
  const handleFeelingLucky = useCallback(async () => {
    try {
      const track = await fetchRandomTrack();
      if (!playlistTrackIds.has(track.id)) {
        const entry: PlaylistEntry = {
          id: `track-${track.id}-${Date.now()}`,
          track_id: track.id,
          jingle_id: null,
          artist: track.artist,
          title: track.title,
          album: track.album,
          duration_ms: track.duration_ms,
          overlay_at_ms: null,
        };
        setPlaylist((prev) => [...prev, entry]);
      }
    } catch (err) {
      console.error("Feeling lucky failed:", err);
    }
  }, [playlistTrackIds]);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // '/' focuses search
      if (e.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      // 'r' triggers Feeling Lucky (only when not in an input)
      if (e.key === "r" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA") {
        handleFeelingLucky();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleFeelingLucky]);

  // Save playlist to .raidio file
  const handleSave = useCallback(() => {
    if (playlist.length === 0) return;

    const data = {
      raidio_version: 1,
      name: name || "Untitled",
      notes: notes || "",
      items: playlist.map((e) => ({
        type: e.track_id ? "track" as const : "jingle" as const,
        id: e.track_id ?? e.jingle_id ?? 0,
        artist: e.artist,
        title: e.title,
        album: e.album,
        overlay_at_ms: e.overlay_at_ms,
      })),
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(name || "playlist").replace(/[^a-zA-Z0-9_-]/g, "_")}.raidio`;
    a.click();
    URL.revokeObjectURL(url);
    setToast("Playlist saved!");
    setTimeout(() => setToast(null), 3000);
  }, [playlist, name, notes]);

  // Load playlist from .raidio file
  const handleLoad = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".raidio,.json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const data = JSON.parse(text);

        if (!data.items || !Array.isArray(data.items)) {
          setToast("Invalid playlist file");
          setTimeout(() => setToast(null), 4000);
          return;
        }

        // Restore name and notes
        if (data.name) setName(data.name);
        if (data.notes) setNotes(data.notes);

        // Convert items back to playlist entries
        const loaded: PlaylistEntry[] = data.items.map(
          (item: { type?: string; id?: number; artist?: string | null; title?: string | null; album?: string | null; overlay_at_ms?: number | null }) => ({
            id: `${item.type || "track"}-${item.id || 0}-${Date.now()}-${Math.random()}`,
            track_id: item.type === "track" ? item.id ?? null : null,
            jingle_id: item.type === "jingle" ? item.id ?? null : null,
            artist: item.artist ?? null,
            title: item.title ?? null,
            album: item.album ?? null,
            duration_ms: null,
            overlay_at_ms: item.overlay_at_ms ?? null,
          }),
        );

        setPlaylist(loaded);
        setToast(`Loaded ${loaded.length} items`);
        setTimeout(() => setToast(null), 4000);
      } catch {
        setToast("Failed to parse playlist file");
        setTimeout(() => setToast(null), 4000);
      }
    };
    input.click();
  }, []);

  // Submit playlist
  const handleSubmit = useCallback(async () => {
    if (playlist.length === 0 || !name.trim()) return;

    setSubmitting(true);
    try {
      await submitPlaylist({
        name: name.trim(),
        notes: notes.trim() || undefined,
        items: playlist.map((e) => ({
          track_id: e.track_id,
          jingle_id: e.jingle_id,
          overlay_at_ms: e.overlay_at_ms,
        })),
        owner_label: label,
      });
      setPlaylist([]);
      setName("");
      setNotes("");
      setToast("Playlist sent to queue!");
    } catch (err) {
      setToast(`Failed: ${err instanceof Error ? err.message : "unknown error"}`);
    } finally {
      setSubmitting(false);
      setTimeout(() => setToast(null), 4000);
    }
  }, [playlist, name, notes, label]);

  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) fetchNextPage();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f0f0f", color: "#fafafa", display: "flex", flexDirection: "column" }}>
      {/* Nav */}
      <nav style={{ display: "flex", alignItems: "center", gap: "1.5rem", padding: "0.75rem 1.5rem", borderBottom: "1px solid #1a1a1a" }}>
        <a href="/" style={{ color: "#fafafa", textDecoration: "none", fontWeight: 700, fontSize: "1.125rem" }}>Raidio</a>
        <a href="/" style={{ color: "#888", textDecoration: "none", fontSize: "0.875rem" }}>Player</a>
        <a href="/create" style={{ color: "#fafafa", textDecoration: "none", fontSize: "0.875rem" }}>Create</a>
        <a href="/admin" style={{ color: "#888", textDecoration: "none", fontSize: "0.875rem" }}>Admin</a>
      </nav>

      {/* Search bar */}
      <div style={{ padding: "1rem 1.5rem", borderBottom: "1px solid #1a1a1a" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div style={{ flex: 1, position: "relative" }}>
            <span style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "#555" }}>🔍</span>
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search tracks, artists, albums… (/ to focus)"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: "100%",
                padding: "0.625rem 0.75rem 0.625rem 2.25rem",
                fontSize: "0.875rem",
                backgroundColor: "#111",
                border: "1px solid #333",
                borderRadius: "0.5rem",
                color: "#fafafa",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>
          <span style={{ fontSize: "0.8125rem", color: "#555", whiteSpace: "nowrap" }}>
            {total.toLocaleString()} tracks
          </span>
        </div>
      </div>

      {/* Two-pane layout */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Left pane: filters + track browser */}
        <FilterSidebar
          selectedGenre={selectedGenre}
          selectedArtist={selectedArtist}
          selectedAlbum={selectedAlbum}
          yearFrom={yearFrom}
          yearTo={yearTo}
          onGenreChange={setSelectedGenre}
          onArtistChange={setSelectedArtist}
          onAlbumChange={setSelectedAlbum}
          onYearFromChange={setYearFrom}
          onYearToChange={setYearTo}
          onClear={clearFilters}
        />

        {/* Track list (left, scrollable) */}
        <div style={{ flex: 1, overflow: "auto" }}>
          {tracks.map((track, index) => (
            <TrackRow
              key={track.id}
              index={index}
              track={track}
              inPlaylist={playlistTrackIds.has(track.id)}
              onDoubleClick={() => handleAddTrack(track)}
            />
          ))}
          {hasNextPage && (
            <button
              onClick={loadMore}
              disabled={isFetchingNextPage}
              style={{
                display: "block",
                width: "100%",
                padding: "0.75rem",
                background: "none",
                border: "none",
                color: "#888",
                cursor: isFetchingNextPage ? "wait" : "pointer",
                fontSize: "0.8125rem",
              }}
            >
              {isFetchingNextPage ? "Loading…" : "Load more"}
            </button>
          )}
        </div>

        {/* Divider */}
        <div style={{ width: "1px", backgroundColor: "#222" }} />

        {/* Right pane: playlist builder */}
        <div
          style={{
            width: "350px",
            minWidth: "300px",
            display: "flex",
            flexDirection: "column",
            borderLeft: "1px solid #222",
            backgroundColor: "#0a0a0a",
          }}
        >
          {/* Playlist header */}
          <div style={{ padding: "1rem", borderBottom: "1px solid #222" }}>
            <input
              type="text"
              placeholder="Playlist name (required)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                fontSize: "0.875rem",
                backgroundColor: "#111",
                border: "1px solid #333",
                borderRadius: "0.375rem",
                color: "#fafafa",
                outline: "none",
                marginBottom: "0.5rem",
                boxSizing: "border-box",
              }}
            />
            <input
              type="text"
              placeholder="Notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                fontSize: "0.8125rem",
                backgroundColor: "#111",
                border: "1px solid #333",
                borderRadius: "0.375rem",
                color: "#fafafa",
                outline: "none",
                marginBottom: "0.5rem",
                boxSizing: "border-box",
              }}
            />
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                onClick={handleFeelingLucky}
                style={{
                  flex: 1,
                  padding: "0.5rem",
                  fontSize: "0.75rem",
                  border: "1px solid #333",
                  borderRadius: "0.375rem",
                  backgroundColor: "transparent",
                  color: "#ccc",
                  cursor: "pointer",
                }}
              >
                🎲 Feeling Lucky
              </button>
              <button
                onClick={handleSubmit}
                disabled={playlist.length === 0 || !name.trim() || submitting}
                style={{
                  flex: 1,
                  padding: "0.5rem",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  border: playlist.length > 0 && name.trim() ? "2px solid #22c55e" : "1px solid #333",
                  borderRadius: "0.375rem",
                  backgroundColor: playlist.length > 0 && name.trim() ? "transparent" : "transparent",
                  color: playlist.length > 0 && name.trim() ? "#22c55e" : "#555",
                  cursor: playlist.length > 0 && name.trim() ? "pointer" : "not-allowed",
                }}
              >
                {submitting ? "Sending…" : "Send to Queue"}
              </button>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.375rem" }}>
              <button
                onClick={handleSave}
                disabled={playlist.length === 0}
                style={{
                  flex: 1,
                  padding: "0.375rem",
                  fontSize: "0.6875rem",
                  border: "1px solid #333",
                  borderRadius: "0.375rem",
                  backgroundColor: "transparent",
                  color: playlist.length > 0 ? "#aaa" : "#444",
                  cursor: playlist.length > 0 ? "pointer" : "not-allowed",
                }}
              >
                💾 Save
              </button>
              <button
                onClick={handleLoad}
                style={{
                  flex: 1,
                  padding: "0.375rem",
                  fontSize: "0.6875rem",
                  border: "1px solid #333",
                  borderRadius: "0.375rem",
                  backgroundColor: "transparent",
                  color: "#aaa",
                  cursor: "pointer",
                }}
              >
                📂 Load
              </button>
            </div>
            <p style={{ fontSize: "0.6875rem", color: "#444", margin: "0.5rem 0 0" }}>
              Double-click a track to add it · Drag to reorder · <kbd style={{ fontSize: "0.625rem", background: "#222", padding: "0 0.25rem", borderRadius: "2px" }}>/</kbd> search · <kbd style={{ fontSize: "0.625rem", background: "#222", padding: "0 0.25rem", borderRadius: "2px" }}>r</kbd> lucky
            </p>
          </div>

          {/* Playlist items */}
          <div style={{ flex: 1, overflow: "auto", padding: "0.5rem" }}>
            {playlist.length === 0 && (
              <div style={{ textAlign: "center", padding: "2rem 1rem", color: "#444" }}>
                <p style={{ fontSize: "0.875rem" }}>Your playlist is empty</p>
                <p style={{ fontSize: "0.75rem", marginTop: "0.25rem" }}>
                  Double-click tracks from the list to add them
                </p>
              </div>
            )}

            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={playlist.map((e) => e.id)}
                strategy={verticalListSortingStrategy}
              >
                {playlist.map((entry) => (
                  <SortablePlaylistItem
                    key={entry.id}
                    entry={entry}
                    onRemove={handleRemove}
                  />
                ))}
              </SortableContext>
            </DndContext>
          </div>

          {/* Playlist footer */}
          {playlist.length > 0 && (
            <div style={{ padding: "0.75rem 1rem", borderTop: "1px solid #222", fontSize: "0.75rem", color: "#666" }}>
              {playlist.length} track{playlist.length !== 1 ? "s" : ""}
              {(() => {
                const totalMs = playlist.reduce((sum, e) => sum + (e.duration_ms || 0), 0);
                const min = Math.floor(totalMs / 60000);
                return min > 0 ? ` · ~${min} min` : "";
              })()}
            </div>
          )}
        </div>
      </div>

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
            boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
          }}
        >
          {toast}
        </div>
      )}
    </div>
  );
}
