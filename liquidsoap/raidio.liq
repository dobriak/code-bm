#!/usr/bin/env liquidsoap

# Raidio Liquidsoap baseline script
# Environment variables:
#   ICECAST_HOST     - Icecast host (default: 127.0.0.1)
#   ICECAST_PORT     - Icecast port (default: 8000)
#   ICECAST_MOUNT    - Icecast mount point (default: /raidio.mp3)
#   ICECAST_SOURCE_PASSWORD - Source password for Icecast
#   LIQUIDSOAP_TELNET_PORT - Telnet control port (default: 1234)
#   TEST_MP3_PATH    - Path to test MP3 file for fallback

# Enable telnet server for external control
settings.server.telnet.bindings := [
  ("127.0.0.1", 1234)
]

# Test MP3 file path (default: ./test.mp3 in the same directory as the script)
test_mp3_path = getenv("TEST_MP3_PATH", default="./test.mp3")

# Main request queue for tracks
main = request.queue(id="main")

# Fallback single track for when queue is empty
fallback = single(test_mp3_path)

# Combine queue with fallback
source = fallback({main})

# Output to Icecast
output.icecast(
  %mp3,
  host=getenv("ICECAST_HOST", default="127.0.0.1"),
  port=int_of_string(getenv("ICECAST_PORT", default="8000")),
  mount=getenv("ICECAST_MOUNT", default="/raidio.mp3"),
  password=getenv("ICECAST_SOURCE_PASSWORD", default="hackme"),
  source
)