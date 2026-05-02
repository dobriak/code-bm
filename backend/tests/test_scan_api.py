"""Functional tests for the scan API endpoints.

Tests use admin JWT authentication (Phase 4 requirement).
"""

from __future__ import annotations


class TestScanStatusEndpoint:
    async def test_scan_status_returns_list(self, client, admin_headers, session_factory, db_with_settings):
        """Returns list of scan jobs."""
        resp = await client.get("/api/v1/admin/scan/status", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_scan_status_requires_auth(self, client):
        """Requires admin JWT."""
        resp = await client.get("/api/v1/admin/scan/status")
        assert resp.status_code == 401


class TestScanLibraryEndpoint:
    async def test_scan_library_returns_job_id(self, client, admin_headers, session_factory, db_with_settings):
        """Returns scan_job_id and running status."""
        resp = await client.post(
            "/api/v1/admin/scan/library",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "scan_job_id" in data
        assert data["status"] == "running"

    async def test_scan_library_requires_auth(self, client):
        """Requires admin JWT."""
        resp = await client.post("/api/v1/admin/scan/library")
        assert resp.status_code == 401


class TestScanJinglesEndpoint:
    async def test_scan_jingles_returns_job_id(self, client, admin_headers, session_factory, db_with_settings):
        """Returns scan_job_id and running status."""
        resp = await client.post(
            "/api/v1/admin/scan/jingles",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "scan_job_id" in data
        assert data["status"] == "running"
