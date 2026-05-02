import { useState } from "react";
import { useArtists, useAlbums, useGenres, useTracks, Track } from "../api/tracks";

interface TrackFilters {
  q?: string;
  artist?: string;
  album?: string;
  genre?: string;
  year_from?: number;
  year_to?: number;
  duration_min?: number;
  duration_max?: number;
}

export function BrowsePage() {
  const [filters, setFilters] = useState<TrackFilters>({});
  const [activeTab, setActiveTab] = useState<"browse" | "search">("browse");
  const [selectedArtist, setSelectedArtist] = useState<string | null>(null);
  const [selectedAlbum, setSelectedAlbum] = useState<string | null>(null);

  const { data: artistsData } = useArtists();
  const { data: albumsData } = useAlbums(selectedArtist || undefined);
  const { data: genresData } = useGenres();
  const { data: tracksData, isLoading } = useTracks(filters);

  const handleSearch = (query: string) => {
    setFilters((prev) => ({ ...prev, q: query || undefined }));
  };

  const handleArtistClick = (artist: string) => {
    setSelectedArtist(artist);
    setSelectedAlbum(null);
    setFilters((prev) => ({ ...prev, artist, album: undefined }));
    setActiveTab("browse");
  };

  const handleAlbumClick = (album: string, artist: string) => {
    setSelectedAlbum(album);
    setFilters((prev) => ({ ...prev, artist, album }));
    setActiveTab("browse");
  };

  const handleBackToArtists = () => {
    setSelectedArtist(null);
    setSelectedAlbum(null);
    setFilters({ artist: undefined, album: undefined });
  };

  const handleBackToAlbums = () => {
    setSelectedAlbum(null);
    setFilters((prev) => ({ ...prev, album: undefined }));
  };

  const handleTrackClick = (track: Track) => {
    console.log("Track clicked:", track);
  };

  return (
    <div className="browse-page">
      <div className="browse-header">
        <h1>Browse Library</h1>
        <div className="search-box">
          <input
            type="text"
            placeholder="Search tracks..."
            onChange={(e) => handleSearch(e.target.value)}
            value={filters.q || ""}
          />
        </div>
        <div className="view-toggle">
          <button
            className={activeTab === "browse" ? "active" : ""}
            onClick={() => setActiveTab("browse")}
          >
            Browse
          </button>
          <button
            className={activeTab === "search" ? "active" : ""}
            onClick={() => setActiveTab("search")}
          >
            Search
          </button>
        </div>
      </div>

      <div className="browse-content">
        {activeTab === "browse" && (
          <div className="browse-hierarchy">
            {!selectedArtist ? (
              <div className="artist-list">
                <h2>Artists ({artistsData?.artists?.length || 0})</h2>
                {artistsData?.artists?.map((artist: { name: string; track_count: number }) => (
                  <div
                    key={artist.name}
                    className="artist-row"
                    onClick={() => handleArtistClick(artist.name)}
                  >
                    <span className="artist-name">{artist.name}</span>
                    <span className="track-count">{artist.track_count} tracks</span>
                  </div>
                ))}
              </div>
            ) : !selectedAlbum ? (
              <div className="album-list">
                <button className="back-button" onClick={handleBackToArtists}>
                  Back to Artists
                </button>
                <h2>{selectedArtist}'s Albums ({albumsData?.albums?.length || 0})</h2>
                {albumsData?.albums?.map((album: { album: string; artist: string; track_count: number }) => (
                  <div
                    key={`${album.artist}-${album.album}`}
                    className="album-row"
                    onClick={() => handleAlbumClick(album.album, album.artist)}
                  >
                    <span className="album-name">{album.album}</span>
                    <span className="track-count">{album.track_count} tracks</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="track-list">
                <button className="back-button" onClick={handleBackToAlbums}>
                  Back to Albums
                </button>
                <h2>{selectedAlbum} by {selectedArtist}</h2>
                {tracksData?.tracks?.map((track: Track) => (
                  <TrackRow key={track.id} track={track} onClick={handleTrackClick} />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "search" && (
          <div className="search-results">
            {isLoading ? (
              <div className="loading">Loading...</div>
            ) : tracksData?.tracks?.length === 0 ? (
              <div className="empty">No tracks found</div>
            ) : (
              <div className="track-results">
                <div className="results-count">{tracksData?.total || 0} tracks found</div>
                {tracksData?.tracks?.map((track: Track) => (
                  <TrackRow key={track.id} track={track} onClick={handleTrackClick} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="sidebar">
        <h3>Filter by Genre</h3>
        <div className="genre-list">
          {genresData?.genres?.map((genre: { name: string; track_count: number }) => (
            <div
              key={genre.name}
              className={`genre-item ${filters.genre === genre.name ? "active" : ""}`}
              onClick={() => setFilters((prev) => ({
                ...prev,
                genre: prev.genre === genre.name ? undefined : genre.name,
              }))}
            >
              <span className="genre-name">{genre.name}</span>
              <span className="genre-count">{genre.track_count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface TrackRowProps {
  track: Track;
  onClick: (track: Track) => void;
}

function TrackRow({ track, onClick }: TrackRowProps) {
  const duration = track.duration_ms
    ? `${Math.floor(track.duration_ms / 60000)}:${String(Math.floor((track.duration_ms % 60000) / 1000)).padStart(2, "0")}`
    : "--:--";

  return (
    <div className="track-row" onClick={() => onClick(track)}>
      <div className="track-info">
        <span className="track-title">{track.title || "Unknown Title"}</span>
        <span className="track-artist">{track.artist || "Unknown Artist"}</span>
      </div>
      <div className="track-album">{track.album || "Unknown Album"}</div>
      <div className="track-duration">{duration}</div>
      <div className="track-analysis">
        <span className={`analysis-status ${track.analysis_status || "pending"}`}>
          {track.analysis_status || "pending"}
        </span>
      </div>
    </div>
  );
}