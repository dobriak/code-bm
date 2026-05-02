import { useState, useCallback, useRef, useEffect } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  useTracks, Track, useJingles, Jingle, useRandomTrack,
  savePlaylist, parsePlaylistFile, resolvePaths, RaidioPlaylist,
} from "../api/tracks";
import { useUserStore } from "../stores/userStore";

interface PlaylistItem {
  id: string;
  type: "track" | "jingle";
  trackId?: number;
  jingleId?: number;
  title: string;
  artist?: string;
  duration_ms?: number | null;
  overlay_at_ms?: number;
  path?: string;
}

function SortablePlaylistItem({
  item,
  onRemove,
}: {
  item: PlaylistItem;
  onRemove: (id: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: item.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const duration = item.duration_ms
    ? `${Math.floor(item.duration_ms / 60000)}:${String(Math.floor((item.duration_ms % 60000) / 1000)).padStart(2, "0")}`
    : "--:--";

  return (
    <div ref={setNodeRef} style={style} className="playlist-item" {...attributes} {...listeners}>
      <span className="drag-handle">::</span>
      <span className="item-title">
        {item.title}
        {item.artist && <span className="item-artist"> - {item.artist}</span>}
      </span>
      <span className="item-duration">{duration}</span>
      <button
        type="button"
        className="remove-btn"
        onClick={() => onRemove(item.id)}
      >
        ×
      </button>
    </div>
  );
}

export function PlaylistBuilder() {
  const [searchQuery, setSearchQuery] = useState("");
  const [playlistName, setPlaylistName] = useState("");
  const [playlistNotes, setPlaylistNotes] = useState("");
  const [playlistItems, setPlaylistItems] = useState<PlaylistItem[]>([]);
  const [showJingles, setShowJingles] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { userLabel } = useUserStore();
  const { data: tracksData, isLoading: tracksLoading } = useTracks({ q: searchQuery || undefined });
  const { data: jinglesData } = useJingles();
  const { data: randomTrack } = useRandomTrack();

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  }, []);

  const handleSave = useCallback(() => {
    if (!playlistName.trim()) {
      showToast("Please enter a playlist name to save");
      return;
    }
    if (playlistItems.length === 0) {
      showToast("Add items before saving");
      return;
    }
    const playlist: RaidioPlaylist = {
      raidio_version: 1,
      name: playlistName.trim(),
      notes: playlistNotes.trim() || undefined,
      items: playlistItems.map((item) => ({
        type: item.type,
        path: item.path ?? "",
        overlay_at_ms: item.overlay_at_ms,
      })),
    };
    savePlaylist(playlist);
    showToast("Playlist saved!");
  }, [playlistName, playlistNotes, playlistItems, showToast]);

  const handleLoad = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const parsed = await parsePlaylistFile(file);
      const items = parsed.items.map((item) => ({ path: item.path, type: item.type as "track" | "jingle" }));
      const result = await resolvePaths(items);
      if (result.resolved.length === 0) {
        showToast("No tracks found in current library");
        return;
      }
      const loadedItems: PlaylistItem[] = result.resolved.map((r) => ({
        id: `${r.type}-${r.id}-${Date.now()}-${Math.random()}`,
        type: r.type,
        trackId: r.type === "track" ? r.id : undefined,
        jingleId: r.type === "jingle" ? r.id : undefined,
        title: r.title || "Unknown",
        duration_ms: r.duration_ms,
        path: r.path,
      }));
      setPlaylistItems(loadedItems);
      setPlaylistName(parsed.name);
      setPlaylistNotes(parsed.notes || "");
      if (result.missing.length > 0) {
        showToast(`Loaded ${loadedItems.length} items; ${result.missing.length} not found`);
      } else {
        showToast(`Loaded ${loadedItems.length} items`);
      }
    } catch (err) {
      showToast(`Failed to load: ${err instanceof Error ? err.message : "unknown error"}`);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [showToast]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      setPlaylistItems((items) => {
        const oldIndex = items.findIndex((i) => i.id === active.id);
        const newIndex = items.findIndex((i) => i.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  }, []);

  const addTrackToPlaylist = useCallback((track: Track) => {
    const newItem: PlaylistItem = {
      id: `track-${track.id}-${Date.now()}`,
      type: "track",
      trackId: track.id,
      title: track.title || "Unknown Title",
      artist: track.artist || "Unknown Artist",
      duration_ms: track.duration_ms,
    };
    setPlaylistItems((prev) => [...prev, newItem]);
  }, []);

  const addJingleToPlaylist = useCallback((jingle: Jingle) => {
    const newItem: PlaylistItem = {
      id: `jingle-${jingle.id}-${Date.now()}`,
      type: "jingle",
      jingleId: jingle.id,
      title: jingle.title || "Jingle",
      duration_ms: jingle.duration_ms,
    };
    setPlaylistItems((prev) => [...prev, newItem]);
  }, []);

  const removeFromPlaylist = useCallback((id: string) => {
    setPlaylistItems((prev) => prev.filter((i) => i.id !== id));
  }, []);

  const handleFeelingLucky = useCallback(() => {
    if (randomTrack) {
      addTrackToPlaylist(randomTrack);
    }
  }, [randomTrack, addTrackToPlaylist]);

  const handleSendToQueue = useCallback(async () => {
    if (!playlistName.trim()) {
      setToastMessage("Please enter a playlist name");
      return;
    }
    if (playlistItems.length === 0) {
      setToastMessage("Please add at least one item to the playlist");
      return;
    }

    const body = {
      name: playlistName.trim(),
      notes: playlistNotes.trim() || undefined,
      items: playlistItems.map((item) => ({
        track_id: item.type === "track" ? item.trackId : undefined,
        jingle_id: item.type === "jingle" ? item.jingleId : undefined,
      })),
      owner_label: userLabel,
    };

    try {
      const res = await fetch("/api/v1/queue/playlists", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed to submit playlist");
      setToastMessage(`Queued as ${userLabel}!`);
      setPlaylistItems([]);
      setPlaylistName("");
      setPlaylistNotes("");
    } catch {
      setToastMessage("Failed to send playlist to queue");
    }
  }, [playlistName, playlistNotes, playlistItems, userLabel]);

  useEffect(() => {
    const handleKeydown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;
      if (e.key === "/") {
        e.preventDefault();
        document.querySelector<HTMLInputElement>(".search-box input")?.focus();
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        handleFeelingLucky();
      }
    };
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, [handleFeelingLucky]);

  const totalDuration = playlistItems.reduce((sum, item) => {
    return sum + (item.duration_ms || 0);
  }, 0);
  const totalFormatted = `${Math.floor(totalDuration / 60000)}:${String(Math.floor((totalDuration % 60000) / 1000)).padStart(2, "0")}`;

  return (
    <div className="playlist-creator">
      <div className="creator-left-pane">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search tracks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="content-tabs">
          <button
            className={!showJingles ? "active" : ""}
            onClick={() => setShowJingles(false)}
          >
            Tracks
          </button>
          <button
            className={showJingles ? "active" : ""}
            onClick={() => setShowJingles(true)}
          >
            Jingles
          </button>
        </div>

        {!showJingles ? (
          <div className="track-list">
            {tracksLoading ? (
              <div className="loading">Loading...</div>
            ) : tracksData?.tracks?.length === 0 ? (
              <div className="empty">No tracks found</div>
            ) : (
              tracksData?.tracks?.map((track: Track) => (
                <div
                  key={track.id}
                  className="track-row"
                  onClick={() => addTrackToPlaylist(track)}
                >
                  <span className="track-title">{track.title || "Unknown"}</span>
                  <span className="track-artist">{track.artist || "Unknown"}</span>
                  <span className="track-duration">
                    {track.duration_ms
                      ? `${Math.floor(track.duration_ms / 60000)}:${String(Math.floor((track.duration_ms % 60000) / 1000)).padStart(2, "0")}`
                      : "--:--"}
                  </span>
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="jingle-list">
            {jinglesData?.jingles?.map((jingle: Jingle) => (
              <div
                key={jingle.id}
                className="jingle-row"
                onClick={() => addJingleToPlaylist(jingle)}
              >
                <span className="jingle-title">{jingle.title || "Jingle"}</span>
                <span className="jingle-duration">
                  {jingle.duration_ms
                    ? `${Math.floor(jingle.duration_ms / 60000)}:${String(Math.floor((jingle.duration_ms % 60000) / 1000)).padStart(2, "0")}`
                    : "--:--"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="creator-right-pane">
        <div className="playlist-header">
          <input
            type="text"
            placeholder="Playlist name (required)"
            value={playlistName}
            onChange={(e) => setPlaylistName(e.target.value)}
            maxLength={80}
          />
          <textarea
            placeholder="Notes (optional)"
            value={playlistNotes}
            onChange={(e) => setPlaylistNotes(e.target.value)}
            maxLength={500}
          />
        </div>

        <div className="playlist-actions">
          <button onClick={handleFeelingLucky} className="lucky-btn">
            Feeling Lucky
          </button>
          <button onClick={() => fileInputRef.current?.click()} className="load-btn">
            Load
          </button>
          <button onClick={handleSave} className="save-btn">
            Save
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".raidio"
            style={{ display: "none" }}
            onChange={handleLoad}
          />
        </div>

        <div className="playlist-items">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={playlistItems.map((i) => i.id)}
              strategy={verticalListSortingStrategy}
            >
              {playlistItems.map((item) => (
                <SortablePlaylistItem
                  key={item.id}
                  item={item}
                  onRemove={removeFromPlaylist}
                />
              ))}
            </SortableContext>
          </DndContext>

          {playlistItems.length === 0 && (
            <div className="empty-playlist">
              Drag tracks here to build your playlist
            </div>
          )}
        </div>

        <div className="playlist-footer">
          <div className="playlist-stats">
            <span>{playlistItems.length} items</span>
            <span>Total: {totalFormatted}</span>
          </div>
          <button onClick={handleSendToQueue} className="send-btn">
            Send to Queue
          </button>
        </div>
      </div>

      {toastMessage && (
        <div className="toast" onClick={() => setToastMessage(null)}>
          {toastMessage}
        </div>
      )}
    </div>
  );
}