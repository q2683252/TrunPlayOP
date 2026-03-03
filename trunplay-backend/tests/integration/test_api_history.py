"""
Integration tests for History API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestHistoryAPI:
    """Tests for /api/v1/history endpoints."""

    def test_list_history_empty(self, client):
        """GET /history should return empty list when no history exists."""
        response = client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_history_pagination(self, client):
        """GET /history should support pagination."""
        response = client.get("/api/v1/history", params={"page": 1, "page_size": 10})
        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "total" in data

    def test_list_history_filter_by_plan(self, client):
        """GET /history?plan_id=xxx should filter by plan."""
        response = client.get("/api/v1/history", params={"plan_id": "some-plan-id"})
        assert response.status_code == 200
        # Should return empty if plan doesn't exist
        assert response.json()["total"] == 0

    def test_list_history_page_size_limit(self, client):
        """GET /history with excessive page_size should be limited."""
        response = client.get("/api/v1/history", params={"page_size": 500})
        # Pydantic validation limits page_size to 100
        assert response.status_code == 422  # Validation error

    def test_get_history_nonexistent(self, client):
        """GET /history/{id} with non-existent ID should return 404."""
        response = client.get("/api/v1/history/nonexistent-id")
        assert response.status_code == 404

    def test_delete_history_nonexistent(self, client):
        """DELETE /history/{id} with non-existent ID should return 404."""
        response = client.delete("/api/v1/history/nonexistent-id")
        assert response.status_code == 404

    def test_clear_history(self, client):
        """DELETE /history should clear all history."""
        response = client.delete("/api/v1/history")
        assert response.status_code == 200
        assert "message" in response.json()

        # Verify cleared
        list_resp = client.get("/api/v1/history")
        assert list_resp.json()["total"] == 0
