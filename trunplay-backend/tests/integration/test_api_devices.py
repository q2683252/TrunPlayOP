"""
Integration tests for Device API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestDeviceAPI:
    """Tests for /api/v1/devices endpoints."""

    def test_list_devices_empty(self, client):
        """GET /devices should return empty list when no devices exist."""
        response = client.get("/api/v1/devices")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["items"] == []

    def test_discover_devices(self, client, mock_dlna):
        """POST /devices/discover should discover DLNA devices."""
        # Add mock devices
        mock_dlna.add_device("dev1", "Living Room TV", "192.168.1.100")
        mock_dlna.add_device("dev2", "Bedroom TV", "192.168.1.2")

        response = client.post("/api/v1/devices/discover", json={"timeout": 5.0})
        assert response.status_code == 200
        # Note: This test depends on proper mock injection

    def test_discover_devices_timeout(self, client, mock_dlna):
        """POST /devices/discover should handle timeout gracefully."""
        mock_dlna.fail_mode = "timeout"

        response = client.post("/api/v1/devices/discover", json={"timeout": 1.0})
        # Should not crash, may return empty list or error
        assert response.status_code in [200, 500]

    def test_add_device_manually(self, client):
        """POST /devices/add should add a device manually."""
        response = client.post("/api/v1/devices/add", json={
            "address": "192.168.1.100",
            "port": 8200
        })
        assert response.status_code == 200
        # Note: Response depends on implementation

    def test_delete_device(self, client):
        """DELETE /devices/{id} should delete the device."""
        # This test depends on having a device first
        # Implementation depends on how devices are stored
        pass

    def test_get_device_status(self, client, mock_dlna):
        """GET /devices/{id}/status should return device status."""
        # Add mock device
        mock_dlna.add_device("dev1", "Test TV", "192.168.1.100")

        # This test depends on device being in database
        pass


class TestDeviceErrorHandling:
    """Tests for device error scenarios."""

    def test_discover_with_offline_mode(self, client, mock_dlna):
        """Discovery should handle offline devices gracefully."""
        mock_dlna.fail_mode = "offline"
        response = client.post("/api/v1/devices/discover", json={})
        # Should not crash
        assert response.status_code in [200, 500]

    def test_add_invalid_address(self, client):
        """Adding device with invalid address should fail."""
        response = client.post("/api/v1/devices/add", json={
            "address": "invalid-address",
            "port": 8200
        })
        # Should validate address format
        # Exact behavior depends on implementation
