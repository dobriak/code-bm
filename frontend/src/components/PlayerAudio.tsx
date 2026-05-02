import { useRef, useState, useEffect } from "react";

interface PlayerAudioProps {
  src?: string;
}

export function PlayerAudio({ src = "http://localhost:8000/raidio.mp3" }: PlayerAudioProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [started, setStarted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);

  const handleStart = () => {
    setStarted(true);
    if (audioRef.current) {
      audioRef.current.play().catch(console.error);
    }
  };

  const handlePlayPause = () => {
    if (audioRef.current) {
      if (audioRef.current.paused) {
        audioRef.current.play().catch(console.error);
      } else {
        audioRef.current.pause();
      }
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handlePlaying = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    audio.addEventListener("playing", handlePlaying);
    audio.addEventListener("pause", handlePause);

    return () => {
      audio.removeEventListener("playing", handlePlaying);
      audio.removeEventListener("pause", handlePause);
    };
  }, []);

  return (
    <div className="player-audio">
      {!started ? (
        <div className="player-overlay">
          <button onClick={handleStart} className="start-button">
            Click to start
          </button>
        </div>
      ) : null}

      <audio
        ref={audioRef}
        src={src}
        crossOrigin="anonymous"
        preload="none"
      />

      {started && (
        <div className="player-controls">
          <button onClick={handlePlayPause} className="control-button">
            {isPlaying ? "Pause" : "Play"}
          </button>

          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={volume}
            onChange={handleVolumeChange}
            className="volume-slider"
            aria-label="Volume"
          />
        </div>
      )}

      <style>{`
        .player-audio {
          position: relative;
        }

        .player-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(0, 0, 0, 0.8);
          z-index: 100;
        }

        .start-button {
          padding: 1rem 2rem;
          font-size: 1.5rem;
          background: #0066cc;
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
        }

        .start-button:hover {
          background: #0055aa;
        }

        .player-controls {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          background: #333;
          color: white;
          border-radius: 8px;
        }

        .control-button {
          padding: 0.5rem 1rem;
          font-size: 1rem;
          background: #555;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }

        .control-button:hover {
          background: #666;
        }

        .volume-slider {
          width: 100px;
          cursor: pointer;
        }
      `}</style>
    </div>
  );
}

export default PlayerAudio;