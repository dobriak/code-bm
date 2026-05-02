/**
 * API client for Raidio backend.
 * Includes admin authentication helpers and all endpoint functions.
 */

// ── Types ─────────────────────────────────────────────────────────

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

// ── Now-playing types ────────────────────────────────────────────

export interface QueueTrack {
  id: number;
  track_id: number | null;
  jingle_id: number | null;
  artist: string | null;
  title: string | null;
  album: string | null;
  duration_ms: number | null;
  cover_art_path: string | null;
  state: string;
  started_at: string | null;
  ended_at: string | null;
  owner_label: string | null;
}

export interface NowPlayingData {
  current: QueueTrack | null;
  prev: QueueTrack[];
  next: QueueTrack[];
  buffer_offset_ms: number;
}

// ── Playlist submission types ─────────────────────────────────────

export interface PlaylistItemCreate {
  track_id: number | null;
  jingle_id: number | null;
  overlay_at_ms: number | null;
}

export interface PlaylistCreateRequest {
  name: string;
  notes?: string;
  items: PlaylistItemCreate[];
  owner_label?: string;
}

export interface PlaylistCreateResponse {
  id: number;
  name: string;
  notes: string | null;
  owner_label: string | null;
  estimated_time_to_play_ms: number | null;
}

// ── Random track type ────────────────────────────────────────────

export interface RandomTrack {
  id: number;
  artist: string | null;
  title: string | null;
  album: string | null;
  duration_ms: number | null;
  cover_art_path: string | null;
}

// ── Admin types ───────────────────────────────────────────────────

export interface AdminStats {
  track_count: number;
  artist_count: number;
  album_count: number;
  genre_count: number;
  total_playtime_ms: number;
  queue_length: number;
  broadcast_status: string;
}

export interface AdminSettings {
  id: number;
  library_path: string;
  jingles_path: string;
  idle_behavior: string;
  default_auto_playlist_id: number | null;
  crossfade_enabled: boolean;
  crossfade_duration_ms: number;
  gapless_enabled: boolean;
  jingle_duck_db: number;
  icecast_buffer_offset_ms: number;
  min_quiet_duration_s: number;
}

export interface AdminSettingsUpdate {
  library_path?: string;
  jingles_path?: string;
  idle_behavior?: string;
  default_auto_playlist_id?: number | null;
  crossfade_enabled?: boolean;
  crossfade_duration_ms?: number;
  gapless_enabled?: boolean;
  jingle_duck_db?: number;
  icecast_buffer_offset_ms?: number;
  min_quiet_duration_s?: number;
}

export interface QueueItem {
  id: number;
  position: number;
  playlist_id: number | null;
  track_id: number | null;
  jingle_id: number | null;
  state: string;
  artist: string | null;
  title: string | null;
  album: string | null;
  duration_ms: number | null;
  owner_label: string | null;
}

export interface QueueResponse {
  items: QueueItem[];
  active_playlists: { id: number; name: string; owner_label: string | null; item_count: number }[];
}

export interface AutoPlaylist {
  id: number;
  name: string;
  notes: string | null;
  is_default: boolean;
  item_count: number;
  created_at: string | null;
}

export interface AutoPlaylistDetail extends AutoPlaylist {
  items: { id: number; position: number; track_id: number | null; jingle_id: number | null; overlay_at_ms: number | null }[];
}

const API_BASE = "/api/v1";

// ── Auth helpers ──────────────────────────────────────────────────

function getAdminJwt(): string | null {
  try {
    const data = localStorage.getItem("raidio.admin_jwt");
    if (!data) return null;
    const parsed = JSON.parse(data);
    return parsed?.state?.jwt || null;
  } catch {
    return null;
  }
}

function authHeaders(): Record<string, string> {
  const jwt = getAdminJwt();
  if (!jwt) return {};
  return { Authorization: `Bearer ${jwt}` };
}

async function adminFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const headers = { ...authHeaders(), ...options.headers };
  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (resp.status === 401) {
    // Clear stale JWT and redirect to login
    localStorage.removeItem("raidio.admin_jwt");
    window.location.href = "/admin/login";
    throw new Error("Unauthorized");
  }
  return resp;
}

// ── Admin auth ────────────────────────────────────────────────────

