import { useCallback, useEffect, useRef, useState } from "react";
import type { ScanProgress, ScanStatus } from "../api/client";
import { createScanWebSocket, fetchScanStatus, startScan } from "../api/client";

/**
 * AdminScanPanel — minimal scan UI for Phase 2.
 * Auth gating comes in Phase 4.
 */
export default function AdminScanPanel() {
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState<ScanProgress>({});
  const [recentJobs, setRecentJobs] = useState<ScanStatus[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch recent scan jobs on mount
  useEffect(() => {
    fetchScanStatus().then(setRecentJobs).catch(() => {});
  }, []);

  // Connect to scan WebSocket
  useEffect(() => {
    const ws = createScanWebSocket();
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ScanProgress;
        setProgress((prev) => ({ ...prev, ...data }));

        // Refresh job list when a scan completes
        for (const job of Object.values(data)) {
          if (job.phase === "done" || job.phase === "error") {
            setScanning(false);
            fetchScanStatus().then(setRecentJobs).catch(() => {});
          }
        }
      } catch {
        // ignore parse errors
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  const handleScan = useCallback(
    async (kind: "library" | "jingles") => {
      try {
        setScanning(true);
        const resp = await startScan(kind);
        setProgress((prev) => ({
          ...prev,
          [resp.scan_job_id]: { phase: "scanning", total: 0, done: 0, current_path: "" },
        }));
      } catch (err) {
        setScanning(false);
        console.error("Scan failed:", err);
      }
    },
    [],
  );

  // Aggregate progress from all active jobs
  const activeJobs = Object.entries(progress).filter(([, v]) => v.phase === "scanning");
  const totalDone = activeJobs.reduce((sum, [, v]) => sum + v.done, 0);

  return (
    <div style={{ padding: "1.5rem", maxWidth: "800px", margin: "0 auto" }}>
      <h2 style={{ marginBottom: "1.5rem" }}>Library Scanner</h2>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
        <button
          onClick={() => handleScan("library")}
          disabled={scanning}
          style={{
            padding: "0.625rem 1.5rem",
            fontSize: "0.875rem",
            fontWeight: 600,
            border: "2px solid #fafafa",
            borderRadius: "0.5rem",
            backgroundColor: scanning ? "#333" : "transparent",
            color: scanning ? "#666" : "#fafafa",
            cursor: scanning ? "not-allowed" : "pointer",
          }}
        >
          📀 Scan Library
        </button>
        <button
          onClick={() => handleScan("jingles")}
          disabled={scanning}
          style={{
            padding: "0.625rem 1.5rem",
            fontSize: "0.875rem",
            fontWeight: 600,
            border: "2px solid #fafafa",
            borderRadius: "0.5rem",
            backgroundColor: scanning ? "#333" : "transparent",
            color: scanning ? "#666" : "#fafafa",
            cursor: scanning ? "not-allowed" : "pointer",
          }}
        >
          🔔 Scan Jingles
        </button>
      </div>

      {/* Progress bar */}
      {activeJobs.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <div
            style={{
              width: "100%",
              height: "8px",
              backgroundColor: "#222",
              borderRadius: "4px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                backgroundColor: "#22c55e",
                width: `${Math.min(100, totalDone > 0 ? 100 : 10)}%`,
                transition: "width 0.3s ease",
              }}
            />
          </div>
          <p style={{ fontSize: "0.75rem", color: "#888", marginTop: "0.5rem" }}>
            Scanned {totalDone} files…{Object.values(progress).find((v) => v.current_path) && (
              <> ({Object.values(progress).find((v) => v.current_path)!.current_path})</>
            )}
          </p>
        </div>
      )}

      {/* Recent scan jobs */}
      {recentJobs.length > 0 && (
        <div>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem", color: "#ccc" }}>Recent Scans</h3>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "0.8125rem",
            }}
          >
            <thead>
              <tr style={{ borderBottom: "1px solid #333" }}>
                <th style={{ textAlign: "left", padding: "0.5rem", color: "#888" }}>Kind</th>
                <th style={{ textAlign: "left", padding: "0.5rem", color: "#888" }}>Status</th>
                <th style={{ textAlign: "right", padding: "0.5rem", color: "#888" }}>Added</th>
                <th style={{ textAlign: "right", padding: "0.5rem", color: "#888" }}>Updated</th>
                <th style={{ textAlign: "right", padding: "0.5rem", color: "#888" }}>Removed</th>
              </tr>
            </thead>
            <tbody>
              {recentJobs.map((job) => (
                <tr key={job.id} style={{ borderBottom: "1px solid #1a1a1a" }}>
                  <td style={{ padding: "0.5rem" }}>{job.kind}</td>
                  <td style={{ padding: "0.5rem", color: job.status === "done" ? "#22c55e" : job.status === "error" ? "#ef4444" : "#f59e0b" }}>
                    {job.status}
                  </td>
                  <td style={{ padding: "0.5rem", textAlign: "right" }}>{job.tracks_added}</td>
                  <td style={{ padding: "0.5rem", textAlign: "right" }}>{job.tracks_updated}</td>
                  <td style={{ padding: "0.5rem", textAlign: "right" }}>{job.tracks_removed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
