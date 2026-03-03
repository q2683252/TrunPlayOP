#!/usr/bin/env python3
"""
Mock SMB Server for TrunPlay testing.

Implements a minimal SMB server that serves files from a local directory.
Uses impacket library for SMB protocol implementation.

Usage:
    python3 mock_smb_server.py [--share-path /path/to/media] [--port 4455]

If impacket is not available, falls back to a simple HTTP file server
that TrunPlay can use as an alternative media source.
"""

import argparse
import os
import sys
import logging
import mimetypes
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
import socket
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """Get local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def create_sample_media_files(media_dir: Path):
    """Create sample media files for testing."""
    media_dir.mkdir(parents=True, exist_ok=True)

    # Create sample video placeholder files
    videos_dir = media_dir / "Videos"
    videos_dir.mkdir(exist_ok=True)

    sample_videos = [
        "sample_video_1.mp4",
        "sample_video_2.mkv",
        "nature_documentary.mp4",
        "music_concert.mp4",
    ]

    for video in sample_videos:
        video_path = videos_dir / video
        if not video_path.exists():
            # Create a minimal MP4-like file (just header for testing)
            with open(video_path, 'wb') as f:
                # Write minimal ftyp box (MP4 file type box)
                ftyp = b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom'
                f.write(ftyp)
                # Pad to make it look like a real file
                f.write(b'\x00' * 1024)
            logger.info(f"Created sample: {video_path}")

    # Create sample images
    images_dir = media_dir / "Images"
    images_dir.mkdir(exist_ok=True)

    sample_images = [
        "photo_001.jpg",
        "photo_002.jpg",
        "wallpaper.png",
    ]

    for image in sample_images:
        image_path = images_dir / image
        if not image_path.exists():
            with open(image_path, 'wb') as f:
                if image.endswith('.jpg'):
                    # Minimal JPEG header
                    f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00')
                else:
                    # Minimal PNG header
                    f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde')
                f.write(b'\x00' * 512)
            logger.info(f"Created sample: {image_path}")

    # Create sample audio
    audio_dir = media_dir / "Music"
    audio_dir.mkdir(exist_ok=True)

    sample_audio = [
        "track_01.mp3",
        "track_02.mp3",
    ]

    for audio in sample_audio:
        audio_path = audio_dir / audio
        if not audio_path.exists():
            with open(audio_path, 'wb') as f:
                # Minimal MP3 header (ID3v2)
                f.write(b'ID3\x04\x00\x00\x00\x00\x00\x00')
                f.write(b'\x00' * 512)
            logger.info(f"Created sample: {audio_path}")

    return media_dir


class MediaHTTPHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves media files and provides directory listing as JSON."""

    def __init__(self, *args, media_root=None, **kwargs):
        self.media_root = media_root
        super().__init__(*args, directory=str(media_root) if media_root else None, **kwargs)

    def log_message(self, format, *args):
        logger.debug(f"HTTP: {args[0]}")

    def do_GET(self):
        # Handle API-style requests for directory listing
        if self.path == "/api/files" or self.path.startswith("/api/files?"):
            self.send_file_list("/")
            return
        elif self.path.startswith("/api/files/"):
            subpath = self.path[11:]  # Remove "/api/files/"
            if "?" in subpath:
                subpath = subpath.split("?")[0]
            self.send_file_list(subpath)
            return

        # Normal file serving
        super().do_GET()

    def send_file_list(self, subpath: str):
        """Send JSON list of files in directory."""
        try:
            if self.media_root:
                target_dir = Path(self.media_root) / subpath.lstrip("/")
            else:
                target_dir = Path(".") / subpath.lstrip("/")

            if not target_dir.exists() or not target_dir.is_dir():
                self.send_error(404, "Directory not found")
                return

            files = []
            for item in sorted(target_dir.iterdir()):
                stat = item.stat()
                file_type = "FOLDER" if item.is_dir() else self._get_file_type(item.name)
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.media_root or ".")),
                    "type": file_type,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime * 1000)
                })

            response = json.dumps({"files": files, "path": subpath}).encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(response))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response)

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            self.send_error(500, str(e))

    def _get_file_type(self, filename: str) -> str:
        """Determine file type from extension."""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        video_exts = {'mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', '3gp', 'ts', 'mts', 'm2ts'}
        image_exts = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}
        audio_exts = {'mp3', 'aac', 'flac', 'wav', 'ogg', 'm4a', 'wma'}

        if ext in video_exts:
            return "VIDEO"
        elif ext in image_exts:
            return "IMAGE"
        elif ext in audio_exts:
            return "AUDIO"
        return "UNKNOWN"


def create_handler_class(media_root):
    """Create a handler class with the media root set."""
    class Handler(MediaHTTPHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, media_root=media_root, **kwargs)
    return Handler


def try_run_smb_server(share_path: Path, port: int) -> bool:
    """Try to run actual SMB server using impacket."""
    try:
        from impacket import smbserver
        from impacket.ntlm import compute_lmhash, compute_nthash

        logger.info("Starting SMB server with impacket...")

        server = smbserver.SimpleSMBServer(listenAddress="0.0.0.0", listenPort=port)
        server.addShare("media", str(share_path), "TrunPlay Media Share")
        server.setSMB2Support(True)

        # Allow guest access
        server.addCredential("guest", 0, compute_lmhash(""), compute_nthash(""))

        logger.info(f"SMB server started on port {port}")
        logger.info(f"Share: \\\\{get_local_ip()}\\media -> {share_path}")

        server.start()
        return True

    except ImportError:
        logger.warning("impacket not installed, SMB server not available")
        return False
    except Exception as e:
        logger.error(f"Failed to start SMB server: {e}")
        return False


def run_http_fallback(share_path: Path, port: int):
    """Run HTTP server as fallback for media serving."""
    ip = get_local_ip()

    logger.info("=" * 60)
    logger.info("📁 Mock Media Server (HTTP Mode)")
    logger.info("=" * 60)
    logger.info(f"📍 IP: {ip}")
    logger.info(f"🌐 Port: {port}")
    logger.info(f"📂 Media Path: {share_path}")
    logger.info("")
    logger.info("URLs:")
    logger.info(f"  Browse: http://{ip}:{port}/")
    logger.info(f"  API:    http://{ip}:{port}/api/files")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Note: This is HTTP mode. For true SMB, install impacket:")
    logger.info("  pip3 install impacket")
    logger.info("")

    handler = create_handler_class(share_path)
    server = HTTPServer(('', port), handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Mock SMB/Media Server for TrunPlay testing")
    parser.add_argument("--share-path", default="./mock_media",
                        help="Path to media files to share")
    parser.add_argument("--port", type=int, default=4455,
                        help="Port for SMB server (default: 4455) or HTTP fallback")
    parser.add_argument("--http", action="store_true",
                        help="Force HTTP mode instead of trying SMB")
    parser.add_argument("--create-samples", action="store_true",
                        help="Create sample media files for testing")
    args = parser.parse_args()

    share_path = Path(args.share_path).resolve()

    # Create sample files if requested or if directory is empty/missing
    if args.create_samples or not share_path.exists():
        logger.info("Creating sample media files...")
        create_sample_media_files(share_path)

    share_path.mkdir(parents=True, exist_ok=True)

    if args.http:
        run_http_fallback(share_path, args.port)
    else:
        # Try SMB first, fall back to HTTP
        if not try_run_smb_server(share_path, args.port):
            logger.info("Falling back to HTTP server...")
            run_http_fallback(share_path, args.port)


if __name__ == "__main__":
    main()
