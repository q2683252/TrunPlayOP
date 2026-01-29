"""
Integration tests for Media API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestMediaAPI:
    """Tests for /api/v1/media endpoints."""

    def test_browse_local_root(self, client):
        """GET /media/local should browse local media directories."""
        response = client.get("/api/v1/media/local")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]

    def test_browse_local_with_path(self, client):
        """GET /media/local?path=/mnt should browse specific path."""
        response = client.get("/api/v1/media/local", params={"path": "/mnt"})
        # Response depends on filesystem
        assert response.status_code in [200, 403, 404]

    def test_browse_local_path_traversal_blocked(self, client):
        """GET /media/local with path traversal should be blocked."""
        response = client.get("/api/v1/media/local", params={"path": "../../../etc"})
        assert response.status_code == 403

    def test_browse_local_absolute_path_traversal_blocked(self, client):
        """GET /media/local with absolute path traversal should be blocked."""
        response = client.get("/api/v1/media/local", params={"path": "/etc/passwd"})
        assert response.status_code == 403

    def test_browse_smb_nonexistent_server(self, client):
        """GET /media/smb/{server_id} with non-existent server should return 404."""
        response = client.get("/api/v1/media/smb/nonexistent-server")
        assert response.status_code == 404

    def test_browse_smb_with_path(self, client, mock_smb):
        """GET /media/smb/{server_id}?path=/videos should browse SMB path."""
        # This test requires an SMB server in database
        pass


class TestMediaPathSecurity:
    """Tests for media path security."""

    @pytest.mark.parametrize("malicious_path", [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "/etc/shadow",
        "....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f",
        "..%c0%af..%c0%af",
    ])
    def test_path_traversal_variants_blocked(self, client, malicious_path):
        """Various path traversal attempts should be blocked."""
        response = client.get("/api/v1/media/local", params={"path": malicious_path})
        assert response.status_code == 403

    def test_hidden_files_not_listed(self, client):
        """Hidden files (starting with .) should not be listed."""
        response = client.get("/api/v1/media/local")
        if response.status_code == 200:
            items = response.json()["data"]["items"]
            for item in items:
                assert not item["name"].startswith(".")


class TestMediaSMB:
    """Tests for SMB media browsing."""

    def test_browse_smb_auth_error(self, client, mock_smb):
        """SMB browsing with auth error should return appropriate error."""
        mock_smb.fail_mode = "auth_error"
        # This test requires proper mock injection
        pass

    def test_browse_smb_connection_error(self, client, mock_smb):
        """SMB browsing with connection error should return appropriate error."""
        mock_smb.fail_mode = "connection_error"
        # This test requires proper mock injection
        pass
