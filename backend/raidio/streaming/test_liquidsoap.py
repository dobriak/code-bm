from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raidio.streaming.liquidsoap import (
    CommandError,
    ConnectionError,
    LiquidsoapClient,
    LiquidsoapSettings,
)


@pytest.fixture
def settings():
    return LiquidsoapSettings(host="127.0.0.1", port=1234)


@pytest.fixture
def client(settings):
    return LiquidsoapClient(settings=settings)


class TestLiquidsoapSettings:
    def test_default_values(self):
        settings = LiquidsoapSettings()
        assert settings.host == "127.0.0.1"
        assert settings.port == 1234

    def test_custom_values(self):
        settings = LiquidsoapSettings(host="192.168.1.1", port=5678)
        assert settings.host == "192.168.1.1"
        assert settings.port == 5678

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("liquidsoap_host", "10.0.0.1")
        monkeypatch.setenv("liquidsoap_port", "9999")
        settings = LiquidsoapSettings()
        assert settings.host == "10.0.0.1"
        assert settings.port == 9999


class TestLiquidsoapClientUnit:
    @pytest.mark.asyncio
    async def test_push_returns_request_id(self, client):
        with patch.object(client, "_send_command") as mock_cmd:
            mock_cmd.return_value = "42"
            result = await client.push("/path/to/song.mp3")
            assert result == "42"
            mock_cmd.assert_called_once_with("queue.push /path/to/song.mp3")

    @pytest.mark.asyncio
    async def test_skip_calls_request_queue_skip(self, client):
        with patch.object(client, "_send_command") as mock_cmd:
            mock_cmd.return_value = ""
            await client.skip()
            mock_cmd.assert_called_once_with("request.queue.skip")

    @pytest.mark.asyncio
    async def test_set_var(self, client):
        with patch.object(client, "_send_command") as mock_cmd:
            mock_cmd.return_value = ""
            await client.set_var("crossfade_enabled", "true")
            mock_cmd.assert_called_once_with("var.set crossfade_enabled = true")

    @pytest.mark.asyncio
    async def test_get_var(self, client):
        with patch.object(client, "_send_command") as mock_cmd:
            mock_cmd.return_value = "42.5"
            result = await client.get_var("volume")
            assert result == "42.5"
            mock_cmd.assert_called_once_with("var.get volume")

    @pytest.mark.asyncio
    async def test_queue_size_returns_integer(self, client):
        with patch.object(client, "_send_command") as mock_cmd:
            mock_cmd.return_value = "15"
            result = await client.queue_size()
            assert result == 15

    @pytest.mark.asyncio
    async def test_queue_size_raises_on_invalid_response(self, client):
        with patch.object(client, "_send_command") as mock_cmd:
            mock_cmd.return_value = "not a number"
            with pytest.raises(CommandError):
                await client.queue_size()

    @pytest.mark.asyncio
    async def test_push_with_special_characters(self, client):
        with patch.object(client, "_send_command") as mock_cmd:
            mock_cmd.return_value = "99"
            result = await client.push("http://example.com/song%20with%20spaces.mp3")
            assert result == "99"

    @pytest.mark.asyncio
    async def test_connection_error_propagates(self, client):
        with patch.object(client, "connect", side_effect=ConnectionError("Connection failed")):
            with pytest.raises(ConnectionError):
                await client.push("/test.mp3")

    @pytest.mark.asyncio
    async def test_push_handles_non_numeric_response(self, client):
        with patch.object(client, "_send_command") as mock_cmd:
            mock_cmd.return_value = "OK"
            result = await client.push("/test.mp3")
            assert result == "OK"

    @pytest.mark.asyncio
    async def test_context_manager_connect_and_disconnect(self):
        client = LiquidsoapClient(LiquidsoapSettings(host="127.0.0.1", port=1234))
        with patch.object(client, "connect", new_callable=AsyncMock) as mock_connect:
            with patch.object(client, "disconnect", new_callable=AsyncMock) as mock_disconnect:
                async with client:
                    pass
                mock_connect.assert_called_once()
                mock_disconnect.assert_called_once()


class TestLiquidsoapClientConnection:
    @pytest.mark.asyncio
    async def test_connect_creates_reader_and_writer(self):
        client = LiquidsoapClient(LiquidsoapSettings(host="127.0.0.1", port=12345))
        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_conn:
            mock_conn.return_value = (MagicMock(), MagicMock())
            await client.connect()
            mock_conn.assert_called_once_with("127.0.0.1", 12345)
            assert client._reader is not None
            assert client._writer is not None

    @pytest.mark.asyncio
    async def test_connect_is_idempotent(self):
        client = LiquidsoapClient(LiquidsoapSettings(host="127.0.0.1", port=12345))
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        client._reader = mock_reader
        client._writer = mock_writer
        await client.connect()
        assert client._reader is mock_reader
        assert client._writer is mock_writer

    @pytest.mark.asyncio
    async def test_disconnect_closes_writer(self):
        client = LiquidsoapClient(LiquidsoapSettings(host="127.0.0.1", port=12345))
        mock_writer = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        client._writer = mock_writer
        await client.disconnect()
        mock_writer.close.assert_called_once()
        assert client._writer is None
        assert client._reader is None
