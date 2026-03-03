"""
SMB API endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.models import get_db
from ..database import crud, schemas
from ..services.smb_client import get_smb_client

router = APIRouter(prefix="/smb", tags=["smb"])


@router.get("/servers", response_model=List[schemas.SmbServerResponse])
def get_smb_servers(db: Session = Depends(get_db)):
    """Get all SMB servers."""
    servers = crud.get_smb_servers(db)
    return servers


@router.post("/servers", response_model=schemas.SmbServerResponse)
def create_smb_server(server: schemas.SmbServerCreate, db: Session = Depends(get_db)):
    """Add a new SMB server."""
    db_server = crud.create_smb_server(db, server)
    return db_server


@router.put("/servers/{server_id}", response_model=schemas.SmbServerResponse)
def update_smb_server(
    server_id: str,
    server: schemas.SmbServerUpdate,
    db: Session = Depends(get_db)
):
    """Update an SMB server."""
    db_server = crud.update_smb_server(db, server_id, server)
    if not db_server:
        raise HTTPException(status_code=404, detail="SMB server not found")
    return db_server


@router.delete("/servers/{server_id}")
def delete_smb_server(server_id: str, db: Session = Depends(get_db)):
    """Delete an SMB server."""
    success = crud.delete_smb_server(db, server_id)
    if not success:
        raise HTTPException(status_code=404, detail="SMB server not found")
    return {"message": "SMB server deleted"}


@router.post("/servers/test")
async def test_smb_connection(request: schemas.SmbTestRequest):
    """Test SMB server connection."""
    smb_client = get_smb_client()

    success, message = await smb_client.test_connection(
        host=request.host,
        port=request.port,
        username=request.username,
        password=request.password
    )

    return {
        "success": success,
        "message": message
    }


@router.get("/servers/{server_id}/shares")
async def list_smb_shares(server_id: str, db: Session = Depends(get_db)):
    """List shares on an SMB server."""
    server = crud.get_smb_server(db, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="SMB server not found")

    smb_client = get_smb_client()
    shares = await smb_client.list_shares(
        host=server.host,
        port=server.port,
        username=server.username,
        password=server.password
    )

    # Update connection status
    connected = len(shares) > 0
    crud.update_smb_server_connection(db, server_id, connected)

    return {
        "server_id": server_id,
        "shares": [{"name": s.name, "path": s.path} for s in shares]
    }


@router.post("/servers/scan")
async def scan_smb_servers():
    """
    Scan local network for SMB servers.
    Note: This is a simplified implementation.
    """
    # In a full implementation, this would scan the network
    # For now, return empty list
    return {
        "message": "Network scan not implemented",
        "servers": []
    }
