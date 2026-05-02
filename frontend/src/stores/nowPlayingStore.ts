/**
 * Now-playing store — holds current track, prev/next lists,
 * and the Icecast buffer offset for computing remaining time.
 */

import { create } from "zustand";

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

export interface NowPlayingState {
  /** Currently playing track (null if nothing is on air). */
  current: QueueTrack | null;
  /** Up to 3 tracks that played before current. */
  prev: QueueTrack[];
  /** Up to 3 tracks queued after current. */
  next: QueueTrack[];
  /** Buffer offset in ms for aligning UI with actual audio. */
  bufferOffsetMs: number;
  /** Whether the WebSocket is connected. */
  connected: boolean;
}

interface NowPlayingActions {
  setNowPlaying: (state: NowPlayingState) => void;
  setConnected: (connected: boolean) => void;
}

export const useNowPlayingStore = create<NowPlayingState & NowPlayingActions>()(
  (set) => ({
    current: null,
    prev: [],
    next: [],
    bufferOffsetMs: 3000,
    connected: false,
    setNowPlaying: (state) => set(state),
    setConnected: (connected) => set({ connected }),
  }),
);
