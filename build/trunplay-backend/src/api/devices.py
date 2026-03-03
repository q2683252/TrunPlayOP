"""
Devices API endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.models import get_db
from ..database import crud, schemas
from ..services.dlna_manager import get_dlna_manager

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=List[schemas.DeviceResponse])
def get_devices(db: Session = Depends(get_db)):
    """Get all known devices."""
    devices = crud.get_devices(db)
    return devices


@router.post("/discover")
async def discover_devices(timeout: float = 5.0, db: Session = Depends(get_db)):
    """Discover DLNA devices on the network."""
    dlna_manager = get_dlna_manager()
    devices = await dlna_manager.start_discovery(timeout=timeout)

    # Save discovered devices to database
    for device in devices:
        crud.upsert_device(db, {
            "id": device.id,
            "name": device.name,
            "address": device.address,
            "type": device.type,
            "manufacturer": device.manufacturer,
            "is_online": 1,
            "last_seen": device.last_seen,
            "location_url": device.location_url,
            "source": device.source
        })

    return {
        "message": f"Found {len(devices)} devices",
        "devices": [
            {
                "id": d.id,
                "name": d.name,
                "address": d.address,
                "type": d.type,
                "manufacturer": d.manufacturer
            }
            for d in devices
        ]
    }


@router.post("/add")
async def add_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    """Manually add a device by IP address."""
    dlna_manager = get_dlna_manager()

    discovered = await dlna_manager.add_device_manually(
        address=device.address,
        port=device.port
    )

    if not discovered:
        raise HTTPException(
            status_code=400,
            detail=f"Could not connect to device at {device.address}:{device.port}"
        )

    # Save to database
    db_device = crud.upsert_device(db, {
        "id": discovered.id,
        "name": discovered.name,
        "address": discovered.address,
        "type": discovered.type,
        "manufacturer": discovered.manufacturer,
        "is_online": 1,
        "last_seen": discovered.last_seen,
        "location_url": discovered.location_url,
        "source": "MANUAL"
    })

    return db_device


@router.delete("/{device_id}")
def delete_device(device_id: str, db: Session = Depends(get_db)):
    """Delete a device."""
    # Remove from DLNA manager cache
    dlna_manager = get_dlna_manager()
    dlna_manager.remove_device(device_id)

    # Remove from database
    success = crud.delete_device(db, device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"message": "Device deleted"}


@router.get("/{device_id}/status")
async def check_device_status(device_id: str, db: Session = Depends(get_db)):
    """Check if a device is online."""
    device = crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    dlna_manager = get_dlna_manager()
    is_online = await dlna_manager.check_device_online(device_id)

    # Update database
    crud.update_device(db, device_id, {"is_online": 1 if is_online else 0})

    return {
        "device_id": device_id,
        "name": device.name,
        "is_online": is_online
    }
