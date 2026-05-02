/**
 * React Query hooks for Raidio API.
 */

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import type { TracksQuery } from "./client";
import { fetchAlbums, fetchArtists, fetchGenres, fetchTracks } from "./client";

export function useTracks(params: TracksQuery = {}) {
  return useInfiniteQuery({
    queryKey: ["tracks", params.q, params.artist, params.album, params.genre,
               params.year_from, params.year_to, params.duration_min, params.duration_max],
    queryFn: ({ pageParam }) => fetchTracks({ ...params, cursor: pageParam as string | undefined }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}

export function useArtists() {
  return useQuery({
    queryKey: ["artists"],
    queryFn: fetchArtists,
  });
}

export function useAlbums() {
  return useQuery({
    queryKey: ["albums"],
    queryFn: fetchAlbums,
  });
}

export function useGenres() {
  return useQuery({
    queryKey: ["genres"],
    queryFn: fetchGenres,
  });
}
