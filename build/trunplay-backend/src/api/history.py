"""
Playback history API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database.models import get_db
from ..database import crud, schemas

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=schemas.HistoryListResponse)
def get_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    plan_id: str = Query(default=None),
    db: Session = Depends(get_db)
):
    """Get playback history with pagination."""
    skip = (page - 1) * page_size
    total, items = crud.get_playback_histories(
        db,
        skip=skip,
        limit=page_size,
        plan_id=plan_id
    )

    return schemas.HistoryListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )


@router.get("/{history_id}", response_model=schemas.PlaybackHistoryResponse)
def get_history_item(history_id: str, db: Session = Depends(get_db)):
    """Get a specific history record."""
    history = crud.get_playback_history(db, history_id)
    if not history:
        raise HTTPException(status_code=404, detail="History record not found")
    return history


@router.delete("/{history_id}")
def delete_history_item(history_id: str, db: Session = Depends(get_db)):
    """Delete a history record."""
    success = crud.delete_playback_history(db, history_id)
    if not success:
        raise HTTPException(status_code=404, detail="History record not found")
    return {"message": "History record deleted"}


@router.delete("")
def clear_history(db: Session = Depends(get_db)):
    """Clear all history records."""
    count = crud.clear_playback_history(db)
    return {"message": f"Cleared {count} history records"}
