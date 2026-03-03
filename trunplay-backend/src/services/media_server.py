"""
Media HTTP Server - Serves media files to DLNA devices via HTTP.
Supports Range requests for seeking and both local and SMB files.
"""
import os
import mimetypes
import logging
import uuid
import asyncio
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from urllib.parse import quote
import socket

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import aiofiles

from ..config import get_config

logger = logging.getLogger(__name__)


# MIME type mappings
MIME_TYPES = {
    # Video
    "mp4": "video/mp4",
    "mkv": "video/x-matroska",
    "avi": "video/x-msvideo",
    "mov": "video/quicktime",
    "wmv": "video/x-ms-wmv",
    "flv": "video/x-flv",
    "webm": "video/webm",
    "m4v": "video/x-m4v",
    "3gp": "video/3gpp",
    "ts": "video/mp2t",
    "mts": "video/mp2t",
    "m2ts": "video/mp2t",
    # Audio
    "mp3": "audio/mpeg",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
    # Image
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}


@dataclass
class MediaInfo:
    """Registered media information."""
    media_id: str
    file_path: str
    file_name: str
    mime_type: str
    file_size: int
    is_smb: bool = False
    smb_host: Optional[str] = None
    smb_port: int = 445
    smb_username: str = ""
    smb_password: str = ""
    smb_server_name: str = ""


