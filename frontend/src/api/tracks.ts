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