export async function adminLogin(email: string, password: string): Promise<{ access_token: string }> {
  const resp = await fetch(`${API_BASE}/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    throw new Error("Invalid email or password");
  }
  return resp.json();
}

// ── Track endpoints ──────────────────────────────────────────────

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

export async function fetchRandomTrack(): Promise<RandomTrack> {
  const resp = await fetch(`${API_BASE}/tracks/random`);
  if (!resp.ok) throw new Error(`Failed to fetch random track: ${resp.status}`);
  return resp.json();
}

// ── Facet endpoints ──────────────────────────────────────────────

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

// ── Jingles endpoint ─────────────────────────────────────────────

export async function fetchJingles(): Promise<Jingle[]> {
  const resp = await fetch(`${API_BASE}/jingles`);
  if (!resp.ok) throw new Error("Failed to fetch jingles");
  return resp.json();
}

// ── Now-playing ──────────────────────────────────────────────────

export async function fetchNowPlaying(): Promise<NowPlayingData> {
  const resp = await fetch(`${API_BASE}/now-playing`);
  if (!resp.ok) throw new Error("Failed to fetch now-playing");
  return resp.json();
}

export function createNowPlayingWebSocket(): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return new WebSocket(`${protocol}//${window.location.host}/ws/now-playing`);
}

// ── Queue / Playlist submission ──────────────────────────────────

export async function submitPlaylist(body: PlaylistCreateRequest): Promise<PlaylistCreateResponse> {
  const resp = await fetch(`${API_BASE}/queue/playlists`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Raidio-User": body.owner_label || "" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to submit playlist: ${resp.status}`);
  }
  return resp.json();
}

// ── Scan endpoints (admin, require auth) ─────────────────────────

export async function startScan(kind: "library" | "jingles"): Promise<ScanResponse> {
  const resp = await adminFetch(`/admin/scan/${kind}`, { method: "POST" });
  if (!resp.ok) throw new Error(`Failed to start ${kind} scan`);
  return resp.json();
}

export async function fetchScanStatus(): Promise<ScanStatus[]> {
  const resp = await adminFetch("/admin/scan/status");
  if (!resp.ok) throw new Error("Failed to fetch scan status");
  return resp.json();
}

export function createScanWebSocket(): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const jwt = getAdminJwt();
  const tokenParam = jwt ? `?token=${encodeURIComponent(jwt)}` : "";
  return new WebSocket(`${protocol}//${window.location.host}/ws/admin/scan${tokenParam}`);
}

// ── Admin stats ──────────────────────────────────────────────────

export async function fetchAdminStats(): Promise<AdminStats> {
  const resp = await adminFetch("/admin/stats");
  if (!resp.ok) throw new Error("Failed to fetch admin stats");
  return resp.json();
}

// ── Admin settings ───────────────────────────────────────────────

export async function fetchAdminSettings(): Promise<AdminSettings> {
  const resp = await adminFetch("/admin/settings");
  if (!resp.ok) throw new Error("Failed to fetch admin settings");
  return resp.json();
}

export async function updateAdminSettings(body: AdminSettingsUpdate): Promise<AdminSettings> {
  const resp = await adminFetch("/admin/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error("Failed to update admin settings");
  return resp.json();
}

// ── Admin queue management ───────────────────────────────────────

export async function fetchQueue(): Promise<QueueResponse> {
  const resp = await adminFetch("/admin/queue");
  if (!resp.ok) throw new Error("Failed to fetch queue");
  return resp.json();
}

export async function reorderQueue(items: { id: number; position: number }[]): Promise<void> {
  const resp = await adminFetch("/admin/queue/reorder", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(items),
  });
  if (!resp.ok) throw new Error("Failed to reorder queue");
}

export async function deleteQueueItem(itemId: number): Promise<void> {
  const resp = await adminFetch(`/admin/queue/${itemId}`, { method: "DELETE" });
  if (!resp.ok) throw new Error("Failed to delete queue item");
}

export async function skipCurrentTrack(): Promise<void> {
  const resp = await adminFetch("/admin/queue/skip", { method: "POST" });
  if (!resp.ok) throw new Error("Failed to skip track");
}

export async function insertJingle(jingleId: number): Promise<void> {
  const resp = await adminFetch(`/admin/queue/insert-jingle/${jingleId}`, { method: "POST" });
  if (!resp.ok) throw new Error("Failed to insert jingle");
}

// ── Auto-playlists ───────────────────────────────────────────────

export async function fetchAutoPlaylists(): Promise<AutoPlaylist[]> {
  const resp = await adminFetch("/admin/auto-playlists");
  if (!resp.ok) throw new Error("Failed to fetch auto-playlists");
  return resp.json();
}

export async function fetchAutoPlaylist(id: number): Promise<AutoPlaylistDetail> {
  const resp = await adminFetch(`/admin/auto-playlists/${id}`);
  if (!resp.ok) throw new Error("Failed to fetch auto-playlist");
  return resp.json();
}

export async function createAutoPlaylist(body: {
  name: string;
  notes?: string;
  items: { track_id?: number; jingle_id?: number }[];
}): Promise<AutoPlaylist> {
  const resp = await adminFetch("/admin/auto-playlists", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error("Failed to create auto-playlist");
  return resp.json();
}

export async function updateAutoPlaylist(
  id: number,
  body: {
    name?: string;
    notes?: string;
    is_default?: boolean;
    items?: { track_id?: number; jingle_id?: number }[];
  },
): Promise<AutoPlaylist> {
  const resp = await adminFetch(`/admin/auto-playlists/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error("Failed to update auto-playlist");
  return resp.json();
}

export async function deleteAutoPlaylist(id: number): Promise<void> {
  const resp = await adminFetch(`/admin/auto-playlists/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error("Failed to delete auto-playlist");
}

// ── Re-analyze track ─────────────────────────────────────────────

export async function reanalyzeTrack(trackId: number): Promise<void> {
  const resp = await adminFetch(`/admin/tracks/${trackId}/reanalyze`, { method: "POST" });
  if (!resp.ok) throw new Error("Failed to reanalyze track");
}
