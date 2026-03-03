"""
Utility helper functions.
"""
import re
import hashlib
from typing import Optional
from urllib.parse import urlparse, unquote


def extract_filename(url: str) -> str:
    """Extract filename from URL."""
    try:
        path = urlparse(url).path
        return unquote(path.split("/")[-1])
    except Exception:
        return "media"


def format_time(seconds: int) -> str:
    """Format seconds to HH:MM:SS or MM:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_time(time_str: str) -> int:
    """Parse HH:MM:SS or MM:SS to seconds."""
    if not time_str:
        return 0

    try:
        # Remove fractional seconds
        time_str = time_str.split(".")[0]
        parts = time_str.split(":")

        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return int(parts[0])
    except Exception:
        return 0


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID."""
    import uuid
    uid = uuid.uuid4().hex
    return f"{prefix}_{uid}" if prefix else uid


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename."""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    return filename.strip()


def is_valid_ip(ip: str) -> bool:
    """Check if string is a valid IP address."""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(pattern, ip):
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    return False


def md5_hash(data: str) -> str:
    """Generate MD5 hash of string."""
    return hashlib.md5(data.encode()).hexdigest()
