/**
 * API client for Raidio backend.
 */

export interface Track {
  id: number;
  artist: string | null;
  album: string | null;
  title: string | null;
  genre: string | null;
  year: number | null;
  track_number: number | null;
  duration_ms: number | null;
  cover_art_path: string | null;
  analysis_status: string;
}

export interface PaginatedTracks {
  items: Track[];
  next_cursor: string | null;
  total: number;
}

export interface TrackDetail extends Track {
  path: string;
  file_hash: string | null;
  disc_number: number | null;
  bitrate_kbps: number | null;
  sample_rate_hz: number | null;
  tags_scanned_at: string | null;
  audio_analyzed_at: string | null;
  analysis_error: string | null;
  quiet_passages: { id: number; start_ms: number; end_ms: number; duration_ms: number; region: string }[];
}

export interface FacetItem {
  name: string;
  count: number;
}

export interface Jingle {
  id: number;
  path: string;
  title: string | null;
  duration_ms: number | null;
  cover_art_path: string | null;
}

export interface ScanStatus {
  id: number;
  kind: string;
  started_at: string | null;
  finished_at: string | null;
  status: string;
  tracks_added: number;
  tracks_updated: number;
  tracks_removed: number;
}

export interface ScanResponse {
  scan_job_id: number;
  status: string;
}

export interface ScanProgress {
  [jobId: string]: {
    phase: string;
    total: number;
    done: number;
    current_path: string;
  };
}

export interface TracksQuery {
  q?: string;
  artist?: string;
  album?: string;
  genre?: string;
  year_from?: number;
  year_to?: number;
  duration_min?: number;
  duration_max?: number;
  cursor?: string;
  limit?: number;
}

const API_BASE = "/api/v1";

export async function fetchTracks(params: TracksQuery = {}): Promise<PaginatedTracks> {
  const searchParams = new URLSearchParams();
  if (params.q) searchParams.set("q", params.q);
  if (params.artist) searchParams.set("artist", params.artist);
  if (params.album) searchParams.set("album", params.album);
  if (params.genre) searchParams.set("genre", params.genre);
  if (params.year_from) searchParams.set("year_from", String(params.year_from));
  if (params.year_to) searchParams.set("year_to", String(params.year_to));
  if (params.duration_min) searchParams.set("duration_min", String(params.duration_min));
  if (params.duration_max) searchParams.set("duration_max", String(params.duration_max));
  if (params.cursor) searchParams.set("cursor", params.cursor);
  if (params.limit) searchParams.set("limit", String(params.limit));

  const resp = await fetch(`${API_BASE}/tracks?${searchParams}`);
  if (!resp.ok) throw new Error(`Failed to fetch tracks: ${resp.status}`);
  return resp.json();
}

export async function fetchTrack(id: number): Promise<TrackDetail> {
  const resp = await fetch(`${API_BASE}/tracks/${id}`);
  if (!resp.ok) throw new Error(`Failed to fetch track ${id}: ${resp.status}`);
  return resp.json();
}

export async function fetchArtists(): Promise<FacetItem[]> {
  const resp = await fetch(`${API_BASE}/artists`);
  if (!resp.ok) throw new Error("Failed to fetch artists");
  return resp.json();
}

export async function fetchAlbums(): Promise<FacetItem[]> {
  const resp = await fetch(`${API_BASE}/albums`);
  if (!resp.ok) throw new Error("Failed to fetch albums");
  return resp.json();
}

export async function fetchGenres(): Promise<FacetItem[]> {
  const resp = await fetch(`${API_BASE}/genres`);
  if (!resp.ok) throw new Error("Failed to fetch genres");
  return resp.json();
}

export async function fetchJingles(): Promise<Jingle[]> {
  const resp = await fetch(`${API_BASE}/jingles`);
  if (!resp.ok) throw new Error("Failed to fetch jingles");
  return resp.json();
}

export async function startScan(kind: "library" | "jingles"): Promise<ScanResponse> {
  const resp = await fetch(`${API_BASE}/admin/scan/${kind}`, { method: "POST" });
  if (!resp.ok) throw new Error(`Failed to start ${kind} scan`);
  return resp.json();
}

export async function fetchScanStatus(): Promise<ScanStatus[]> {
  const resp = await fetch(`${API_BASE}/admin/scan/status`);
  if (!resp.ok) throw new Error("Failed to fetch scan status");
  return resp.json();
}

export function createScanWebSocket(): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return new WebSocket(`${protocol}//${window.location.host}/ws/admin/scan`);
}
