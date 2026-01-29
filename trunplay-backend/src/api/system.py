"""
System API endpoints.
"""
import os
import time
from fastapi import APIRouter

from ..database.models import DB_PATH
from ..database.schemas import PlaybackStatus
from ..services.playback import get_playback_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def get_system_status():
    """Get system status."""
    # Get database size
    db_size = 0
    if os.path.exists(DB_PATH):
        db_size = os.path.getsize(DB_PATH)

    # Get playback status
    playback_service = get_playback_service()
    info = playback_service.get_playback_info()

    return {
        "version": "1.0.0",
        "uptime": int(time.time()),
        "db_path": DB_PATH,
        "db_size": db_size,
        "playback_status": info.status.value,
        "local_ip": get_playback_service()._media_server.get_local_ip()
    }


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/config")
def get_config():
    """Get system configuration."""
    return {
        "api_port": 8088,
        "media_port": 8089,
        "db_path": DB_PATH,
        "local_media_paths": ["/mnt", "/tmp"],
        "log_level": "INFO"
    }
