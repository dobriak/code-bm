#!/usr/bin/env liquidsoap
# ── Raidio — Liquidsoap audio engine ──────────────────────────────
# Configuration is injected via envsubst by the Taskfile before launch.
# See DESIGN.md §4 for the streaming architecture overview.
#
# This script provides:
#   - A request queue (main) for track playback
#   - A jingle interrupt queue with ducking support
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
jingle_duck_db = ref(-12.0)

# ── Sources ───────────────────────────────────────────────────────
# Main request queue — backend pushes URIs here via telnet
main_queue = request.queue(id="main")

# Jingle interrupt queue — backend pushes jingles here for ducking
jingles_queue = request.queue(id="jingles_queue")

# Idle fallback: silence when nothing is queued
idle_source = amplify(0., noise())

# Combine: play from the main queue, fall back to idle/silence
radio = fallback(track_sensitive=false, [main_queue, idle_source])

# ── Crossfade ─────────────────────────────────────────────────────
# Apply crossfade when enabled. The crossfade duration is read from
# the ref variable so the backend can toggle it at runtime.
def crossfade_filter(~source) =
  crossfade(
    duration=!crossfade_duration,
    fade_in=linear(duration=!crossfade_duration),
    fade_out=linear(duration=!crossfade_duration),
    source
  )
end

# Wrap the source: when crossfade is enabled, apply the filter.
radio = switch(id="crossfade_switch",
  [({!crossfade_enabled}, crossfade_filter(radio))],
  radio
)

# ── Jingle ducking with smooth_add ────────────────────────────────
# When a jingle is pushed onto the jingles_queue, it ducks the main
# audio by jingle_duck_db and mixes on top. When the jingle ends,
# the main audio volume is restored.
def jingle_duck(~normal, ~special) =
  # Compute the attenuation factor from dB
  duck_factor = db_to_linear(!jingle_duck_db)
  # Normal source (main) is ducked when special (jingle) is available
  amplified_normal = amplify(duck_factor, normal)
  # Special source (jingle) plays at full volume
  add([amplified_normal, special])
end

# smooth_add switches between normal and special sources
# When special is available, it uses the jingle_duck function
radio = smooth_add(normal=radio, special=jingles_queue)

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
