"""Functional tests for the scan API endpoints."""

from __future__ import annotations

import httpx
import pytest

from raidio.main import app


@pytest.fixture
async def client():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


class TestScanStatusEndpoint:
    async def test_scan_status_returns_list(self, client: httpx.AsyncClient):
        response = await client.get("/api/v1/admin/scan/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestScanLibraryEndpoint:
    async def test_scan_library_returns_job_id(self, client: httpx.AsyncClient):
        response = await client.post("/api/v1/admin/scan/library")
        assert response.status_code == 200
        data = response.json()
        assert "scan_job_id" in data
        assert data["status"] == "running"


class TestScanJinglesEndpoint:
    async def test_scan_jingles_returns_job_id(self, client: httpx.AsyncClient):
        response = await client.post("/api/v1/admin/scan/jingles")
        assert response.status_code == 200
        data = response.json()
        assert "scan_job_id" in data
        assert data["status"] == "running"
