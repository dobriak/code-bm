import { useRef, useState, useCallback, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Visualizer } from "./Visualizer";

const FULLSCREEN_KEY = "raidio.fullscreen_art";

export interface NowPlayingTrack {
  id: number;
  title: string | null;
  artist: string | null;
  album: string | null;
  duration_ms: number | null;
  cover_art_path: string | null;
  started_at: string;
  queue_item_id: number | null;
}

export interface NowPlayingData {
  current: NowPlayingTrack | null;
  prev3: NowPlayingTrack[];
  next3: NowPlayingTrack[];
}

function useNowPlaying() {
  const query = useQuery({
    queryKey: ["now-playing"],
    queryFn: async () => {
      const res = await fetch("/api/v1/now-playing");
      if (!res.ok) throw new Error("Failed to fetch now playing");
      return res.json() as Promise<NowPlayingData>;
    },
    refetchInterval: 5000,
  });

  return { data: query.data, isLoading: query.isLoading, isError: query.isError };
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

function computeRemaining(startedAt: string | null, durationMs: number | null): number | null {
  if (!startedAt || durationMs === null) return null;
  const startTime = new Date(startedAt).getTime();
  const now = Date.now();
  const elapsed = now - startTime;
  return durationMs - elapsed;
}

export function NowPlaying() {
  const { data, isLoading, isError } = useNowPlaying();
  const audioRef = useRef<HTMLAudioElement>(null);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [fullscreen, setFullscreen] = useState(() => {
    try {
      return localStorage.getItem(FULLSCREEN_KEY) === "true";
    } catch {
      return false;
    }
  });

  const current = data?.current;
  const prev3 = data?.prev3 ?? [];
  const next3 = data?.next3 ?? [];

  const toggleFullscreen = useCallback(() => {
    setFullscreen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(FULLSCREEN_KEY, String(next));
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  useEffect(() => {
    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === "f" || e.key === "F") {
        toggleFullscreen();
      }
    };
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, [toggleFullscreen]);

  const remainingMs = useMemo(
    () => computeRemaining(current?.started_at ?? null, current?.duration_ms ?? null),
    [current?.started_at, current?.duration_ms]
  );

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  }, []);

  const toggleMute = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
      setIsMuted((prev) => !prev);
    }
  }, [isMuted]);

  const togglePlay = useCallback(() => {
    if (audioRef.current) {
      if (isPaused) {
        audioRef.current.play();
      } else {
        audioRef.current.pause();
      }
      setIsPaused((prev) => !prev);
    }
  }, [isPaused]);

  if (isLoading) {
    return <div className="now-playing loading">Loading...</div>;
  }

  if (isError || !data) {
    return <div className="now-playing error">Unable to load now playing</div>;
  }

  return (
    <div className="now-playing">
      <audio ref={audioRef} crossOrigin="anonymous" />
      <div className={`now-playing-main ${fullscreen ? "fullscreen" : ""}`}>
        {current ? (
          <>
            <div className="album-art" onClick={toggleFullscreen} title="Toggle fullscreen (f)">
              {current.cover_art_path ? (
                <img src={`/api/v1/tracks/${current.id}/cover`} alt={current.title ?? "Album art"} />
              ) : (
                <div className="album-art-placeholder" />
              )}
            </div>
            {!fullscreen && (
              <div className="track-info">
                <h2 className="track-title">{current.title ?? "Unknown Title"}</h2>
                <p className="track-artist">{current.artist ?? "Unknown Artist"}</p>
                <p className="track-album">{current.album ?? "Unknown Album"}</p>
                <p className="track-remaining">
                  Remaining: {remainingMs !== null && remainingMs > 0 ? formatDuration(remainingMs) : "--:--"}
                </p>
              </div>
            )}
          </>
        ) : (
          <div className="no-track">
            <p>No track playing</p>
          </div>
        )}
      </div>

      {!fullscreen && (
        <>
          <div className="prev-next-strip">
            <div className="prev-tracks">
              {prev3.slice().reverse().map((track) => (
                <div key={track.queue_item_id ?? track.id} className="prev-track">
                  <span className="prev-track-title">{track.title ?? "Unknown"}</span>
                  <span className="prev-track-artist">{track.artist ?? "Unknown"}</span>
                </div>
              ))}
            </div>
            <div className="now-playing-controls">
              <button onClick={toggleMute} className="control-btn">
                {isMuted ? "Unmute" : "Mute"}
              </button>
              <button onClick={togglePlay} className="control-btn">
                {isPaused ? "Play" : "Pause"}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={volume}
                onChange={handleVolumeChange}
                className="volume-slider"
              />
            </div>
            <div className="next-tracks">
              {next3.map((track) => (
                <div key={track.queue_item_id ?? track.id} className="next-track">
                  <span className="next-track-title">{track.title ?? "Unknown"}</span>
                  <span className="next-track-artist">{track.artist ?? "Unknown"}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="broadcast-info">
            <span className="info-text">Volume and pause affect your local playback only</span>
          </div>

          <Visualizer audioElement={audioSourceRef.current} />
        </>
      )}
    </div>
  );
}