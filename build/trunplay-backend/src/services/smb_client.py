"""
SMB Client - File browsing and streaming from SMB/CIFS shares.
Uses pysmb for pure Python SMB implementation.
"""
import logging
import uuid
import io
from typing import List, Optional, Tuple
from dataclasses import dataclass

from smb.SMBConnection import SMBConnection
from smb.smb_structs import OperationFailure

logger = logging.getLogger(__name__)


# Supported media formats
VIDEO_EXTENSIONS = {
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "3gp", "ts", "mts", "m2ts"
}

IMAGE_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "bmp", "webp"
}

AUDIO_EXTENSIONS = {
    "mp3", "aac", "flac", "wav", "ogg", "m4a", "wma"
}


@dataclass
class SmbShareInfo:
    name: str
    path: str


@dataclass
class SmbFileItem:
    id: str
    name: str
    path: str
    uri: str
    type: str  # FOLDER, VIDEO, IMAGE, AUDIO, UNKNOWN
    source_type: str = "SMB"
    server_id: Optional[str] = None
    size: int = 0
    last_modified: int = 0


class SmbClient:
    """
    SMB client for browsing and streaming files from SMB/CIFS shares.
    """

    def __init__(self):
        self._connections: dict = {}
        self._client_name = "TrunPlay"

    def _get_connection(
        self,
        host: str,
        username: str = "",
        password: str = "",
        port: int = 445,
        server_name: str = ""
    ) -> Optional[SMBConnection]:
        """Get or create SMB connection."""
        conn_key = f"{host}:{port}:{username}"

        if conn_key in self._connections:
            conn = self._connections[conn_key]
            # Check if connection is still alive
            try:
                conn.echo(b"ping")
                return conn
            except Exception:
                # Connection dead, remove it
                try:
                    conn.close()
                except Exception:
                    pass
                del self._connections[conn_key]

        # Create new connection
        try:
            use_ntlm_v2 = True
            is_direct_tcp = True if port == 445 else False

            conn = SMBConnection(
                username=username or "guest",
                password=password or "",
                my_name=self._client_name,
                remote_name=server_name or host,
                use_ntlm_v2=use_ntlm_v2,
                is_direct_tcp=is_direct_tcp
            )

            success = conn.connect(host, port, timeout=30)
            if success:
                self._connections[conn_key] = conn
                logger.info(f"Connected to SMB server: {host}")
                return conn
            else:
                logger.error(f"Failed to connect to SMB server: {host}")
                return None

        except Exception as e:
            logger.error(f"SMB connection error for {host}: {e}")
            return None

    def close_all(self):
        """Close all SMB connections."""
        for conn in self._connections.values():
            try:
                conn.close()
            except Exception:
                pass
        self._connections.clear()

    async def test_connection(
        self,
        host: str,
        port: int = 445,
        username: str = "",
        password: str = ""
    ) -> Tuple[bool, str]:
        """Test SMB connection."""
        try:
            conn = self._get_connection(host, username, password, port)
            if conn:
                # Try to list shares
                shares = conn.listShares()
                share_names = [s.name for s in shares if not s.isSpecial]
                return True, f"Connected. Found {len(share_names)} shares: {', '.join(share_names)}"
            else:
                return False, "Connection failed"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    async def list_shares(
        self,
        host: str,
        port: int = 445,
        username: str = "",
        password: str = "",
        server_name: str = ""
    ) -> List[SmbShareInfo]:
        """List available shares on SMB server."""
        try:
            conn = self._get_connection(host, username, password, port, server_name)
            if not conn:
                return []

            shares = conn.listShares()
            result = []

            for share in shares:
                # Skip special shares (IPC$, ADMIN$, etc.)
                if share.isSpecial:
                    continue

                name = share.name
                result.append(SmbShareInfo(name=name, path=f"/{name}"))

            logger.info(f"Listed {len(result)} shares on {host}")
            return result

        except Exception as e:
            logger.error(f"Error listing shares on {host}: {e}")
            return []

    async def list_files(
        self,
        host: str,
        path: str,
        port: int = 445,
        username: str = "",
        password: str = "",
        server_id: str = "",
        server_name: str = ""
    ) -> List[SmbFileItem]:
        """Browse files in SMB path."""
        try:
            conn = self._get_connection(host, username, password, port, server_name)
            if not conn:
                return []

            # Parse path to get share name and relative path
            # path format: /sharename/folder/subfolder
            path = path.strip("/")
            if not path:
                # Return shares list as folders
                shares = await self.list_shares(host, port, username, password, server_name)
                return [
                    SmbFileItem(
                        id=f"smb_{server_id}_{share.name}_dir",
                        name=share.name,
                        path=share.path,
                        uri=f"smb://{host}/{share.name}",
                        type="FOLDER",
                        server_id=server_id
                    )
                    for share in shares
                ]

            parts = path.split("/", 1)
            share_name = parts[0]
            relative_path = parts[1] if len(parts) > 1 else ""

            # List files
            smb_path = relative_path.replace("/", "\\") if relative_path else ""
            files = conn.listPath(share_name, smb_path or "/")

            result = []
            for f in files:
                # Skip . and ..
                if f.filename in (".", ".."):
                    continue

                is_directory = f.isDirectory
                file_name = f.filename
                file_path = f"/{share_name}/{relative_path}/{file_name}".replace("//", "/")
                file_uri = f"smb://{host}{file_path}"

                # Determine file type
                if is_directory:
                    file_type = "FOLDER"
                else:
                    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
                    if ext in VIDEO_EXTENSIONS:
                        file_type = "VIDEO"
                    elif ext in IMAGE_EXTENSIONS:
                        file_type = "IMAGE"
                    elif ext in AUDIO_EXTENSIONS:
                        file_type = "AUDIO"
                    else:
                        # Skip unsupported files
                        continue

                result.append(SmbFileItem(
                    id=f"smb_{server_id}_{file_path.replace('/', '_')}_{uuid.uuid4().hex[:8]}",
                    name=file_name,
                    path=file_path,
                    uri=file_uri,
                    type=file_type,
                    server_id=server_id,
                    size=f.file_size if not is_directory else 0,
                    last_modified=int(f.last_write_time * 1000) if f.last_write_time else 0
                ))

            # Sort: folders first, then by name
            result.sort(key=lambda x: (x.type != "FOLDER", x.name.lower()))

            logger.info(f"Listed {len(result)} items in {path}")
            return result

        except OperationFailure as e:
            logger.error(f"SMB operation failed for {path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing files in {path}: {e}")
            return []

    async def get_file_size(
        self,
        host: str,
        path: str,
        port: int = 445,
        username: str = "",
        password: str = "",
        server_name: str = ""
    ) -> int:
        """Get file size."""
        try:
            conn = self._get_connection(host, username, password, port, server_name)
            if not conn:
                return 0

            # Parse path
            path = path.strip("/")
            parts = path.split("/", 1)
            if len(parts) < 2:
                return 0

            share_name = parts[0]
            relative_path = parts[1].replace("/", "\\")

            # Get file attributes
            attrs = conn.getAttributes(share_name, relative_path)
            return attrs.file_size

        except Exception as e:
            logger.error(f"Error getting file size for {path}: {e}")
            return 0

    def get_file_stream(
        self,
        host: str,
        path: str,
        port: int = 445,
        username: str = "",
        password: str = "",
        server_name: str = "",
        offset: int = 0,
        length: int = -1
    ) -> Optional[io.BytesIO]:
        """
        Get file stream for HTTP serving.
        Returns a BytesIO object containing file data.
        For large files, consider using chunk-based streaming.
        """
        try:
            conn = self._get_connection(host, username, password, port, server_name)
            if not conn:
                return None

            # Parse path
            path = path.strip("/")
            parts = path.split("/", 1)
            if len(parts) < 2:
                return None

            share_name = parts[0]
            relative_path = parts[1].replace("/", "\\")

            # Create buffer and retrieve file
            buffer = io.BytesIO()
            file_attrs, file_size = conn.retrieveFile(share_name, relative_path, buffer)

            if offset > 0:
                buffer.seek(offset)

            logger.debug(f"Retrieved file stream: {path}, size={file_size}")
            return buffer

        except Exception as e:
            logger.error(f"Error getting file stream for {path}: {e}")
            return None

    def stream_file_chunks(
        self,
        host: str,
        path: str,
        port: int = 445,
        username: str = "",
        password: str = "",
        server_name: str = "",
        chunk_size: int = 1024 * 1024  # 1MB chunks
    ):
        """
        Generator that yields file chunks for streaming.
        More memory-efficient for large files.
        """
        try:
            conn = self._get_connection(host, username, password, port, server_name)
            if not conn:
                return

            # Parse path
            path = path.strip("/")
            parts = path.split("/", 1)
            if len(parts) < 2:
                return

            share_name = parts[0]
            relative_path = parts[1].replace("/", "\\")

            # Get file size
            attrs = conn.getAttributes(share_name, relative_path)
            file_size = attrs.file_size

            # Stream in chunks
            offset = 0
            while offset < file_size:
                buffer = io.BytesIO()
                bytes_to_read = min(chunk_size, file_size - offset)
                conn.retrieveFileFromOffset(share_name, relative_path, buffer, offset, bytes_to_read)
                buffer.seek(0)
                yield buffer.read()
                offset += bytes_to_read

        except Exception as e:
            logger.error(f"Error streaming file {path}: {e}")
            return


# Global instance
_smb_client: Optional[SmbClient] = None


def get_smb_client() -> SmbClient:
    """Get global SMB client instance."""
    global _smb_client
    if _smb_client is None:
        _smb_client = SmbClient()
    return _smb_client