class MediaHttpServer:
    """
    HTTP server for streaming media to DLNA devices.
    """

    def __init__(self, port: int = 8089):
        self._port = port
        self._media_registry: Dict[str, MediaInfo] = {}
        self._local_ip: Optional[str] = None
        self._app: Optional[FastAPI] = None
        self._config = get_config()
        self._chunk_size = self._config.media_chunk_size

    @property
    def port(self) -> int:
        return self._port

    def get_local_ip(self) -> str:
        """Get local IP address for media URLs."""
        if self._local_ip:
            return self._local_ip

        try:
            # Try to get the IP by connecting to a known address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self._local_ip = ip
            return ip
        except Exception:
            pass

        # Fallback: enumerate interfaces
        try:
            import socket
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip and not ip.startswith("127."):
                self._local_ip = ip
                return ip
        except Exception:
            pass

        # Last resort
        return "127.0.0.1"

    def clear_ip_cache(self):
        """Clear cached IP address (call on network change)."""
        self._local_ip = None

    def register_local_media(
        self,
        file_path: str,
        file_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Register a local file and return HTTP URL.
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        file_name = file_name or os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        mime_type = self._get_mime_type(file_name)

        media_id = uuid.uuid4().hex
        self._media_registry[media_id] = MediaInfo(
            media_id=media_id,
            file_path=file_path,
            file_name=file_name,
            mime_type=mime_type,
            file_size=file_size,
            is_smb=False
        )

        url = self._build_url(media_id, file_name)
        logger.info(f"Registered local media: {file_path} -> {url}")
        return url

    def register_smb_media(
        self,
        smb_path: str,
        file_name: str,
        file_size: int,
        smb_host: str,
        smb_port: int = 445,
        smb_username: str = "",
        smb_password: str = "",
        smb_server_name: str = ""
    ) -> str:
        """
        Register an SMB file and return HTTP URL.
        """
        mime_type = self._get_mime_type(file_name)

        media_id = uuid.uuid4().hex
        self._media_registry[media_id] = MediaInfo(
            media_id=media_id,
            file_path=smb_path,
            file_name=file_name,
            mime_type=mime_type,
            file_size=file_size,
            is_smb=True,
            smb_host=smb_host,
            smb_port=smb_port,
            smb_username=smb_username,
            smb_password=smb_password,
            smb_server_name=smb_server_name
        )

        url = self._build_url(media_id, file_name)
        logger.info(f"Registered SMB media: smb://{smb_host}{smb_path} -> {url}")
        return url

    def unregister_media(self, media_id: str):
        """Remove media from registry."""
        if media_id in self._media_registry:
            del self._media_registry[media_id]
            logger.debug(f"Unregistered media: {media_id}")

    def clear_all_media(self):
        """Clear all registered media."""
        self._media_registry.clear()
        logger.info("Cleared all registered media")

    def get_media_info(self, media_id: str) -> Optional[MediaInfo]:
        """Get registered media info."""
        return self._media_registry.get(media_id)

    def _build_url(self, media_id: str, file_name: str) -> str:
        """Build HTTP URL for media."""
        ip = self.get_local_ip()
        encoded_name = quote(file_name)
        return f"http://{ip}:{self._port}/stream/{media_id}/{encoded_name}"

    def _get_mime_type(self, file_name: str) -> str:
        """Get MIME type from filename."""
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        return MIME_TYPES.get(ext, "application/octet-stream")

    def create_app(self) -> FastAPI:
        """Create FastAPI app for media streaming."""
        app = FastAPI(title="TrunPlay Media Server")

        @app.get("/stream/{media_id}/{filename}")
        async def stream_media(media_id: str, filename: str, request: Request):
            """Stream media file with Range support."""
            media_info = self._media_registry.get(media_id)
            if not media_info:
                raise HTTPException(status_code=404, detail="Media not found")

            # Parse Range header
            range_header = request.headers.get("range")
            start, end = 0, media_info.file_size - 1

            if range_header:
                range_match = range_header.replace("bytes=", "").split("-")
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else media_info.file_size - 1

            # Validate range
            if start >= media_info.file_size or start > end:
                raise HTTPException(status_code=416, detail="Range Not Satisfiable")

            content_length = end - start + 1

            headers = {
                "Content-Type": media_info.mime_type,
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Content-Disposition": f'inline; filename="{media_info.file_name}"',
                "Access-Control-Allow-Origin": "*",
            }

            if range_header:
                headers["Content-Range"] = f"bytes {start}-{end}/{media_info.file_size}"
                status_code = 206
            else:
                status_code = 200

            if media_info.is_smb:
                # SMB file streaming
                generator = self._stream_smb_file(media_info, start, content_length)
            else:
                # Local file streaming
                generator = self._stream_local_file(media_info.file_path, start, content_length)

            return StreamingResponse(
                generator,
                status_code=status_code,
                headers=headers,
                media_type=media_info.mime_type
            )

        @app.get("/health")
        async def health():
            return {"status": "ok", "registered_media": len(self._media_registry)}

        self._app = app
        return app

    async def _stream_local_file(
        self,
        file_path: str,
        start: int,
        length: int
    ):
        """Stream local file with Range support using configurable chunk size."""
        chunk_size = self._chunk_size
        async with aiofiles.open(file_path, "rb") as f:
            await f.seek(start)
            remaining = length

            while remaining > 0:
                read_size = min(chunk_size, remaining)
                data = await f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    async def _stream_smb_file(
        self,
        media_info: MediaInfo,
        start: int,
        length: int
    ):
        """Stream SMB file with Range support using configurable chunk size."""
        chunk_size = self._chunk_size
        from .smb_client import get_smb_client

        smb_client = get_smb_client()

        # Parse SMB path
        path = media_info.file_path.strip("/")
        parts = path.split("/", 1)
        if len(parts) < 2:
            return

        share_name = parts[0]
        relative_path = parts[1].replace("/", "\\")

        try:
            conn = smb_client._get_connection(
                media_info.smb_host,
                media_info.smb_username,
                media_info.smb_password,
                media_info.smb_port,
                media_info.smb_server_name
            )

            if not conn:
                logger.error(f"Failed to connect to SMB: {media_info.smb_host}")
                return

            offset = start
            remaining = length

            while remaining > 0:
                read_size = min(chunk_size, remaining)
                import io
                buffer = io.BytesIO()

                try:
                    conn.retrieveFileFromOffset(
                        share_name,
                        relative_path,
                        buffer,
                        offset,
                        read_size
                    )
                    buffer.seek(0)
                    data = buffer.read()
                    if not data:
                        break
                    yield data
                    offset += len(data)
                    remaining -= len(data)
                except Exception as e:
                    logger.error(f"SMB read error: {e}")
                    break

        except Exception as e:
            logger.error(f"SMB streaming error: {e}")


# Global instance
_media_server: Optional[MediaHttpServer] = None


def get_media_server(port: int = 8089) -> MediaHttpServer:
    """Get global media server instance."""
    global _media_server
    if _media_server is None:
        _media_server = MediaHttpServer(port=port)
    return _media_server
