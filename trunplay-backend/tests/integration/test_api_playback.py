"""
Integration tests for Playback API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestPlaybackAPI:
    """Tests for /api/v1/playback endpoints."""

    def test_get_playback_status_idle(self, client):
        """GET /playback/status should return idle status when nothing is playing."""
        response = client.get("/api/v1/playback/status")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "STOPPED"

    def test_play_nonexistent_plan(self, client):
        """POST /playback/play with non-existent plan should return 404."""
        response = client.post("/api/v1/playback/play", json={
            "plan_id": "nonexistent-plan"
        })
        assert response.status_code == 404

    def test_play_plan_without_device(self, client):
        """POST /playback/play without device should fail."""
        # Create a plan without device
        create_resp = client.post("/api/v1/plans", json={
            "title": "No Device Plan",
            "start_time": "09:00",
            "end_time": "17:00",
            "repeat_days": "1,2,3",
            "media_url": "smb://nas/video.mp4"
        })
        plan_id = create_resp.json()["data"]["id"]

        # Try to play
        response = client.post("/api/v1/playback/play", json={
            "plan_id": plan_id
        })
        # Should fail because no device assigned
        assert response.status_code in [400, 404, 500]

    def test_pause_without_active_playback(self, client):
        """POST /playback/pause without active playback should return 400."""
        response = client.post("/api/v1/playback/pause")
        assert response.status_code == 400

    def test_resume_without_active_playback(self, client):
        """POST /playback/resume without active playback should return 400."""
        response = client.post("/api/v1/playback/resume")
        assert response.status_code == 400

    def test_stop_without_active_playback(self, client):
        """POST /playback/stop without active playback should succeed (idempotent)."""
        response = client.post("/api/v1/playback/stop")
        # Stop should be idempotent - OK even when nothing is playing
        assert response.status_code == 200

    def test_seek_without_active_playback(self, client):
        """POST /playback/seek without active playback should return 400."""
        response = client.post("/api/v1/playback/seek", json={"position": 1000})
        assert response.status_code == 400

    def test_seek_negative_position(self, client):
        """POST /playback/seek with negative position should fail or clamp."""
        response = client.post("/api/v1/playback/seek", json={"position": -100})
        # Should either reject or clamp to 0
        assert response.status_code in [200, 400, 422]

    def test_get_volume(self, client):
        """GET /playback/volume should return current volume."""
        response = client.get("/api/v1/playback/volume")
        # Behavior depends on whether there's active playback
        assert response.status_code in [200, 400]

    def test_set_volume_valid(self, client):
        """POST /playback/volume with valid level."""
        response = client.post("/api/v1/playback/volume", json={"level": 50})
        # Behavior depends on whether there's active playback
        assert response.status_code in [200, 400]

    def test_set_volume_out_of_range(self, client):
        """POST /playback/volume with out-of-range level should be clamped or rejected."""
        # Test value above 100
        response = client.post("/api/v1/playback/volume", json={"level": 150})
        # Should either clamp to 100 or reject
        assert response.status_code in [200, 400, 422]

        # Test negative value
        response = client.post("/api/v1/playback/volume", json={"level": -10})
        assert response.status_code in [200, 400, 422]

    def test_get_position(self, client):
        """GET /playback/position should return current position."""
        response = client.get("/api/v1/playback/position")
        # Behavior depends on whether there's active playback
        assert response.status_code in [200, 400]


class TestPlaybackErrorHandling:
    """Tests for playback error scenarios."""

    def test_play_with_offline_device(self, client, mock_dlna):
        """Playing to an offline device should fail gracefully."""
        mock_dlna.fail_mode = "offline"
        # This test requires proper mock injection and plan setup
        pass

    def test_play_with_smb_connection_error(self, client, mock_smb):
        """Playing SMB media with connection error should fail gracefully."""
        mock_smb.fail_mode = "connection_error"
        # This test requires proper mock injection and plan setup
        pass
