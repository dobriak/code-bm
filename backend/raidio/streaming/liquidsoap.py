"""Async telnet client for controlling Liquidsoap.

Connects to Liquidsoap's telnet interface to push tracks, skip, and
read metadata. Connection is pooled with automatic reconnection.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class LiquidsoapError(Exception):
    """Base exception for Liquidsoap client errors."""


class LiquidsoapConnectionError(LiquidsoapError):
    """Failed to connect to Liquidsoap telnet server."""


class LiquidsoapCommandError(LiquidsoapError):
    """Liquidsoap rejected a command."""


@dataclass
class Metadata:
    """Parsed metadata from Liquidsoap's current track."""

    artist: str = ""
    title: str = ""
    album: str = ""
    uri: str = ""


class LiquidsoapClient:
    """Async telnet client for Liquidsoap.

    Usage::

        client = LiquidsoapClient(host="127.0.0.1", port=1234)
        await client.connect()
        await client.push("/path/to/track.mp3")
        meta = await client.current_metadata()
        await client.close()
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 1234) -> None:
        self._host = host
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Open the telnet connection. Reconnects if already open."""
        await self.close()
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=5.0,
            )
            logger.info("Connected to Liquidsoap at %s:%d", self._host, self._port)
        except (TimeoutError, ConnectionRefusedError, OSError) as exc:
            raise LiquidsoapConnectionError(
                f"Cannot connect to Liquidsoap at {self._host}:{self._port}: {exc}"
            ) from exc

    async def close(self) -> None:
        """Close the telnet connection."""
        if self._writer:
            self._writer.close()
            with contextlib.suppress(Exception):
                await self._writer.wait_closed()
            self._writer = None
            self._reader = None

    def _ensure_connected(self) -> None:
        """Raise if not connected."""
        if self._writer is None or self._reader is None:
            raise LiquidsoapConnectionError("Not connected to Liquidsoap")

    async def _send_command(self, command: str) -> str:
        """Send a telnet command and read the response.

        Liquidsoap telnet protocol:
        - Commands are sent as text lines
        - Response ends with a line starting with 'END'
        - Empty response still has 'END'
        """
        self._ensure_connected()

        async with self._lock:
            self._writer.write(f"{command}\n".encode())  # type: ignore[union-attr]
            await self._writer.drain()  # type: ignore[union-attr]

            lines: list[str] = []
            while True:
                try:
                    raw = await asyncio.wait_for(
                        self._reader.readline(),
                        timeout=10.0,  # type: ignore[arg-type]
                    )
                except (TimeoutError, ConnectionError) as exc:
                    raise LiquidsoapConnectionError(
                        f"Lost connection to Liquidsoap: {exc}"
                    ) from exc

                if not raw:
                    raise LiquidsoapConnectionError("Liquidsoap closed connection")

                line = raw.decode().rstrip("\r\n")

                if line == "END":
                    break

                lines.append(line)

            # First line is the command echo, rest is response
            response = "\n".join(lines[1:]) if lines else ""

            # Check for error responses
            if response.startswith("ERROR"):
                raise LiquidsoapCommandError(f"Liquidsoap command failed: {response}")

            return response

    async def push(self, uri: str) -> str:
        """Push a URI onto the main request queue.

        Args:
            uri: File path or URL to queue for playback.

        Returns:
            The request ID assigned by Liquidsoap.

        Raises:
            LiquidsoapCommandError: If the push fails.
        """
        response = await self._send_command(f'main.push "{uri}"')
        logger.info("Pushed %s to Liquidsoap queue", uri)
        return response.strip()

    async def push_jingle(self, uri: str) -> str:
        """Push a URI onto the jingle interrupt queue.

        Args:
            uri: File path or URL to queue for jingle playback.

        Returns:
            The request ID assigned by Liquidsoap.

        Raises:
            LiquidsoapCommandError: If the push fails.
        """
        response = await self._send_command(f'jingles_queue.push "{uri}"')
        logger.info("Pushed jingle %s to Liquidsoap jingle queue", uri)
        return response.strip()

    async def skip(self) -> None:
        """Skip the currently playing track."""
        response = await self._send_command("main.skip")
        logger.info("Skipped current track: %s", response.strip())

    async def set_var(self, name: str, value: str) -> None:
        """Set a Liquidsoap variable.

        Args:
            name: Variable name (e.g. 'crossfade_enabled').
            value: New value.
        """
        response = await self._send_command(f"var.set {name} = {value}")
        logger.debug("Set var %s = %s: %s", name, value, response.strip())

    async def queue_size(self) -> int:
        """Return the number of pending items in the main queue.

        Uses ``main.queue`` and counts non-empty lines in the response.
        """
        response = await self._send_command("main.queue")
        # Response has empty lines for each queued item; count them
        # If the queue is empty, response is a single empty line
        lines = [line for line in response.splitlines() if line.strip()]
        return len(lines)

    async def current_metadata(self) -> Metadata:
        """Get metadata for the currently playing track.

        First gets the on-air request ID via ``request.on_air``,
        then fetches full metadata via ``request.metadata <rid>``.

        Returns:
            Metadata with artist, title, album, and uri fields.
        """
        # Get the currently playing request ID
        rid_response = await self._send_command("request.on_air")
        rid = rid_response.strip()

        meta = Metadata()
        if not rid or rid == "":
            return meta

        # Fetch metadata for this request
        response = await self._send_command(f"request.metadata {rid}")

        for line in response.strip().splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip().lower()
                value = value.strip().strip('"')
                if key == "artist":
                    meta.artist = value
                elif key == "title":
                    meta.title = value
                elif key == "album":
                    meta.album = value
                elif key in ("initial_uri", "filename", "source_url"):
                    meta.uri = value

        return meta
