"""
Media browsing API endpoints.
"""
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database.models import get_db
from ..database import crud, schemas
from ..services.smb_client import get_smb_client

router = APIRouter(prefix="/media", tags=["media"])

# Default local media paths
DEFAULT_MEDIA_PATHS = ["/mnt", "/tmp", "/root"]

# Supported extensions
VIDEO_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "3gp", "ts"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
AUDIO_EXTENSIONS = {"mp3", "aac", "flac", "wav", "ogg", "m4a"}


def _get_media_type(filename: str) -> str:
    """Determine media type from filename."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in VIDEO_EXTENSIONS:
        return "VIDEO"
    elif ext in IMAGE_EXTENSIONS:
        return "IMAGE"
    elif ext in AUDIO_EXTENSIONS:
        return "AUDIO"
    return "UNKNOWN"


@router.get("/local", response_model=schemas.MediaBrowseResponse)
def browse_local(path: str = Query(default="")):
    """Browse local filesystem."""
    # Default to listing root paths
    if not path:
        items = []
        for root_path in DEFAULT_MEDIA_PATHS:
            if os.path.exists(root_path):
                items.append(schemas.MediaItem(
                    id=f"local_{root_path.replace('/', '_')}",
                    name=os.path.basename(root_path) or root_path,
                    path=root_path,
                    uri=f"file://{root_path}",
                    type=schemas.MediaType.FOLDER,
                    source_type=schemas.MediaSourceType.LOCAL
                ))
        return schemas.MediaBrowseResponse(path="/", items=items)

    # Security: prevent path traversal
    path = os.path.abspath(path)
    allowed = False
    for root in DEFAULT_MEDIA_PATHS:
        if path.startswith(os.path.abspath(root)):
            allowed = True
            break

    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")

    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Not a directory")

    items = []
    try:
        for entry in os.scandir(path):
            if entry.name.startswith("."):
                continue

            if entry.is_dir():
                items.append(schemas.MediaItem(
                    id=f"local_{entry.path.replace('/', '_')}",
                    name=entry.name,
                    path=entry.path,
                    uri=f"file://{entry.path}",
                    type=schemas.MediaType.FOLDER,
                    source_type=schemas.MediaSourceType.LOCAL
                ))
            else:
                media_type = _get_media_type(entry.name)
                if media_type != "UNKNOWN":
                    stat = entry.stat()
                    items.append(schemas.MediaItem(
                        id=f"local_{entry.path.replace('/', '_')}",
                        name=entry.name,
                        path=entry.path,
                        uri=f"file://{entry.path}",
                        type=schemas.MediaType(media_type),
                        source_type=schemas.MediaSourceType.LOCAL,
                        size=stat.st_size,
                        last_modified=int(stat.st_mtime * 1000)
                    ))

    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Sort: folders first, then by name
    items.sort(key=lambda x: (x.type != schemas.MediaType.FOLDER, x.name.lower()))

    # Calculate parent path
    parent_path = os.path.dirname(path)
    if parent_path == path:
        parent_path = None

    return schemas.MediaBrowseResponse(
        path=path,
        parent_path=parent_path,
        items=items
    )


@router.get("/smb/{server_id}", response_model=schemas.MediaBrowseResponse)
async def browse_smb(
    server_id: str,
    path: str = Query(default=""),
    db: Session = Depends(get_db)
):
    """Browse SMB server."""
    server = crud.get_smb_server(db, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="SMB server not found")

    smb_client = get_smb_client()
    files = await smb_client.list_files(
        host=server.host,
        path=path,
        port=server.port,
        username=server.username,
        password=server.password,
        server_id=server_id
    )

    items = [
        schemas.MediaItem(
            id=f.id,
            name=f.name,
            path=f.path,
            uri=f.uri,
            type=schemas.MediaType(f.type),
            source_type=schemas.MediaSourceType.SMB,
            server_id=server_id,
            size=f.size,
            last_modified=f.last_modified
        )
        for f in files
    ]

    # Calculate parent path
    parent_path = None
    if path:
        path_parts = path.strip("/").split("/")
        if len(path_parts) > 1:
            parent_path = "/" + "/".join(path_parts[:-1])
        elif len(path_parts) == 1:
            parent_path = ""

    return schemas.MediaBrowseResponse(
        path=path or "/",
        parent_path=parent_path,
        items=items
    )
