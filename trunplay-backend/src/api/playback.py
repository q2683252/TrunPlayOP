"""
Playback control API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.models import get_db
from ..database import crud, schemas
from ..services.playback import get_playback_service

router = APIRouter(prefix="/playback", tags=["playback"])


@router.get("/status")
def get_playback_status():
    """Get current playback status."""
    playback_service = get_playback_service()
    info = playback_service.get_playback_info()

    return {
        "status": info.status.value,
        "device_id": info.device_id,
        "device_name": info.device_name,
        "plan_id": info.plan_id,
        "plan_title": info.plan_title,
        "media_url": info.media_url,
        "media_name": info.media_name,
        "position": info.position,
        "duration": info.duration,
        "volume": info.volume
    }


@router.post("/play")
async def play(request: schemas.PlayRequest, db: Session = Depends(get_db)):
    """Start playback for a plan."""
    plan = crud.get_plan(db, request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    playback_service = get_playback_service()
    success = await playback_service.start_playback(
        db=db,
        plan=plan,
        trigger_type=schemas.TriggerType.MANUAL,
        start_position=request.start_position
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to start playback")

    return {"message": "Playback started"}


@router.post("/pause")
async def pause():
    """Pause playback."""
    playback_service = get_playback_service()
    success = await playback_service.pause()

    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause")

    return {"message": "Playback paused"}


@router.post("/resume")
async def resume():
    """Resume playback."""
    playback_service = get_playback_service()
    success = await playback_service.resume()

    if not success:
        raise HTTPException(status_code=400, detail="Cannot resume")

    return {"message": "Playback resumed"}


@router.post("/stop")
async def stop(db: Session = Depends(get_db)):
    """Stop playback."""
    playback_service = get_playback_service()
    await playback_service.stop_playback(db)

    return {"message": "Playback stopped"}


@router.post("/seek")
async def seek(request: schemas.SeekRequest):
    """Seek to position."""
    playback_service = get_playback_service()
    success = await playback_service.seek(request.position)

    if not success:
        raise HTTPException(status_code=400, detail="Seek failed")

    return {"message": "Seeked", "position": request.position}


@router.post("/volume")
async def set_volume(request: schemas.VolumeRequest):
    """Set volume."""
    playback_service = get_playback_service()
    success = await playback_service.set_volume(request.level)

    if not success:
        raise HTTPException(status_code=400, detail="Set volume failed")

    return {"message": "Volume set", "level": request.level}


@router.get("/volume")
async def get_volume():
    """Get current volume."""
    playback_service = get_playback_service()
    volume = await playback_service.get_volume()

    return {"volume": volume}


@router.get("/position")
async def get_position():
    """Get current playback position."""
    playback_service = get_playback_service()
    info = await playback_service.get_position_info()

    if not info:
        return {"position": 0, "duration": 0}

    return info
