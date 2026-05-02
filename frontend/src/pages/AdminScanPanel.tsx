import { useRef, useEffect, useState } from "react";
import { useAdminScanStore } from "../stores/adminScanStore";
import { useScanLibrary, useScanJingles, useScanStatus } from "../api/admin";

export default function AdminScanPanel() {
  const { progress, isConnected, setProgress, setConnected } = useAdminScanStore();
  const scanLibrary = useScanLibrary();
  const scanJingles = useScanJingles();
  const { data: statusData } = useScanStatus();
  const wsRef = useRef<WebSocket | null>(null);
  const [recentPaths, setRecentPaths] = useState<string[]>([]);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/v1/admin/scan`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.phase) {
          setProgress(data);
          setRecentPaths((prev) => [data.current_path, ...prev.slice(0, 19)]);
        }
      } catch {
        // ignore non-JSON messages
      }
    };

    return () => {
      ws.close();
    };
  }, [setConnected, setProgress]);

  const handleScanLibrary = () => {
    scanLibrary.mutate();
  };

  const handleScanJingles = () => {
    scanJingles.mutate();
  };

  const lastJob = statusData?.jobs?.[0];

  return (
    <div className="admin-scan-panel">
      <h2>Library Scanner</h2>

      <div className="scan-buttons">
        <button
          onClick={handleScanLibrary}
          disabled={scanLibrary.isPending}
        >
          {scanLibrary.isPending ? "Scanning..." : "Scan Library"}
        </button>
        <button
          onClick={handleScanJingles}
          disabled={scanJingles.isPending}
        >
          {scanJingles.isPending ? "Scanning..." : "Scan Jingles"}
        </button>
      </div>

      <div className="scan-status">
        <div className="connection-status">
          <span className={isConnected ? "connected" : "disconnected"}>
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>

        {progress && (
          <div className="progress-container">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${(progress.done / progress.total) * 100}%` }}
              />
            </div>
            <div className="progress-text">
              {progress.done} / {progress.total} files
            </div>
          </div>
        )}

        {lastJob && (
          <div className="last-job">
            <h3>Last Scan Job</h3>
            <p>Status: {lastJob.status}</p>
            <p>Kind: {lastJob.kind}</p>
            <p>Added: {lastJob.tracks_added}, Updated: {lastJob.tracks_updated}, Removed: {lastJob.tracks_removed}</p>
            {lastJob.errors && lastJob.errors.length > 0 && (
              <div className="errors">
                <h4>Errors:</h4>
                <ul>
                  {lastJob.errors.slice(0, 5).map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {recentPaths.length > 0 && (
          <div className="recent-paths">
            <h3>Recent Paths</h3>
            <ul>
              {recentPaths.slice(0, 10).map((path, i) => (
                <li key={i}>{path}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}