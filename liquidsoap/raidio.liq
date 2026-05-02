#!/usr/bin/env liquidsoap

# Raidio Liquidsoap script with gapless, crossfade, and jingle ducking support
# Environment variables:
#   ICECAST_HOST              - Icecast host (default: 127.0.0.1)
#   ICECAST_PORT              - Icecast port (default: 8000)
#   ICECAST_MOUNT             - Icecast mount point (default: /raidio.mp3)
#   ICECAST_SOURCE_PASSWORD   - Source password for Icecast
#   LIQUIDSOAP_TELNET_PORT    - Telnet control port (default: 1234)

# Enable telnet server for external control
settings.server.telnet.bindings := [
  ("127.0.0.1", 1234)
]

# Crossfade duration variable (controlled by backend, default: 0 = off)
crossfade_duration = ref(0.0)

# Crossfade enabled variable
crossfade_enabled = ref(false)

# Gapless enabled variable
gapless_enabled = ref(true)

# Jingle duck depth (dB, controlled by backend)
jingle_duck_db = ref(-12.0)

# Main request queue for tracks
main_queue = request.queue(id="main")

# Jingles queue for interrupt/live-drop with ducking
jingles_queue = request.queue(id="jingles")

# Apply crossfade if enabled
processed_source = if !crossfade_enabled or !crossfade_duration <= 0.0 then
  main_queue
else
  crossfade(duration=!crossfade_duration, main_queue)
end

# Apply smooth_add for jingle ducking: main plays underneath,
# jingles interrupt with automatic ducking to jingle_duck_db
final_source = smooth_add(
  normal=processed_source,
  special=jingles_queue,
  p=fun(_,_) -> !jingle_duck_db
)

# Output to Icecast with gapless if enabled
output.icecast(
  %mp3,
  host=getenv("ICECAST_HOST", default="127.0.0.1"),
  port=int_of_string(getenv("ICECAST_PORT", default="8000")),
  mount=getenv("ICECAST_MOUNT", default="/raidio.mp3"),
  password=getenv("ICECAST_SOURCE_PASSWORD", default="hackme"),
  final_source
)
