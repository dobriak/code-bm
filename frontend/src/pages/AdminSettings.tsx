import { useState } from "react";
import { useAdminSettings, useUpdateAdminSettings } from "../api/admin";

export function AdminSettings() {
  const { data, isLoading, error } = useAdminSettings();
  const updateSettings = useUpdateAdminSettings();
  const [saved, setSaved] = useState(false);

  if (isLoading) return <div className="loading">Loading settings...</div>;
  if (error) return <div className="error">Failed to load settings</div>;
  if (!data) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const formData = new FormData(form);
    const updates: Record<string, unknown> = {};

    formData.forEach((value, key) => {
      if (key === "crossfade_enabled" || key === "gapless_enabled") {
        updates[key] = value === "true";
      } else if (key === "default_auto_playlist_id" || key === "min_quiet_duration_s" || key === "icecast_buffer_offset_ms" || key === "crossfade_duration_ms") {
        updates[key] = value === "" ? null : Number(value);
      } else if (key === "jingle_duck_db") {
        updates[key] = parseFloat(value as string);
      } else {
        updates[key] = value;
      }
    });

    try {
      await updateSettings.mutateAsync(updates);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // error handled in mutation
    }
  };

  return (
    <div className="admin-settings">
      <h2>Settings</h2>
      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>Paths</legend>
          <label>
            Library Path
            <input name="library_path" defaultValue={data.library_path} />
          </label>
          <label>
            Jingles Path
            <input name="jingles_path" defaultValue={data.jingles_path} />
          </label>
        </fieldset>

        <fieldset>
          <legend>Playback</legend>
          <label>
            Idle Behavior
            <select name="idle_behavior" defaultValue={data.idle_behavior}>
              <option value="auto_playlist">Auto Playlist</option>
              <option value="random">Random</option>
              <option value="silence">Silence</option>
            </select>
          </label>
          <label>
            Default Auto Playlist
            <select name="default_auto_playlist_id" defaultValue={data.default_auto_playlist_id ?? ""}>
              <option value="">None</option>
              {data.auto_playlists?.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </label>
        </fieldset>

        <fieldset>
          <legend>Crossfade & Gapless</legend>
          <label className="checkbox-label">
            <input
              type="checkbox"
              name="crossfade_enabled"
              value="true"
              defaultChecked={data.crossfade_enabled}
            />
            Enable Crossfade
          </label>
          <label>
            Crossfade Duration (ms)
            <input
              name="crossfade_duration_ms"
              type="number"
              min="0"
              max="10000"
              defaultValue={data.crossfade_duration_ms}
            />
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              name="gapless_enabled"
              value="true"
              defaultChecked={data.gapless_enabled}
            />
            Enable Gapless
          </label>
        </fieldset>

        <fieldset>
          <legend>Jingles</legend>
          <label>
            Jingle Duck Depth (dB)
            <input
              name="jingle_duck_db"
              type="number"
              min="-24"
              max="0"
              step="0.5"
              defaultValue={data.jingle_duck_db}
            />
            <span className="hint">-24 to 0 dB</span>
          </label>
        </fieldset>

        <fieldset>
          <legend>Audio Analysis</legend>
          <label>
            Min Quiet Passage Duration (s)
            <input
              name="min_quiet_duration_s"
              type="number"
              min="1"
              max="10"
              defaultValue={data.min_quiet_duration_s}
            />
          </label>
        </fieldset>

        <fieldset>
          <legend>Icecast</legend>
          <label>
            Icecast Buffer Offset (ms)
            <input
              name="icecast_buffer_offset_ms"
              type="number"
              min="0"
              max="10000"
              defaultValue={data.icecast_buffer_offset_ms}
            />
          </label>
        </fieldset>

        <button type="submit" disabled={updateSettings.isPending}>
          {saved ? "Saved!" : "Save Settings"}
        </button>
      </form>
    </div>
  );
}
