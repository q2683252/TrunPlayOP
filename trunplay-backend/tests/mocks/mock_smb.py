"""
Mock SMB Client for testing.

Simulates SMB server connections and file operations without actual network operations.
"""
import io
from typing import Dict, List, Optional, Any


class SMBAuthenticationError(Exception):
    """SMB authentication failed."""
    pass


class SMBConnectionError(Exception):
    """SMB connection failed."""
    pass


class SMBFileNotFoundError(Exception):
    """SMB file not found."""
    pass


class MockSMBClient:
    """Mock implementation of SMBClient for testing."""

    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.file_tree: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        self.connections: Dict[str, bool] = {}
        self.fail_mode: Optional[str] = None  # "auth_error", "connection_error", "not_found"
        self._call_history: List[Dict[str, Any]] = []

    def _record_call(self, method: str, **kwargs):
        """Record method calls for verification."""
        self._call_history.append({"method": method, **kwargs})

    def connect(self, server_id: str) -> bool:
        """Connect to an SMB server."""
        self._record_call("connect", server_id=server_id)

        if self.fail_mode == "auth_error":
            raise SMBAuthenticationError("Invalid credentials")
        if self.fail_mode == "connection_error":
            raise SMBConnectionError("Cannot connect to server")

        if server_id not in self.servers:
            raise SMBConnectionError(f"Server {server_id} not found")

        self.connections[server_id] = True
        return True

    def disconnect(self, server_id: str):
        """Disconnect from an SMB server."""
        self._record_call("disconnect", server_id=server_id)
        self.connections.pop(server_id, None)

    def is_connected(self, server_id: str) -> bool:
        """Check if connected to a server."""
        return self.connections.get(server_id, False)

    def list_shares(self, server_id: str) -> List[Dict[str, Any]]:
        """List shares on a server."""
        self._record_call("list_shares", server_id=server_id)

        if self.fail_mode == "connection_error":
            raise SMBConnectionError("Connection lost")

        server = self.servers.get(server_id, {})
        return server.get("shares", [])

    def list_files(self, server_id: str, share: str, path: str = "") -> List[Dict[str, Any]]:
        """List files in a directory."""
        self._record_call("list_files", server_id=server_id, share=share, path=path)

        if self.fail_mode == "connection_error":
            raise SMBConnectionError("Connection lost")
        if self.fail_mode == "not_found":
            return []

        full_path = f"{share}/{path}".rstrip("/")
        tree = self.file_tree.get(server_id, {})
        return tree.get(full_path, [])

    def get_file_stream(self, server_id: str, share: str, path: str) -> io.BytesIO:
        """Get a file stream for reading."""
        self._record_call("get_file_stream", server_id=server_id, share=share, path=path)

        if self.fail_mode == "connection_error":
            raise SMBConnectionError("Connection lost")
        if self.fail_mode == "not_found":
            raise SMBFileNotFoundError(f"File not found: {path}")
        if self.fail_mode == "auth_error":
            raise SMBAuthenticationError("Permission denied")

        # Return mock file content
        full_path = f"{share}/{path}"
        return io.BytesIO(f"Mock content for {full_path}".encode())

    def get_file_size(self, server_id: str, share: str, path: str) -> int:
        """Get file size in bytes."""
        self._record_call("get_file_size", server_id=server_id, share=share, path=path)

        if self.fail_mode == "not_found":
            raise SMBFileNotFoundError(f"File not found: {path}")

        # Return mock file size
        return 1024 * 1024  # 1MB default

    def file_exists(self, server_id: str, share: str, path: str) -> bool:
        """Check if a file exists."""
        self._record_call("file_exists", server_id=server_id, share=share, path=path)

        if self.fail_mode == "not_found":
            return False

        full_path = f"{share}/{path}"
        tree = self.file_tree.get(server_id, {})

        # Check if file is in any directory listing
        for dir_path, files in tree.items():
            for f in files:
                if f.get("path") == path or f.get("name") == path.split("/")[-1]:
                    return True
        return False

    def close_all(self):
        """Close all connections."""
        self._record_call("close_all")
        self.connections.clear()

    # ==================== Test Helper Methods ====================

    def add_server(self, server_id: str, name: str, address: str, **kwargs) -> Dict[str, Any]:
        """Add a mock SMB server."""
        server = {
            "id": server_id,
            "name": name,
            "address": address,
            "port": kwargs.get("port", 445),
            "username": kwargs.get("username", "guest"),
            "password": kwargs.get("password", ""),
            "shares": kwargs.get("shares", [{"name": "media", "path": "/media"}]),
        }
        self.servers[server_id] = server
        return server

    def remove_server(self, server_id: str):
        """Remove a mock server."""
        self.servers.pop(server_id, None)
        self.file_tree.pop(server_id, None)
        self.connections.pop(server_id, None)

    def add_files(self, server_id: str, path: str, files: List[Dict[str, Any]]):
        """Add mock files to a directory."""
        if server_id not in self.file_tree:
            self.file_tree[server_id] = {}
        self.file_tree[server_id][path] = files

    def add_file(self, server_id: str, path: str, name: str, **kwargs):
        """Add a single mock file."""
        file_entry = {
            "name": name,
            "path": f"{path}/{name}".lstrip("/"),
            "size": kwargs.get("size", 1024 * 1024),
            "is_directory": kwargs.get("is_directory", False),
            "modified": kwargs.get("modified", "2024-01-01 00:00:00"),
        }

        if server_id not in self.file_tree:
            self.file_tree[server_id] = {}
        if path not in self.file_tree[server_id]:
            self.file_tree[server_id][path] = []

        self.file_tree[server_id][path].append(file_entry)

    def get_call_history(self, method: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get call history, optionally filtered by method name."""
        if method:
            return [c for c in self._call_history if c["method"] == method]
        return self._call_history

    def clear_call_history(self):
        """Clear call history."""
        self._call_history.clear()

    def reset(self):
        """Reset all state."""
        self.servers.clear()
        self.file_tree.clear()
        self.connections.clear()
        self._call_history.clear()
        self.fail_mode = None
