#!/usr/bin/env liquidsoap
# ── Raidio — Liquidsoap audio engine ──────────────────────────────
# Configuration is injected via envsubst by the Taskfile before launch.
# See DESIGN.md §4 for the streaming architecture overview.
#
# This script provides:
#   - A request queue (main) for track playback
#   - A fallback single() source for idle/testing
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

# ── Sources ───────────────────────────────────────────────────────
# Main request queue — backend pushes URIs here via telnet
main_queue = request.queue(id="main")

# Fallback: loop a single test file when the queue is empty
fallback_source = single("${LIQUIDSOAP_FALLBACK_FILE}")

# Combine: play from the queue, fall back to the single file
radio = fallback(track_sensitive=false, [main_queue, fallback_source])

# Make the source safe (never crashes, outputs silence on error)
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
