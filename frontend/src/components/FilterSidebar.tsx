import { useCallback, useMemo, useState } from "react";
import { useGenres, useArtists, useAlbums } from "../api/hooks";
import { FacetItem } from "../api/client";

interface FilterSidebarProps {
  selectedGenre: string | null;
  selectedArtist: string | null;
  selectedAlbum: string | null;
  yearFrom: string;
  yearTo: string;
  onGenreChange: (genre: string | null) => void;
  onArtistChange: (artist: string | null) => void;
  onAlbumChange: (album: string | null) => void;
  onYearFromChange: (year: string) => void;
  onYearToChange: (year: string) => void;
  onClear: () => void;
}

export default function FilterSidebar({
  selectedGenre,
  selectedArtist,
  selectedAlbum,
  yearFrom,
  yearTo,
  onGenreChange,
  onArtistChange,
  onAlbumChange,
  onYearFromChange,
  onYearToChange,
  onClear,
}: FilterSidebarProps) {
  const { data: genres } = useGenres();
  const { data: artists } = useArtists();
  const { data: albums } = useAlbums();

  const hasFilters = selectedGenre || selectedArtist || selectedAlbum || yearFrom || yearTo;

  const facetStyle: React.CSSProperties = {
    maxHeight: "200px",
    overflowY: "auto",
    marginBottom: "1rem",
  };

  return (
    <div
      style={{
        width: "240px",
        minWidth: "240px",
        borderRight: "1px solid #222",
        padding: "1rem",
        overflowY: "auto",
        backgroundColor: "#0a0a0a",
      }}
    >
      <h3 style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "#666", marginBottom: "0.75rem" }}>
        Filters
      </h3>

      {hasFilters && (
        <button
          onClick={onClear}
          style={{
            fontSize: "0.75rem",
            color: "#f59e0b",
            background: "none",
            border: "none",
            cursor: "pointer",
            marginBottom: "0.75rem",
            padding: 0,
          }}
        >
          ✕ Clear all
        </button>
      )}

      <FacetSection
        title="Genres"
        items={genres ?? []}
        selected={selectedGenre}
        onSelect={onGenreChange}
        style={facetStyle}
      />

      <FacetSection
        title="Artists"
        items={artists ?? []}
        selected={selectedArtist}
        onSelect={onArtistChange}
        style={facetStyle}
      />

      <FacetSection
        title="Albums"
        items={albums ?? []}
        selected={selectedAlbum}
        onSelect={onAlbumChange}
        style={facetStyle}
      />

      <h4 style={{ fontSize: "0.75rem", color: "#666", marginBottom: "0.5rem" }}>Year Range</h4>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
        <input
          type="number"
          placeholder="From"
          value={yearFrom}
          onChange={(e) => onYearFromChange(e.target.value)}
          style={inputStyle}
          min={0}
          max={9999}
        />
        <input
          type="number"
          placeholder="To"
          value={yearTo}
          onChange={(e) => onYearToChange(e.target.value)}
          style={inputStyle}
          min={0}
          max={9999}
        />
      </div>
    </div>
  );
}

function FacetSection({
  title,
  items,
  selected,
  onSelect,
  style,
}: {
  title: string;
  items: FacetItem[];
  selected: string | null;
  onSelect: (value: string | null) => void;
  style: React.CSSProperties;
}) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div style={style}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          background: "none",
          border: "none",
          color: "#ccc",
          cursor: "pointer",
          fontSize: "0.8125rem",
          fontWeight: 600,
          width: "100%",
          textAlign: "left",
          padding: "0.25rem 0",
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        {title}
        <span style={{ fontSize: "0.75rem", color: "#555" }}>{expanded ? "▾" : "▸"}</span>
      </button>
      {expanded && (
        <div style={{ maxHeight: "150px", overflowY: "auto" }}>
          {items.slice(0, 50).map((item) => (
            <button
              key={item.name}
              onClick={() => onSelect(selected === item.name ? null : item.name)}
              style={{
                display: "flex",
                justifyContent: "space-between",
                width: "100%",
                background: selected === item.name ? "#1a3a5c" : "none",
                border: "none",
                color: selected === item.name ? "#60a5fa" : "#aaa",
                cursor: "pointer",
                fontSize: "0.75rem",
                padding: "0.2rem 0.25rem",
                borderRadius: "2px",
              }}
            >
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {item.name}
              </span>
              <span style={{ color: "#555", marginLeft: "0.5rem", flexShrink: 0 }}>{item.count}</span>
            </button>
          ))}
          {items.length === 0 && (
            <span style={{ fontSize: "0.75rem", color: "#444" }}>No data</span>
          )}
        </div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.375rem 0.5rem",
  fontSize: "0.75rem",
  backgroundColor: "#111",
  border: "1px solid #333",
  borderRadius: "4px",
  color: "#fafafa",
  outline: "none",
};
