from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict


class LiquidsoapSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="liquidsoap_")

    host: str = "127.0.0.1"
    port: int = 1234


class LiquidsoapError(Exception):
    pass


class ConnectionError(LiquidsoapError):
    pass


class CommandError(LiquidsoapError):
    pass


@dataclass
class TrackMetadata:
    request_id: str | None
    artist: str | None
    title: str | None
    album: str | None
    duration: float | None


class LiquidsoapClient:
    def __init__(self, settings: LiquidsoapSettings | None = None):
        self.settings = settings or LiquidsoapSettings()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._reader and self._writer:
            return
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.settings.host, self.settings.port
            )
        except OSError as e:
            raise ConnectionError(f"Failed to connect to Liquidsoap: {e}") from e

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self._reader = None

    async def _send_command(self, cmd: str) -> str:
        await self.connect()
        if not self._writer or not self._reader:
            raise ConnectionError("Not connected to Liquidsoap")

        async with self._lock:
            self._writer.write(f"{cmd}\n".encode())
            await self._writer.drain()

            response_lines = []
            while True:
                line = await self._reader.readline()
                if not line:
                    raise ConnectionError("Connection closed by Liquidsoap")
                decoded = line.decode().strip()
                if decoded == "END":
                    break
                if decoded.startswith("ERROR"):
                    raise CommandError(decoded)
                response_lines.append(decoded)

            return "\n".join(response_lines)

    async def push(self, uri: str) -> str:
        result = await self._send_command(f'queue.push {uri}')
        match = re.search(r"^\d+$", result.strip())
        if match:
            return match.group(0)
        return result

    async def push_jingle(self, uri: str) -> str:
        result = await self._send_command(f'queue.pushj {uri}')
        match = re.search(r"^\d+$", result.strip())
        if match:
            return match.group(0)
        return result

    async def skip(self) -> None:
        await self._send_command("request.queue.skip")

    async def set_var(self, name: str, value: str) -> None:
        await self._send_command(f"var.set {name} = {value}")

    async def get_var(self, name: str) -> str:
        result = await self._send_command(f"var.get {name}")
        return result.strip()

    async def set_jingle_duck_db(self, db: float) -> None:
        await self.set_var("jingle_duck_db", str(db))

    async def queue_size(self) -> int:
        result = await self._send_command("queue.length")
        try:
            return int(result.strip())
        except ValueError:
            raise CommandError(f"Unexpected queue size response: {result}")

    async def current_metadata(self) -> TrackMetadata | None:
        await self.connect()
        if not self._reader or not self._writer:
            raise ConnectionError("Not connected")

        async with self._lock:
            self._writer.write(b"queue.current\n")
            await self._writer.drain()

            lines = []
            while True:
                line = await self._reader.readline()
                if not line:
                    raise ConnectionError("Connection closed")
                decoded = line.decode().strip()
                if decoded == "END":
                    break
                lines.append(decoded)

        if not lines or lines[0] == "":
            return None

        metadata: dict[str, str | None] = {
            "request_id": None,
            "artist": None,
            "title": None,
            "album": None,
            "duration": None,
        }

        for line in lines:
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                if key in metadata:
                    metadata[key] = value

        duration_str = metadata.get("duration")
        duration: float | None = None
        if duration_str:
            try:
                duration = float(duration_str)
            except ValueError:
                pass

        return TrackMetadata(
            request_id=metadata.get("request_id"),
            artist=metadata.get("artist"),
            title=metadata.get("title"),
            album=metadata.get("album"),
            duration=duration,
        )

    async def __aenter__(self) -> LiquidsoapClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()
