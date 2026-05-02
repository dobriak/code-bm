# Raidio Playlist Format (.raidio)

**Version:** 1
**MIME Type:** `application/json`
**File Extension:** `.raidio`

## Schema

```json
{
  "raidio_version": 1,
  "name": "My Playlist",
  "notes": "Optional playlist notes",
  "items": [
    {
      "type": "track",
      "path": "/absolute/path/to/track.mp3"
    },
    {
      "type": "jingle",
      "path": "/absolute/path/to/jingle.mp3",
      "overlay_at_ms": 12000
    }
  ]
}
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `raidio_version` | integer | Yes | Must be `1`. Reserved for future format evolution. |
| `name` | string | Yes | Playlist name (1–80 characters). |
| `notes` | string | No | Playlist notes (0–500 characters). |
| `items` | array | Yes | At least one item. |
| `items[].type` | string | Yes | Either `"track"` or `"jingle"`. |
| `items[].path` | string | Yes | Absolute filesystem path to the audio file. |
| `items[].overlay_at_ms` | integer | No | For jingles only: millisecond offset into the track at which to play the jingle overlay. |

## Validation Rules

1. `raidio_version` must be `1`. Reject other values.
2. `name` must be non-empty and ≤ 80 characters after trimming whitespace.
3. `items` must contain at least one element.
4. Each item must have a valid `type` (`"track"` or `"jingle"`).
5. Each item must have a non-empty `path`.
6. `overlay_at_ms` is only valid when `type` is `"jingle"`. If present, must be a non-negative integer.
7. Paths are resolved server-side against the configured library/jingles directories.

## Loading Behavior

When loading a `.raidio` file:

1. Parse and validate the JSON structure.
2. Resolve each `path` against the backend's known tracks/jingles via `POST /api/v1/tracks/resolve-paths`.
3. Tracks/jingles not found in the current library are reported as warnings.
4. Valid items are restored to the playlist builder state.
5. If all items fail resolution, show an error toast.

## Saving Behavior

When saving a `.raidio` file:

1. Serialize the current playlist builder state to the format above.
2. Trigger a browser download of the file named `<playlist-name>.raidio`.

## Example

```json
{
  "raidio_version": 1,
  "name": "Friday Night Vibes",
  "notes": "Upbeat tracks for the weekend",
  "items": [
    {
      "type": "track",
      "path": "/music/library/daft-punk-around-the-world.mp3"
    },
    {
      "type": "jingle",
      "path": "/music/jingles/id-call-in.mp3",
      "overlay_at_ms": 45000
    }
  ]
}
```
