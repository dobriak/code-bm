import { useCallback, useEffect, useRef, useState } from "react";

const STREAM_URL = "http://localhost:8000/raidio.mp3";

/**
 * PlayerAudio — hidden <audio> element connected to the Icecast stream,
 * plus a "Click to start" overlay (browser autoplay policy) and basic
 * volume / pause controls.
 */
export default function PlayerAudio() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [started, setStarted] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolume] = useState(0.75);
  const [error, setError] = useState<string | null>(null);

  // Sync volume to the audio element
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  const handleStart = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.play().then(() => {
      setStarted(true);
      setPlaying(true);
      setError(null);
    }).catch((err) => {
      setError(`Playback failed: ${err instanceof Error ? err.message : String(err)}`);
    });
  }, []);

  const handlePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (audio.paused) {
      audio.play().then(() => setPlaying(true)).catch(() => {});
    } else {
      audio.pause();
      setPlaying(false);
    }
  }, []);

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setVolume(parseFloat(e.target.value));
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={STREAM_URL}
        crossOrigin="anonymous"
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onError={() => setError("Lost connection to stream")}
      />

      {/* Click-to-start overlay */}
      {!started && (
        <button
          onClick={handleStart}
          style={{
            padding: "0.75rem 2rem",
            fontSize: "1.125rem",
            fontWeight: 600,
            border: "2px solid #fafafa",
            borderRadius: "0.5rem",
            backgroundColor: "transparent",
            color: "#fafafa",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "#fafafa";
            e.currentTarget.style.color = "#0f0f0f";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "transparent";
            e.currentTarget.style.color = "#fafafa";
          }}
        >
          ▶ Click to Start Listening
        </button>
      )}

      {/* Error display */}
      {error && (
        <span style={{ color: "#ef4444", fontSize: "0.875rem" }}>{error}</span>
      )}

      {/* Controls (visible after start) */}
      {started && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
          }}
        >
          <button
            onClick={handlePlayPause}
            aria-label={playing ? "Pause" : "Play"}
            style={{
              width: "2.5rem",
              height: "2.5rem",
              borderRadius: "50%",
              border: "2px solid #fafafa",
              backgroundColor: "transparent",
              color: "#fafafa",
              cursor: "pointer",
              fontSize: "1rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {playing ? "⏸" : "▶"}
          </button>

          {/* Volume slider */}
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              fontSize: "0.875rem",
              color: "#fafafa",
              opacity: 0.7,
            }}
          >
            🔊
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={volume}
              onChange={handleVolumeChange}
              aria-label="Volume"
              style={{ width: "100px", accentColor: "#fafafa" }}
            />
          </label>
        </div>
      )}
    </div>
  );
}
