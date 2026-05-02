/**
 * Browse/Create page — track browser with search and filters.
 * The right pane (playlist builder) comes in Phase 3.
 */
import { useCallback, useMemo, useState } from "react";
import { useTracks } from "../api/hooks";
import FilterSidebar from "../components/FilterSidebar";
import TrackTable from "../components/TrackTable";
import { TracksQuery } from "../api/client";

export default function CreatePage() {
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

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useTracks(query);

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

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f0f0f", color: "#fafafa", display: "flex", flexDirection: "column" }}>
      {/* Nav */}
      <nav
        style={{
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
        <a href="/" style={{ color: "#888", textDecoration: "none", fontSize: "0.875rem" }}>
          Player
        </a>
        <a href="/create" style={{ color: "#fafafa", textDecoration: "none", fontSize: "0.875rem" }}>
          Create
        </a>
        <a href="/admin" style={{ color: "#888", textDecoration: "none", fontSize: "0.875rem" }}>
          Admin
        </a>
      </nav>

      {/* Search bar */}
      <div
        style={{
          padding: "1rem 1.5rem",
          borderBottom: "1px solid #1a1a1a",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
          }}
        >
          <div
            style={{
              flex: 1,
              position: "relative",
            }}
          >
            <span style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "#555" }}>
              🔍
            </span>
            <input
              type="text"
              placeholder="Search tracks, artists, albums…"
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

      {/* Main content: sidebar + track table */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
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
        <TrackTable
          tracks={tracks}
          total={total}
          hasNextPage={hasNextPage ?? false}
          isFetchingNextPage={isFetchingNextPage}
          onLoadMore={() => fetchNextPage()}
        />
      </div>
    </div>
  );
}
