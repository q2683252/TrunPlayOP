"""
Plans API endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.models import get_db
from ..database import crud, schemas
from ..services.scheduler import get_scheduler
from ..services.playback import get_playback_service

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=List[schemas.PlanResponse])
def get_plans(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all plans."""
    plans = crud.get_plans(db, skip=skip, limit=limit)
    return plans


@router.get("/{plan_id}", response_model=schemas.PlanResponse)
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    """Get a specific plan."""
    plan = crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.post("", response_model=schemas.PlanResponse)
def create_plan(plan: schemas.PlanCreate, db: Session = Depends(get_db)):
    """Create a new plan."""
    db_plan = crud.create_plan(db, plan)

    # Schedule if active
    if db_plan.is_active:
        scheduler = get_scheduler()
        scheduler.schedule_plan(
            plan_id=db_plan.id,
            plan_title=db_plan.title,
            start_time=db_plan.start_time,
            repeat_days=db_plan.repeat_days,
            skip_holidays=bool(db_plan.skip_holidays)
        )

    return db_plan


@router.put("/{plan_id}", response_model=schemas.PlanResponse)
def update_plan(plan_id: str, plan: schemas.PlanUpdate, db: Session = Depends(get_db)):
    """Update a plan."""
    db_plan = crud.update_plan(db, plan_id, plan)
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Update schedule
    scheduler = get_scheduler()
    if db_plan.is_active:
        scheduler.schedule_plan(
            plan_id=db_plan.id,
            plan_title=db_plan.title,
            start_time=db_plan.start_time,
            repeat_days=db_plan.repeat_days,
            skip_holidays=bool(db_plan.skip_holidays)
        )
    else:
        scheduler.cancel_plan(plan_id)

    return db_plan


@router.delete("/{plan_id}")
def delete_plan(plan_id: str, db: Session = Depends(get_db)):
    """Delete a plan."""
    # Cancel schedule first
    scheduler = get_scheduler()
    scheduler.cancel_plan(plan_id)

    success = crud.delete_plan(db, plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {"message": "Plan deleted"}


@router.post("/{plan_id}/activate", response_model=schemas.PlanResponse)
def activate_plan(plan_id: str, db: Session = Depends(get_db)):
    """Activate a plan."""
    plan = crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = crud.update_plan(db, plan_id, schemas.PlanUpdate(is_active=True))

    # Schedule
    scheduler = get_scheduler()
    scheduler.schedule_plan(
        plan_id=plan.id,
        plan_title=plan.title,
        start_time=plan.start_time,
        repeat_days=plan.repeat_days,
        skip_holidays=bool(plan.skip_holidays)
    )

    return plan


@router.post("/{plan_id}/deactivate", response_model=schemas.PlanResponse)
def deactivate_plan(plan_id: str, db: Session = Depends(get_db)):
    """Deactivate a plan."""
    plan = crud.update_plan(db, plan_id, schemas.PlanUpdate(is_active=False))
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Cancel schedule
    scheduler = get_scheduler()
    scheduler.cancel_plan(plan_id)

    return plan


@router.post("/{plan_id}/play")
async def play_plan(
    plan_id: str,
    start_position: int = 0,
    db: Session = Depends(get_db)
):
    """Immediately play a plan."""
    plan = crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    playback_service = get_playback_service()
    success = await playback_service.start_playback(
        db=db,
        plan=plan,
        trigger_type=schemas.TriggerType.MANUAL,
        start_position=start_position
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to start playback")

    return {"message": "Playback started", "plan_id": plan_id}


@router.post("/{plan_id}/reset-progress")
def reset_plan_progress(plan_id: str, db: Session = Depends(get_db)):
    """Reset playback progress for a plan."""
    plan = crud.reset_plan_progress(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {"message": "Progress reset", "plan_id": plan_id}
