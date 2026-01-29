"""
Integration tests for Plan API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestPlanAPI:
    """Tests for /api/v1/plans endpoints."""

    def test_list_plans_empty(self, client):
        """GET /plans should return empty list when no plans exist."""
        response = client.get("/api/v1/plans")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["items"] == []

    def test_create_plan(self, client):
        """POST /plans should create a new plan."""
        plan_data = {
            "title": "Morning Routine",
            "start_time": "08:00",
            "end_time": "09:00",
            "repeat_days": "1,2,3,4,5",
            "media_url": "smb://nas/morning.mp4"
        }
        response = client.post("/api/v1/plans", json=plan_data)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["title"] == "Morning Routine"
        assert "id" in data["data"]

    def test_create_plan_with_all_fields(self, client):
        """POST /plans with all optional fields."""
        plan_data = {
            "title": "Full Plan",
            "start_time": "08:00",
            "end_time": "18:00",
            "repeat_days": "1,2,3,4,5,6,7",
            "skip_holidays": True,
            "device_id": "device-123",
            "media_url": "smb://nas/video.mp4",
            "is_active": False,
            "play_mode": "LOOP"
        }
        response = client.post("/api/v1/plans", json=plan_data)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["skip_holidays"] is True
        assert data["is_active"] is False
        assert data["play_mode"] == "LOOP"

    def test_get_plan_existing(self, client):
        """GET /plans/{id} should return the plan."""
        # First create a plan
        create_resp = client.post("/api/v1/plans", json={
            "title": "Test Plan",
            "start_time": "09:00",
            "end_time": "17:00",
            "repeat_days": "1,2,3",
            "media_url": "smb://nas/video.mp4"
        })
        plan_id = create_resp.json()["data"]["id"]

        # Then get it
        response = client.get(f"/api/v1/plans/{plan_id}")
        assert response.status_code == 200
        assert response.json()["data"]["id"] == plan_id

    def test_get_plan_nonexistent(self, client):
        """GET /plans/{id} should return 404 for non-existent plan."""
        response = client.get("/api/v1/plans/nonexistent-id")
        assert response.status_code == 404

    def test_update_plan(self, client):
        """PUT /plans/{id} should update the plan."""
        # Create
        create_resp = client.post("/api/v1/plans", json={
            "title": "Original",
            "start_time": "09:00",
            "end_time": "17:00",
            "repeat_days": "1,2,3",
            "media_url": "smb://nas/video.mp4"
        })
        plan_id = create_resp.json()["data"]["id"]

        # Update
        response = client.put(f"/api/v1/plans/{plan_id}", json={
            "title": "Updated"
        })
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "Updated"

    def test_update_plan_nonexistent(self, client):
        """PUT /plans/{id} should return 404 for non-existent plan."""
        response = client.put("/api/v1/plans/nonexistent", json={"title": "New"})
        assert response.status_code == 404

    def test_delete_plan(self, client):
        """DELETE /plans/{id} should delete the plan."""
        # Create
        create_resp = client.post("/api/v1/plans", json={
            "title": "To Delete",
            "start_time": "09:00",
            "end_time": "17:00",
            "repeat_days": "1,2,3",
            "media_url": "smb://nas/video.mp4"
        })
        plan_id = create_resp.json()["data"]["id"]

        # Delete
        response = client.delete(f"/api/v1/plans/{plan_id}")
        assert response.status_code == 200

        # Verify deleted
        get_resp = client.get(f"/api/v1/plans/{plan_id}")
        assert get_resp.status_code == 404

    def test_delete_plan_nonexistent(self, client):
        """DELETE /plans/{id} should return 404 for non-existent plan."""
        response = client.delete("/api/v1/plans/nonexistent")
        assert response.status_code == 404

    def test_activate_plan(self, client):
        """POST /plans/{id}/activate should activate the plan."""
        # Create inactive plan
        create_resp = client.post("/api/v1/plans", json={
            "title": "Inactive Plan",
            "start_time": "09:00",
            "end_time": "17:00",
            "repeat_days": "1,2,3",
            "media_url": "smb://nas/video.mp4",
            "is_active": False
        })
        plan_id = create_resp.json()["data"]["id"]

        # Activate
        response = client.post(f"/api/v1/plans/{plan_id}/activate")
        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is True

    def test_deactivate_plan(self, client):
        """POST /plans/{id}/deactivate should deactivate the plan."""
        # Create active plan
        create_resp = client.post("/api/v1/plans", json={
            "title": "Active Plan",
            "start_time": "09:00",
            "end_time": "17:00",
            "repeat_days": "1,2,3",
            "media_url": "smb://nas/video.mp4",
            "is_active": True
        })
        plan_id = create_resp.json()["data"]["id"]

        # Deactivate
        response = client.post(f"/api/v1/plans/{plan_id}/deactivate")
        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    def test_reset_plan_progress(self, client):
        """POST /plans/{id}/reset-progress should reset progress."""
        # Create plan
        create_resp = client.post("/api/v1/plans", json={
            "title": "Progress Plan",
            "start_time": "09:00",
            "end_time": "17:00",
            "repeat_days": "1,2,3",
            "media_url": "smb://nas/video.mp4"
        })
        plan_id = create_resp.json()["data"]["id"]

        # Reset progress
        response = client.post(f"/api/v1/plans/{plan_id}/reset-progress")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["last_playback_position"] == 0
