/**
 * Visualizer — Web Audio API visualizer fed from the broadcast <audio> element.
 *
 * Modes:
 *   "bars"    — 32-band frequency bars (canvas)
 *   "wave"    — sine-wave waveform (canvas)
 *   "off"     — hidden
 *
 * Smoothing constant ≈ 0.85 for a "musical" feel.
 * On CORS error or crossOrigin failure, gracefully degrades by hiding the toggle.
 *
 * Persists user choice in localStorage.raidio.visualizer_mode.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export type VisualizerMode = "bars" | "wave" | "off";

const STORAGE_KEY = "raidio.visualizer_mode";
const FFT_SIZE = 64; // 32 bins after halving
const SMOOTHING = 0.85;

function loadMode(): VisualizerMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "bars" || stored === "wave" || stored === "off") return stored;
  } catch {
    // ignore
  }
  return "off";
}

function saveMode(mode: VisualizerMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    // ignore
  }
}

interface VisualizerProps {
  /** Ref to the <audio> element to connect the analyser to. */
  audioRef: React.RefObject<HTMLAudioElement | null>;
}

export default function Visualizer({ audioRef }: VisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [mode, setMode] = useState<VisualizerMode>(loadMode);
  const [corsBlocked, setCorsBlocked] = useState(false);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef<number>(0);

  // Cycle through modes: bars → wave → off → bars
  const cycleMode = useCallback(() => {
    setMode((prev) => {
      const next: VisualizerMode = prev === "off" ? "bars" : prev === "bars" ? "wave" : "off";
      saveMode(next);
      return next;
    });
  }, []);

  // Initialize AudioContext + AnalyserNode on first interaction
  useEffect(() => {
    if (mode === "off") return;

    const audio = audioRef.current;
    if (!audio) return;

    let cancelled = false;

    async function init() {
      try {
        // Create or reuse AudioContext
        if (!ctxRef.current) {
          const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
          ctxRef.current = new AudioCtx();
        }
        const ctx = ctxRef.current;

        // Resume if suspended (browser autoplay policy)
        if (ctx.state === "suspended") {
          await ctx.resume();
        }

        // Connect audio element → analyser (only once)
        if (!sourceRef.current) {
          sourceRef.current = ctx.createMediaElementSource(audio);
          analyserRef.current = ctx.createAnalyser();
          analyserRef.current.fftSize = FFT_SIZE * 2;
          analyserRef.current.smoothingTimeConstant = SMOOTHING;
          sourceRef.current.connect(analyserRef.current);
          analyserRef.current.connect(ctx.destination);
        }

        if (cancelled) return;
        setCorsBlocked(false);
      } catch (err) {
        if (cancelled) return;
        // CORS error: MediaElementAudioSource outputs silence due to tainted origin
        console.warn("Visualizer: could not connect to audio element (CORS?)", err);
        setCorsBlocked(true);
      }
    }

    init();

    return () => {
      cancelled = true;
    };
  }, [mode, audioRef]);

  // Animation loop
  useEffect(() => {
    if (mode === "off" || corsBlocked) return;

    const canvas = canvasRef.current;
    const analyser = analyserRef.current;
    if (!canvas || !analyser) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function drawBars() {
      if (!ctx || !analyser || !canvas) return;
      analyser.getByteFrequencyData(dataArray);

      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const barCount = bufferLength;
      const barWidth = w / barCount;
      const gap = 2;

      for (let i = 0; i < barCount; i++) {
        const value = dataArray[i] / 255;
        const barHeight = value * h;

        // Gradient from accent to dim
        const hue = 200 + (i / barCount) * 40;
        ctx.fillStyle = `hsla(${hue}, 70%, ${40 + value * 30}%, ${0.6 + value * 0.4})`;
        ctx.fillRect(
          i * barWidth + gap / 2,
          h - barHeight,
          barWidth - gap,
          barHeight,
        );
      }
    }

    function drawWave() {
      if (!ctx || !analyser || !canvas) return;
      analyser.getByteTimeDomainData(dataArray);

      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      ctx.lineWidth = 2;
      ctx.strokeStyle = "hsla(220, 80%, 65%, 0.8)";
      ctx.beginPath();

      const sliceWidth = w / bufferLength;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = (v * h) / 2;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
        x += sliceWidth;
      }

      ctx.lineTo(w, h / 2);
      ctx.stroke();
    }

    function animate() {
      if (mode === "bars") {
        drawBars();
      } else if (mode === "wave") {
        drawWave();
      }
      rafRef.current = requestAnimationFrame(animate);
    }

    rafRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, [mode, corsBlocked]);

  // Resize canvas to match parent
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        canvas.width = width * window.devicePixelRatio;
        canvas.height = height * window.devicePixelRatio;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        }
      }
    });
    observer.observe(canvas);

    return () => observer.disconnect();
  }, []);

  // Cleanup AudioContext on unmount
  useEffect(() => {
    return () => {
      if (ctxRef.current && ctxRef.current.state !== "closed") {
        ctxRef.current.close().catch(() => {});
      }
      ctxRef.current = null;
      sourceRef.current = null;
      analyserRef.current = null;
    };
  }, []);

  // If CORS blocked, don't render anything
  if (corsBlocked) {
    return null;
  }

  return (
    <div style={{ position: "relative", width: "100%", display: "flex", flexDirection: "column", alignItems: "center" }}>
      {mode !== "off" && (
        <canvas
          ref={canvasRef}
          style={{
            width: "100%",
            height: mode === "bars" ? "80px" : "60px",
            borderRadius: "0.5rem",
            opacity: 0.8,
          }}
        />
      )}
      <button
        onClick={cycleMode}
        aria-label={`Visualizer: ${mode}`}
        title={`Visualizer: ${mode} (click to cycle)`}
        style={{
          background: "none",
          border: "1px solid #333",
          borderRadius: "0.375rem",
          color: mode === "off" ? "#555" : "#999",
          cursor: "pointer",
          fontSize: "0.625rem",
          padding: "0.25rem 0.5rem",
          marginTop: "0.25rem",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}
      >
        {mode === "off" ? "visualizer off" : mode === "bars" ? "♫ bars" : "〰 wave"}
      </button>
    </div>
  );
}
