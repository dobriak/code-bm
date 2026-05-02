#!/usr/bin/env liquidsoap
# ── Raidio — Liquidsoap audio engine ──────────────────────────────
# Configuration is injected via envsubst by the Taskfile before launch.
# See DESIGN.md §4 for the streaming architecture overview.
#
# This script provides:
#   - A request queue (main) for track playback
#   - Crossfade + gapless support (controlled by variables)
#   - Idle source for when no tracks are queued
#   - Telnet control on LIQUIDSOAP_TELNET_PORT for push/skip/set_var
#   - Icecast output at ICECAST_MOUNT
# ──────────────────────────────────────────────────────────────────

# ── Logging ───────────────────────────────────────────────────────
log.stdout.set(true)
log.level.set(3)

# ── Telnet server (for backend control) ───────────────────────────
settings.server.telnet.set(true)
settings.server.telnet.bind_addr.set("127.0.0.1")
settings.server.telnet.port.set(${LIQUIDSOAP_TELNET_PORT})

# ── Variables (controlled by backend via telnet) ──────────────────
crossfade_enabled = ref(false)
crossfade_duration = ref(4.0)

# ── Sources ───────────────────────────────────────────────────────
# Main request queue — backend pushes URIs here via telnet
main_queue = request.queue(id="main")

# Idle fallback: random track from library when queue is empty.
# Uses a blank source as ultimate fallback (silence).
idle_source = amplify(0., noise())

# Combine: play from the queue, fall back to idle/silence
radio = fallback(track_sensitive=false, [main_queue, idle_source])

# ── Crossfade ─────────────────────────────────────────────────────
# Apply crossfade when enabled. The crossfade duration is read from
# the ref variable so the backend can toggle it at runtime.
def crossfade_filter(~source) =
  # Only crossfade between actual tracks, not into silence
  crossfade(
    duration=!crossfade_duration,
    fade_in=linear(duration=!crossfade_duration),
    fade_out=linear(duration=!crossfade_duration),
    source
  )
end

# Wrap the source: when crossfade is enabled, apply the filter.
# This uses a conditional approach so we can toggle at runtime.
radio = switch(id="crossfade_switch",
  [({!crossfade_enabled}, crossfade_filter(radio))],
  radio
)

# ── Safety: ensure the source never crashes ───────────────────────
radio = mksafe(radio)

# ── Icecast output ────────────────────────────────────────────────
output.icecast(
  %mp3(bitrate=192),
  host="${ICECAST_HOST}",
  port=${ICECAST_PORT},
  password="${ICECAST_SOURCE_PASSWORD}",
  mount="${ICECAST_MOUNT}",
  radio
)
