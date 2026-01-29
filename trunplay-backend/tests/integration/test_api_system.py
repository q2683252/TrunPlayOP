"""
Integration tests for System API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestSystemAPI:
    """Tests for /api/v1/system endpoints."""

    def test_get_system_status(self, client):
        """GET /system/status should return system status."""
        response = client.get("/api/v1/system/status")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "version" in data
        assert "playback_status" in data

    def test_health_check(self, client):
        """GET /system/health should return health status."""
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "ok"

    def test_get_config(self, client):
        """GET /system/config should return configuration."""
        response = client.get("/api/v1/system/config")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "api_port" in data
        assert "media_port" in data
        assert "local_media_paths" in data


class TestRootEndpoints:
    """Tests for root-level endpoints."""

    def test_root_endpoint(self, client):
        """GET / should return API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data or "version" in data

    def test_health_endpoint(self, client):
        """GET /health should return health status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
