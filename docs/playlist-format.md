# Raidio Playlist Format (`.raidio`)

Playlists can be saved to and loaded from `.raidio` files — JSON documents with a `.raidio` extension.

## Format Specification

```json
{
  "raidio_version": 1,
  "name": "My Awesome Mix",
  "notes": "Friday evening vibes",
  "items": [
    {
      "type": "track",
      "id": 42,
      "artist": "Daft Punk",
      "title": "Get Lucky",
      "album": "Random Access Memories",
      "overlay_at_ms": null
    },
    {
      "type": "jingle",
      "id": 3,
      "artist": null,
      "title": "Station ID",
      "album": null,
      "overlay_at_ms": 12000
    }
  ]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `raidio_version` | integer | yes | Format version. Currently `1`. |
| `name` | string | yes | Playlist name (≤ 200 chars) |
| `notes` | string | no | Freeform notes (≤ 500 chars) |
| `items` | array | yes | Ordered list of tracks/jingles |

### Item Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"track"` \| `"jingle"` | yes | Whether this item is a library track or a jingle |
| `id` | integer | yes | Track or jingle ID in the Raidio database |
| `artist` | string \| null | no | Cached artist name (for display when loading) |
| `title` | string \| null | no | Cached title (for display when loading) |
| `album` | string \| null | no | Cached album name |
| `overlay_at_ms` | integer \| null | no | If set, jingle overlays the previous track at this offset (ms) |

## Behavior

- **Save:** The playlist creator serializes the current builder state and triggers a browser download.
- **Load:** A file picker opens the `.raidio` file, validates the structure, and restores the builder state.
- **Mismatch handling:** If tracks in the file don't exist in the current library (e.g., after a re-scan), the loader reports which items couldn't be found and loads the rest with a warning toast.
- **Round-trip fidelity:** Saving and loading preserves item order, names, notes, and overlay positions.

## File Extension

Files use the `.raidio` extension but are valid JSON. The extension is cosmetic — the parser accepts `.raidio` or `.json`.
