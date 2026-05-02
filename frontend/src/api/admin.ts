import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminFetch } from "./adminAuth";

export interface ScanJob {
  id: number;
  kind: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  tracks_added: number;
  tracks_updated: number;
  tracks_removed: number;
  errors: string[];
}

export interface AdminStats {
  tracks: number;
  artists: number;
  albums: number;
  genres: number;
  total_playtime_ms: number;
  jingles: number;
  queue_length: number;
  broadcast_status: string;
}

export interface AdminSettings {
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
  auto_playlists: { id: number; name: string }[];
}

const API_BASE = "/api/v1/admin";

export function useScanStatus() {
  return useQuery({
    queryKey: ["admin-scan-status"],
    queryFn: async () => {
      const res = await adminFetch(`${API_BASE}/scan/status`);
      if (!res.ok) throw new Error("Failed to fetch scan status");
      return res.json() as Promise<{ jobs: ScanJob[] }>;
    },
    refetchInterval: 5000,
  });
}

export function useScanLibrary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (path?: string) => {
      const params = path ? `?path=${encodeURIComponent(path)}` : "";
      const res = await adminFetch(`${API_BASE}/scan/library${params}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to start library scan");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-scan-status"] });
    },
  });
}

export function useScanJingles() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (path?: string) => {
      const params = path ? `?path=${encodeURIComponent(path)}` : "";
      const res = await adminFetch(`${API_BASE}/scan/jingles${params}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to start jingles scan");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-scan-status"] });
    },
  });
}

export function useAdminStats() {
  return useQuery({
    queryKey: ["admin-stats"],
    queryFn: async () => {
      const res = await adminFetch(`${API_BASE}/stats`);
      if (!res.ok) throw new Error("Failed to fetch stats");
      return res.json() as Promise<AdminStats>;
    },
  });
}

export function useAdminSettings() {
  return useQuery({
    queryKey: ["admin-settings"],
    queryFn: async () => {
      const res = await adminFetch(`${API_BASE}/settings`);
      if (!res.ok) throw new Error("Failed to fetch settings");
      return res.json() as Promise<AdminSettings>;
    },
  });
}

export function useUpdateAdminSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<AdminSettings>) => {
      const res = await adminFetch(`${API_BASE}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed to update settings");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-settings"] });
    },
  });
}

export function useAdminQueue() {
  return useQuery({
    queryKey: ["admin-queue"],
    queryFn: async () => {
      const res = await adminFetch(`${API_BASE}/queue`);
      if (!res.ok) throw new Error("Failed to fetch queue");
      return res.json();
    },
  });
}

export function useReorderQueue() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (items: number[]) => {
      const res = await adminFetch(`${API_BASE}/queue/reorder`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items }),
      });
      if (!res.ok) throw new Error("Failed to reorder queue");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-queue"] });
    },
  });
}

export function useDeleteQueueItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: number) => {
      const res = await adminFetch(`${API_BASE}/queue/${itemId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete item");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-queue"] });
    },
  });
}

export function useSkipQueue() {
  return useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`${API_BASE}/queue/skip`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to skip");
      return res.json();
    },
  });
}

export function useInsertJingle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (jingleId: number) => {
      const res = await adminFetch(`${API_BASE}/queue/insert-jingle/${jingleId}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to insert jingle");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-queue"] });
    },
  });
}

export function useReanalyzeTrack() {
  return useMutation({
    mutationFn: async (trackId: number) => {
      const res = await adminFetch(`${API_BASE}/tracks/${trackId}/reanalyze`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to reanalyze");
      return res.json();
    },
  });
}

export function useAutoPlaylists() {
  return useQuery({
    queryKey: ["admin-auto-playlists"],
    queryFn: async () => {
      const res = await adminFetch(`${API_BASE}/auto-playlists`);
      if (!res.ok) throw new Error("Failed to fetch playlists");
      return res.json();
    },
  });
}

export function useCreateAutoPlaylist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; notes?: string; items?: unknown[] }) => {
      const res = await adminFetch(`${API_BASE}/auto-playlists`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed to create playlist");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-auto-playlists"] });
    },
  });
}

export function useUpdateAutoPlaylist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (playlistId: number, body: { name?: string; notes?: string; items?: unknown[] }) => {
      const res = await adminFetch(`${API_BASE}/auto-playlists/${playlistId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed to update playlist");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-auto-playlists"] });
    },
  });
}

export function useDeleteAutoPlaylist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (playlistId: number) => {
      const res = await adminFetch(`${API_BASE}/auto-playlists/${playlistId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete playlist");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-auto-playlists"] });
    },
  });
}
