"""
Study tasks API endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.models import get_db
from ..database import crud, schemas

router = APIRouter(prefix="/study", tags=["study"])


@router.get("/tasks", response_model=List[schemas.StudyTaskResponse])
def get_study_tasks(db: Session = Depends(get_db)):
    """Get all study tasks."""
    tasks = crud.get_study_tasks(db)
    return tasks


@router.get("/tasks/{task_id}", response_model=schemas.StudyTaskResponse)
def get_study_task(task_id: str, db: Session = Depends(get_db)):
    """Get a specific study task."""
    task = crud.get_study_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Study task not found")
    return task


@router.post("/tasks", response_model=schemas.StudyTaskResponse)
def create_study_task(task: schemas.StudyTaskCreate, db: Session = Depends(get_db)):
    """Create a new study task."""
    db_task = crud.create_study_task(db, task)
    return db_task


@router.put("/tasks/{task_id}", response_model=schemas.StudyTaskResponse)
def update_study_task(
    task_id: str,
    task: schemas.StudyTaskUpdate,
    db: Session = Depends(get_db)
):
    """Update a study task."""
    db_task = crud.update_study_task(db, task_id, task)
    if not db_task:
        raise HTTPException(status_code=404, detail="Study task not found")
    return db_task


@router.delete("/tasks/{task_id}")
def delete_study_task(task_id: str, db: Session = Depends(get_db)):
    """Delete a study task."""
    success = crud.delete_study_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Study task not found")
    return {"message": "Study task deleted"}


@router.post("/tasks/{task_id}/reset")
def reset_study_task_progress(task_id: str, db: Session = Depends(get_db)):
    """Reset study task progress."""
    task = crud.reset_study_task_progress(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Study task not found")
    return {"message": "Progress reset", "task_id": task_id}


@router.post("/tasks/{task_id}/media", response_model=schemas.StudyTaskMediaResponse)
def add_media_to_task(
    task_id: str,
    media: schemas.StudyTaskMediaCreate,
    db: Session = Depends(get_db)
):
    """Add media to a study task."""
    db_media = crud.add_study_task_media(db, task_id, media)
    if not db_media:
        raise HTTPException(status_code=404, detail="Study task not found")
    return db_media


@router.delete("/tasks/{task_id}/media/{media_id}")
def remove_media_from_task(task_id: str, media_id: str, db: Session = Depends(get_db)):
    """Remove media from a study task."""
    success = crud.remove_study_task_media(db, task_id, media_id)
    if not success:
        raise HTTPException(status_code=404, detail="Media not found")
    return {"message": "Media removed"}


# ==================== Plan-Task Links ====================

@router.post("/tasks/{task_id}/link/{plan_id}")
def link_task_to_plan(task_id: str, plan_id: str, db: Session = Depends(get_db)):
    """Link a study task to a plan."""
    link = crud.link_plan_study_task(db, plan_id, task_id)
    if not link:
        raise HTTPException(status_code=400, detail="Failed to link")
    return {"message": "Linked", "plan_id": plan_id, "task_id": task_id}


@router.delete("/tasks/{task_id}/link/{plan_id}")
def unlink_task_from_plan(task_id: str, plan_id: str, db: Session = Depends(get_db)):
    """Unlink a study task from a plan."""
    success = crud.unlink_plan_study_task(db, plan_id, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"message": "Unlinked"}
