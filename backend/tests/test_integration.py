"""Integration test: health endpoint and Icecast stream availability.

These tests require `dev:icecast` and `dev:liquidsoap` to be running.
They are marked with the 'integration' marker so they can be skipped in CI.
"""

from __future__ import annotations

import httpx
import pytest

from raidio.main import app

# Marker for integration tests (requires external services)
pytestmark = pytest.mark.integration


ICECAST_STREAM_URL = "http://127.0.0.1:8000/raidio.mp3"


@pytest.fixture
async def client():
    """Async HTTP client for testing the FastAPI app."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


class TestHealthEndpoint:
    """Test the health endpoint (no external services needed)."""

    async def test_health_returns_ok(self, client: httpx.AsyncClient):
        """GET /api/v1/health returns status ok and version."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestIcecastStream:
    """Test Icecast is serving the audio stream.

    These tests are skipped if Icecast is not running.
    """

    @pytest.fixture(autouse=True)
    def _check_icecast_available(self):
        """Skip test if Icecast is not responding."""
        try:
            import socket

            sock = socket.create_connection(("127.0.0.1", 8000), timeout=2)
            sock.close()
        except (ConnectionRefusedError, OSError):
            pytest.skip("Icecast not running — start with `task dev:icecast`")

    async def test_icecast_responds_with_audio_mpeg(self):
        """Icecast mount point returns 200 with audio/mpeg content type."""
        async with httpx.AsyncClient(timeout=5.0) as c:
            response = await c.get(ICECAST_STREAM_URL, follow_redirects=True)
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "audio/mpeg" in content_type or "audio/mp3" in content_type

    async def test_icecast_has_cors_headers(self):
        """Icecast sends Access-Control-Allow-Origin header."""
        async with httpx.AsyncClient(timeout=5.0) as c:
            response = await c.options(
                ICECAST_STREAM_URL,
                headers={"Origin": "http://localhost:5173"},
            )
            cors = response.headers.get("Access-Control-Allow-Origin", "")
            assert cors == "*"
