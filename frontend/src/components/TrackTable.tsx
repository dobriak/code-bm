import { useRef, useCallback } from "react";
import { Virtuoso } from "react-virtuoso";
import type { VirtuosoHandle } from "react-virtuoso";
import type { Track } from "../api/client";

interface TrackTableProps {
  tracks: Track[];
  total: number;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  onLoadMore: () => void;
}

export function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "";
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

function AnalysisBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "#f59e0b",
    running: "#3b82f6",
    done: "#22c55e",
    error: "#ef4444",
  };
  const color = colors[status] || "#555";

  return (
    <span
      style={{
        display: "inline-block",
        width: "6px",
        height: "6px",
        borderRadius: "50%",
        backgroundColor: color,
      }}
      title={status}
    />
  );
}

export function TrackRow({
  index,
  track,
  inPlaylist = false,
  onDoubleClick,
}: {
  index: number;
  track: Track;
  inPlaylist?: boolean;
  onDoubleClick?: () => void;
}) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "2rem 1fr 1fr 2fr 1fr 4rem 2rem",
        gap: "0.5rem",
        padding: "0.5rem 1rem",
        borderBottom: "1px solid #111",
        fontSize: "0.8125rem",
        cursor: onDoubleClick ? "pointer" : "default",
        alignItems: "center",
        opacity: inPlaylist ? 0.4 : 1,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = "#141414";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = "transparent";
      }}
      onDoubleClick={onDoubleClick}
      title={onDoubleClick ? "Double-click to add to playlist" : undefined}
    >
      <span style={{ color: "#555", fontSize: "0.75rem" }}>{index + 1}</span>
      <span
        style={{
          color: "#ccc",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
        title={track.artist ?? undefined}
      >
        {track.artist || "—"}
      </span>
      <span
        style={{
          color: "#999",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
        title={track.album ?? undefined}
      >
        {track.album || "—"}
      </span>
      <span
        style={{
          color: "#fafafa",
          fontWeight: 500,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
        title={track.title ?? undefined}
      >
        {track.title || "—"}
      </span>
      <span
        style={{
          color: "#888",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {track.genre || ""}
      </span>
      <span style={{ color: "#888", textAlign: "right", fontSize: "0.75rem" }}>
        {formatDuration(track.duration_ms)}
      </span>
      <span>
        <AnalysisBadge status={track.analysis_status} />
      </span>
    </div>
  );
}

export default function TrackTable({ tracks, total, hasNextPage, isFetchingNextPage, onLoadMore }: TrackTableProps) {
  const virtuosoRef = useRef<VirtuosoHandle>(null);

  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      onLoadMore();
    }
  }, [hasNextPage, isFetchingNextPage, onLoadMore]);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Header */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2rem 1fr 1fr 2fr 1fr 4rem 2rem",
          gap: "0.5rem",
          padding: "0.5rem 1rem",
          borderBottom: "1px solid #222",
          fontSize: "0.6875rem",
          textTransform: "uppercase",
          color: "#555",
          fontWeight: 600,
          letterSpacing: "0.05em",
          flexShrink: 0,
        }}
      >
        <span>#</span>
        <span>Artist</span>
        <span>Album</span>
        <span>Title</span>
        <span>Genre</span>
        <span style={{ textAlign: "right" }}>Duration</span>
        <span />
      </div>

      {/* Virtualized track list */}
      <Virtuoso
        ref={virtuosoRef}
        style={{ flex: 1 }}
        data={tracks}
        endReached={loadMore}
        increaseViewportBy={300}
        itemContent={(index, track) => (
          <TrackRow index={index} track={track} />
        )}
        components={{
          Footer: () =>
            isFetchingNextPage ? (
              <div style={{ padding: "1rem", textAlign: "center", color: "#555", fontSize: "0.75rem" }}>
                Loading more…
              </div>
            ) : null,
          EmptyPlaceholder: () => (
            <div style={{ padding: "3rem 1rem", textAlign: "center", color: "#444" }}>
              <p style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>No tracks found</p>
              <p style={{ fontSize: "0.8125rem" }}>
                {total === 0
                  ? "Scan your library first — go to Admin → Scanner"
                  : "Try adjusting your search or filters"}
              </p>
            </div>
          ),
        }}
      />
    </div>
  );
}
