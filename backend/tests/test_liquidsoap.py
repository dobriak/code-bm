"""Unit tests for the Liquidsoap telnet client.

Uses an asyncio TCP server to simulate Liquidsoap's telnet protocol.
"""

from __future__ import annotations

import asyncio
import contextlib

import pytest

from raidio.streaming.liquidsoap import (
    LiquidsoapClient,
    LiquidsoapCommandError,
    LiquidsoapConnectionError,
    Metadata,
)


class FakeLiquidsoapServer:
    """Simulates Liquidsoap's telnet protocol for testing.

    Protocol:
    - Client sends a command line
    - Server echoes the command, then sends response lines, then 'END'
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None
        self.recorded_commands: list[str] = []

    async def start(self) -> int:
        self._server = await asyncio.start_server(self._handle_connection, self.host, self.port)
        # Get the actual bound port
        sockets = self._server.sockets  # type: ignore[union-attr]
        if sockets:
            return sockets[0].getsockname()[1]
        return self.port

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                line = data.decode().strip()
                self.recorded_commands.append(line)

                # Simulate Liquidsoap responses
                response = self._generate_response(line)

                writer.write(f"{line}\n".encode())
                if response:
                    for resp_line in response:
                        writer.write(f"{resp_line}\n".encode())
                writer.write(b"END\n")
                await writer.drain()
        except (TimeoutError, ConnectionError):
            pass
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    def _generate_response(self, command: str) -> list[str]:
        """Generate Liquidsoap-style responses for known commands.

        Mimics the real Liquidsoap 2.2.x telnet protocol:
        - ``main.push <uri>`` returns a request ID
        - ``main.skip`` returns "Done."
        - ``main.queue`` returns queued items (empty = no lines)
        - ``request.on_air`` returns the current request ID
        - ``request.metadata <rid>`` returns key=value metadata pairs
        """
        cmd = command.strip()

        if cmd.startswith("main.push"):
            uri = command.split('"')[1] if '"' in command else "unknown"
            return [str(abs(hash(uri)) % 10000)]

        if cmd == "main.skip":
            return ["Done."]

        if cmd.startswith("var.set"):
            return ["Variable updated."]

        if cmd == "main.queue":
            # Empty queue: no item lines between echo and END
            return []

        if cmd == "request.on_air":
            return ["0"]

        if cmd == "request.metadata 0":
            return [
                'rid="0"',
                'status="playing"',
                'initial_uri="/music/test.mp3"',
                'filename="/music/test.mp3"',
                'title="Test Song"',
                'artist="Test Artist"',
                'album="Test Album"',
            ]

        return []


@pytest.fixture
async def fake_server():
    """Start a fake Liquidsoap server and return (server, port)."""
    server = FakeLiquidsoapServer()
    port = await server.start()
    yield server, port
    await server.stop()


@pytest.fixture
async def client(fake_server):
    """Create a LiquidsoapClient connected to the fake server."""
    _server, port = fake_server
    ls = LiquidsoapClient(host="127.0.0.1", port=port)
    await ls.connect()
    yield ls
    await ls.close()


class TestLiquidsoapClient:
    """Tests for LiquidsoapClient against the fake server."""

    async def test_connect_success(self, fake_server):
        """Client connects successfully to a running server."""
        _server, port = fake_server
        ls = LiquidsoapClient(host="127.0.0.1", port=port)
        await ls.connect()
        assert ls._reader is not None
        assert ls._writer is not None
        await ls.close()

    async def test_connect_failure(self):
        """Client raises LiquidsoapConnectionError when server is unreachable."""
        ls = LiquidsoapClient(host="127.0.0.1", port=19999)
        with pytest.raises(LiquidsoapConnectionError):
            await ls.connect()

    async def test_push(self, client, fake_server):
        """push() sends the correct telnet command and returns a response."""
        result = await client.push("/music/test.mp3")
        assert result != ""
        assert 'main.push "/music/test.mp3"' in fake_server[0].recorded_commands

    async def test_skip(self, client, fake_server):
        """skip() sends the skip command."""
        await client.skip()
        assert "main.skip" in fake_server[0].recorded_commands

    async def test_set_var(self, client, fake_server):
        """set_var() sends the correct variable assignment."""
        await client.set_var("crossfade_enabled", "true")
        assert "var.set crossfade_enabled = true" in fake_server[0].recorded_commands

    async def test_queue_size(self, client):
        """queue_size() returns an integer."""
        size = await client.queue_size()
        assert isinstance(size, int)

    async def test_current_metadata(self, client):
        """current_metadata() returns parsed Metadata."""
        meta = await client.current_metadata()
        assert isinstance(meta, Metadata)
        assert meta.artist == "Test Artist"
        assert meta.title == "Test Song"
        assert meta.album == "Test Album"
        assert meta.uri == "/music/test.mp3"

    async def test_command_error(self, fake_server):
        """LiquidsoapCommandError is raised when server returns ERROR."""
        _server, port = fake_server

        # Save the original before replacing
        original_generate = FakeLiquidsoapServer._generate_response

        def error_response(self_inner, command: str) -> list[str]:
            if command.strip().startswith("main.push"):
                return ["ERROR: No such file"]
            return original_generate(self_inner, command)

        FakeLiquidsoapServer._generate_response = error_response
        try:
            ls = LiquidsoapClient(host="127.0.0.1", port=port)
            await ls.connect()

            with pytest.raises(LiquidsoapCommandError, match="No such file"):
                await ls.push("/nonexistent.mp3")

            await ls.close()
        finally:
            FakeLiquidsoapServer._generate_response = original_generate

    async def test_not_connected_raises(self):
        """Operations raise LiquidsoapConnectionError when not connected."""
        ls = LiquidsoapClient()
        with pytest.raises(LiquidsoapConnectionError, match="Not connected"):
            await ls.skip()

    async def test_reconnect(self, fake_server):
        """connect() closes existing connection and opens a new one."""
        _server, port = fake_server
        ls = LiquidsoapClient(host="127.0.0.1", port=port)
        await ls.connect()
        first_writer = ls._writer
        await ls.connect()
        assert ls._writer is not first_writer
        await ls.close()
