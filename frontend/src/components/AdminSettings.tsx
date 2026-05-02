/**
 * AdminSettings — form to view and edit all admin settings.
 * Changes take effect immediately (Liquidsoap vars pushed on save).
 */

import { useCallback, useEffect, useState } from "react";
import type { AdminSettings, AdminSettingsUpdate } from "../api/client";
import { fetchAdminSettings, updateAdminSettings } from "../api/client";

export default function AdminSettingsPanel() {
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [libraryPath, setLibraryPath] = useState("");
  const [jinglesPath, setJinglesPath] = useState("");
  const [idleBehavior, setIdleBehavior] = useState("random");
  const [crossfadeEnabled, setCrossfadeEnabled] = useState(false);
  const [crossfadeDuration, setCrossfadeDuration] = useState(4);
  const [gaplessEnabled, setGaplessEnabled] = useState(true);
  const [jingleDuckDb, setJingleDuckDb] = useState(-12);
  const [bufferOffset, setBufferOffset] = useState(3000);
  const [minQuietDuration, setMinQuietDuration] = useState(2);

  useEffect(() => {
    fetchAdminSettings()
      .then((s) => {
        setSettings(s);
        setLibraryPath(s.library_path);
        setJinglesPath(s.jingles_path);
        setIdleBehavior(s.idle_behavior);
        setCrossfadeEnabled(s.crossfade_enabled);
        setCrossfadeDuration(s.crossfade_duration_ms / 1000);
        setGaplessEnabled(s.gapless_enabled);
        setJingleDuckDb(s.jingle_duck_db);
        setBufferOffset(s.icecast_buffer_offset_ms);
        setMinQuietDuration(s.min_quiet_duration_s);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      const body: AdminSettingsUpdate = {
        crossfade_enabled: crossfadeEnabled,
        crossfade_duration_ms: crossfadeDuration * 1000,
        gapless_enabled: gaplessEnabled,
        jingle_duck_db: jingleDuckDb,
        icecast_buffer_offset_ms: bufferOffset,
        min_quiet_duration_s: minQuietDuration,
        idle_behavior: idleBehavior,
        library_path: libraryPath,
        jingles_path: jinglesPath,
      };
      const updated = await updateAdminSettings(body);
      setSettings(updated);
      setToast("Settings saved — changes applied");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
      setTimeout(() => setToast(null), 4000);
    }
  }, [
    crossfadeEnabled, crossfadeDuration, gaplessEnabled,
    jingleDuckDb, bufferOffset, minQuietDuration, idleBehavior,
    libraryPath, jinglesPath,
  ]);

  if (loading) {
    return (
      <div style={{ padding: "1.5rem" }}>
        <h2 style={{ marginBottom: "1.5rem" }}>Settings</h2>
        <div style={{ color: "#666" }}>Loading…</div>
      </div>
    );
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: "800px", margin: "0 auto" }}>
      <h2 style={{ marginBottom: "1.5rem" }}>Settings</h2>

      {error && (
        <div
          style={{
            padding: "0.625rem 0.75rem",
            backgroundColor: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "0.5rem",
            color: "#ef4444",
            fontSize: "0.8125rem",
            marginBottom: "1rem",
          }}
        >
          {error}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {/* Paths */}
        <Section title="Paths">
          <Field label="Library Path">
            <input
              type="text"
              value={libraryPath}
              onChange={(e) => setLibraryPath(e.target.value)}
              style={inputStyle}
            />
          </Field>
          <Field label="Jingles Path">
            <input
              type="text"
              value={jinglesPath}
              onChange={(e) => setJinglesPath(e.target.value)}
              style={inputStyle}
            />
          </Field>
        </Section>

        {/* Playback */}
        <Section title="Playback">
          <Field label="Idle Behavior">
            <select
              value={idleBehavior}
              onChange={(e) => setIdleBehavior(e.target.value)}
              style={inputStyle}
            >
              <option value="random">Random Track</option>
              <option value="auto_playlist">Auto-Playlist</option>
              <option value="silence">Silence</option>
            </select>
          </Field>

          <Field label="Crossfade">
            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <ToggleSwitch
                checked={crossfadeEnabled}
                onChange={setCrossfadeEnabled}
              />
              {crossfadeEnabled && (
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.5"
                    value={crossfadeDuration}
                    onChange={(e) => setCrossfadeDuration(parseFloat(e.target.value))}
                    style={{ width: "120px", accentColor: "#fafafa" }}
                  />
                  <span style={{ fontSize: "0.75rem", color: "#888", minWidth: "3rem" }}>
                    {crossfadeDuration}s
                  </span>
                </div>
              )}
            </div>
          </Field>

          <Field label="Gapless Playback">
            <ToggleSwitch checked={gaplessEnabled} onChange={setGaplessEnabled} />
          </Field>

          <Field label="Jingle Duck Depth">
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <input
                type="range"
                min="-24"
                max="0"
                step="1"
                value={jingleDuckDb}
                onChange={(e) => setJingleDuckDb(parseFloat(e.target.value))}
                style={{ width: "120px", accentColor: "#fafafa" }}
              />
              <span style={{ fontSize: "0.75rem", color: "#888", minWidth: "4rem" }}>
                {jingleDuckDb} dB
              </span>
            </div>
          </Field>
        </Section>

        {/* Advanced */}
        <Section title="Advanced">
          <Field label="Icecast Buffer Offset (ms)">
            <input
              type="number"
              min="0"
              max="10000"
              value={bufferOffset}
              onChange={(e) => setBufferOffset(parseInt(e.target.value, 10))}
              style={inputStyle}
            />
            <span style={{ fontSize: "0.6875rem", color: "#555" }}>
              Delays now-playing UI to match what listeners hear
            </span>
          </Field>

          <Field label="Min Quiet-Passage Duration (s)">
            <input
              type="number"
              min="1"
              max="10"
              step="0.5"
              value={minQuietDuration}
              onChange={(e) => setMinQuietDuration(parseFloat(e.target.value))}
              style={inputStyle}
            />
            <span style={{ fontSize: "0.6875rem", color: "#555" }}>
              Minimum silence duration for audio analysis detection
            </span>
          </Field>
        </Section>
      </div>

      {/* Save button */}
      <div style={{ marginTop: "2rem" }}>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: "0.75rem 2rem",
            fontSize: "0.875rem",
            fontWeight: 600,
            border: "none",
            borderRadius: "0.5rem",
            backgroundColor: saving ? "#333" : "#fafafa",
            color: saving ? "#666" : "#0f0f0f",
            cursor: saving ? "not-allowed" : "pointer",
            transition: "all 0.2s ease",
          }}
        >
          {saving ? "Saving…" : "Save Settings"}
        </button>
      </div>

      {/* Toast */}
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: "1.5rem",
            left: "50%",
            transform: "translateX(-50%)",
            padding: "0.75rem 1.5rem",
            backgroundColor: "#22c55e",
            color: "#0f0f0f",
            borderRadius: "0.5rem",
            fontSize: "0.875rem",
            fontWeight: 600,
            zIndex: 100,
          }}
        >
          {toast}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        padding: "1.25rem",
        backgroundColor: "#141414",
        border: "1px solid #222",
        borderRadius: "0.75rem",
      }}
    >
      <h3
        style={{
          fontSize: "0.875rem",
          fontWeight: 600,
          color: "#ccc",
          marginBottom: "1rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {title}
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {children}
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label
        style={{
          display: "block",
          fontSize: "0.75rem",
          color: "#888",
          marginBottom: "0.375rem",
          fontWeight: 500,
        }}
      >
        {label}
      </label>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
        {children}
      </div>
    </div>
  );
}

function ToggleSwitch({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
}) {
  return (
    <button
      onClick={() => onChange(!checked)}
      style={{
        width: "44px",
        height: "24px",
        borderRadius: "12px",
        border: "none",
        backgroundColor: checked ? "#22c55e" : "#333",
        position: "relative",
        cursor: "pointer",
        transition: "background-color 0.2s ease",
      }}
    >
      <span
        style={{
          position: "absolute",
          top: "2px",
          left: checked ? "22px" : "2px",
          width: "20px",
          height: "20px",
          borderRadius: "50%",
          backgroundColor: "#fafafa",
          transition: "left 0.2s ease",
        }}
      />
    </button>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.5rem 0.75rem",
  fontSize: "0.8125rem",
  backgroundColor: "#111",
  border: "1px solid #333",
  borderRadius: "0.375rem",
  color: "#fafafa",
  outline: "none",
  boxSizing: "border-box",
};
