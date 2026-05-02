import { useQuery } from "@tanstack/react-query";

export interface Track {
  id: number;
  path: string;
  artist: string | null;
  album: string | null;
  title: string | null;
  genre: string | null;
  year: number | null;
  track_number: number | null;
  disc_number: number | null;
  duration_ms: number | null;
  bitrate_kbps: number | null;
  sample_rate_hz: number | null;
  analysis_status: string | null;
  cover_art_path: string | null;
}

export interface QuietPassage {
  id: number;
  start_ms: number;
  end_ms: number;
  duration_ms: number;
  region: string | null;
}

export interface TrackDetail extends Track {
  quiet_passages: QuietPassage[];
}

export interface Jingle {
  id: number;
  path: string;
  title: string;
  duration_ms: number | null;
  cover_art_path: string | null;
}

const API_BASE = "/api/v1";

async function fetchTracks(params: Record<string, string | number | undefined>) {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) searchParams.set(key, String(value));
  }
  const res = await fetch(`${API_BASE}/tracks?${searchParams}`);
  if (!res.ok) throw new Error("Failed to fetch tracks");
  return res.json();
}

export function useTracks(params: {
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
}) {
  return useQuery({
    queryKey: ["tracks", params],
    queryFn: () => fetchTracks(params),
  });
}

export function useTrack(trackId: number) {
  return useQuery({
    queryKey: ["track", trackId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/tracks/${trackId}`);
      if (!res.ok) throw new Error("Failed to fetch track");
      return res.json() as Promise<TrackDetail>;
    },
  });
}

export function useArtists() {
  return useQuery({
    queryKey: ["artists"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/artists`);
      if (!res.ok) throw new Error("Failed to fetch artists");
      return res.json();
    },
  });
}

export function useAlbums(artist?: string) {
  return useQuery({
    queryKey: ["albums", artist],
    queryFn: async () => {
      const params = artist ? `?artist=${encodeURIComponent(artist)}` : "";
      const res = await fetch(`${API_BASE}/albums${params}`);
      if (!res.ok) throw new Error("Failed to fetch albums");
      return res.json();
    },
    enabled: true,
  });
}

export function useGenres() {
  return useQuery({
    queryKey: ["genres"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/genres`);
      if (!res.ok) throw new Error("Failed to fetch genres");
      return res.json();
    },
  });
}

export function useJingles() {
  return useQuery({
    queryKey: ["jingles"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/jingles`);
      if (!res.ok) throw new Error("Failed to fetch jingles");
      return res.json();
    },
  });
}

export function useRandomTrack() {
  return useQuery({
    queryKey: ["random-track"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/tracks/random`);
      if (!res.ok) throw new Error("Failed to fetch random track");
      return res.json() as Promise<Track>;
    },
  });
}

export interface ResolvedItem {
  path: string;
  type: "track" | "jingle";
  id: number;
  title: string | null;
  duration_ms: number | null;
}

export interface ResolveResult {
  resolved: ResolvedItem[];
  missing: string[];
}

export async function resolvePaths(items: { path: string; type: "track" | "jingle" }[]): Promise<ResolveResult> {
  const res = await fetch(`${API_BASE}/tracks/resolve-paths`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
  if (!res.ok) throw new Error("Failed to resolve paths");
  return res.json();
}

export interface RaidioPlaylist {
  raidio_version: 1;
  name: string;
  notes?: string;
  items: {
    type: "track" | "jingle";
    path: string;
    overlay_at_ms?: number;
  }[];
}

export function savePlaylist(playlist: RaidioPlaylist): void {
  const blob = new Blob([JSON.stringify(playlist, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${playlist.name.replace(/[^a-z0-9]/gi, "_")}.raidio`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function parsePlaylistFile(file: File): Promise<RaidioPlaylist> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result as string);
        if (parsed.raidio_version !== 1) {
          reject(new Error("Unsupported playlist version"));
          return;
        }
        if (!parsed.name || !Array.isArray(parsed.items)) {
          reject(new Error("Invalid playlist format"));
          return;
        }
        resolve(parsed as RaidioPlaylist);
      } catch {
        reject(new Error("Failed to parse playlist file"));
      }
    };
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsText(file);
  });
}