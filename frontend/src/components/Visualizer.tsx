import { useRef, useState, useCallback, useEffect } from "react";

export type VisualizerMode = "bars" | "wave" | "off";

const STORAGE_KEY = "raidio.visualizer_mode";

function getStoredMode(): VisualizerMode {
  try {
    return (localStorage.getItem(STORAGE_KEY) as VisualizerMode) ?? "off";
  } catch {
    return "off";
  }
}

function storeMode(mode: VisualizerMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    // ignore
  }
}

interface VisualizerProps {
  streamSrc?: string;
}

export function Visualizer({ streamSrc = "http://localhost:8000/raidio.mp3" }: VisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [mode, setMode] = useState<VisualizerMode>(getStoredMode);
  const animFrameRef = useRef<number>(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const initializedRef = useRef(false);

  const cycleMode = useCallback(() => {
    setMode((prev) => {
      const next = prev === "off" ? "bars" : prev === "bars" ? "wave" : "off";
      storeMode(next);
      return next;
    });
  }, []);

  useEffect(() => {
    if (mode === "off") return;

    if (initializedRef.current) return;
    initializedRef.current = true;

    const audio = new Audio(streamSrc);
    audio.crossOrigin = "anonymous";
    audio.preload = "none";
    audioRef.current = audio;

    const ctx = new AudioContext();
    audioContextRef.current = ctx;

    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.85;
    analyserRef.current = analyser;

    const source = ctx.createMediaElementSource(audio);
    source.connect(analyser);
    analyser.connect(ctx.destination);

    audio.play().catch(() => {});
  }, [mode, streamSrc]);

  useEffect(() => {
    if (mode === "off" || !canvasRef.current || !analyserRef.current) {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const analyser = analyserRef.current;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      animFrameRef.current = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);

      ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      if (mode === "bars") {
        const barCount = 32;
        const barWidth = canvas.width / barCount;
        for (let i = 0; i < barCount; i++) {
          const dataIndex = Math.floor((i / barCount) * bufferLength);
          const value = dataArray[dataIndex];
          const barHeight = (value / 255) * canvas.height;
          const hue = (i / barCount) * 360;
          ctx.fillStyle = `hsl(${hue}, 80%, 55%)`;
          ctx.fillRect(i * barWidth, canvas.height - barHeight, barWidth - 2, barHeight);
        }
      } else if (mode === "wave") {
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#c084fc";
        ctx.beginPath();
        const sliceWidth = canvas.width / bufferLength;
        let x = 0;
        for (let i = 0; i < bufferLength; i++) {
          const v = dataArray[i] / 255;
          const y = (1 - v) * canvas.height;
          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
          x += sliceWidth;
        }
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();
      }
    };

    draw();

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [mode]);

  if (mode === "off") {
    return null;
  }

  return (
    <div className="visualizer">
      <button onClick={cycleMode} className="visualizer-toggle" aria-label="Toggle visualizer">
        {mode === "off" ? "Visualizer" : mode === "bars" ? "Bars" : "Wave"}
      </button>
      <canvas
        ref={canvasRef}
        width={300}
        height={80}
        className="visualizer-canvas"
      />
    </div>
  );
}
