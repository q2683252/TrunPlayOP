"""
CRUD operations for database models.
"""
import uuid
import time
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .models import (
    Plan, Device, SmbServer, PlaybackHistory,
    StudyTask, StudyTaskMedia, PlanStudyTask
)
from .schemas import (
    PlanCreate, PlanUpdate,
    SmbServerCreate, SmbServerUpdate,
    StudyTaskCreate, StudyTaskUpdate, StudyTaskMediaCreate,
    TriggerType, EndStatus
)


# ==================== Plan CRUD ====================

def create_plan(db: Session, plan: PlanCreate) -> Plan:
    db_plan = Plan(
        id=str(uuid.uuid4()),
        title=plan.title,
        start_time=plan.start_time,
        end_time=plan.end_time,
        repeat_days=plan.repeat_days,
        skip_holidays=1 if plan.skip_holidays else 0,
        device_id=plan.device_id,
        media_url=plan.media_url,
        is_active=1 if plan.is_active else 0,
        play_mode=plan.play_mode.value,
        created_at=int(time.time() * 1000)
    )
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan


def get_plan(db: Session, plan_id: str) -> Optional[Plan]:
    return db.query(Plan).filter(Plan.id == plan_id).first()


def get_plans(db: Session, skip: int = 0, limit: int = 100) -> List[Plan]:
    return db.query(Plan).offset(skip).limit(limit).all()


def get_active_plans(db: Session) -> List[Plan]:
    return db.query(Plan).filter(Plan.is_active == 1).all()


def update_plan(db: Session, plan_id: str, plan: PlanUpdate) -> Optional[Plan]:
    db_plan = get_plan(db, plan_id)
    if not db_plan:
        return None

    update_data = plan.dict(exclude_unset=True)
    if "skip_holidays" in update_data:
        update_data["skip_holidays"] = 1 if update_data["skip_holidays"] else 0
    if "is_active" in update_data:
        update_data["is_active"] = 1 if update_data["is_active"] else 0
    if "play_mode" in update_data:
        update_data["play_mode"] = update_data["play_mode"].value

    for key, value in update_data.items():
        setattr(db_plan, key, value)

    db.commit()
    db.refresh(db_plan)
    return db_plan


def delete_plan(db: Session, plan_id: str) -> bool:
    db_plan = get_plan(db, plan_id)
    if not db_plan:
        return False
    db.delete(db_plan)
    db.commit()
    return True


def update_plan_playback_progress(
    db: Session,
    plan_id: str,
    position: int,
    media_uri: str = "",
    duration: int = 0
) -> Optional[Plan]:
    db_plan = get_plan(db, plan_id)
    if not db_plan:
        return None

    db_plan.last_playback_position = position
    db_plan.last_playback_media_uri = media_uri
    db_plan.last_playback_time = int(time.time() * 1000)
    if duration > 0:
        db_plan.media_duration = duration

    db.commit()
    db.refresh(db_plan)
    return db_plan


def reset_plan_progress(db: Session, plan_id: str) -> Optional[Plan]:
    db_plan = get_plan(db, plan_id)
    if not db_plan:
        return None

    db_plan.last_playback_position = 0
    db_plan.last_playback_media_uri = ""
    db_plan.last_playback_time = 0

    db.commit()
    db.refresh(db_plan)
    return db_plan


# ==================== Device CRUD ====================

def create_device(db: Session, device_data: dict) -> Device:
    db_device = Device(**device_data)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def get_device(db: Session, device_id: str) -> Optional[Device]:
    return db.query(Device).filter(Device.id == device_id).first()


def get_devices(db: Session) -> List[Device]:
    return db.query(Device).all()


def update_device(db: Session, device_id: str, update_data: dict) -> Optional[Device]:
    db_device = get_device(db, device_id)
    if not db_device:
        return None

    for key, value in update_data.items():
        setattr(db_device, key, value)

    db.commit()
    db.refresh(db_device)
    return db_device


def upsert_device(db: Session, device_data: dict) -> Device:
    """Insert or update device by ID."""
    device_id = device_data.get("id")
    db_device = get_device(db, device_id)

    if db_device:
        for key, value in device_data.items():
            setattr(db_device, key, value)
    else:
        db_device = Device(**device_data)
        db.add(db_device)

    db.commit()
    db.refresh(db_device)
    return db_device


def delete_device(db: Session, device_id: str) -> bool:
    db_device = get_device(db, device_id)
    if not db_device:
        return False
    db.delete(db_device)
    db.commit()
    return True


# ==================== SMB Server CRUD ====================

def create_smb_server(db: Session, server: SmbServerCreate) -> SmbServer:
    db_server = SmbServer(
        id=str(uuid.uuid4()),
        name=server.name,
        host=server.host,
        port=server.port,
        protocol=server.protocol,
        username=server.username,
        password=server.password,
        share_path=server.share_path,
        created_at=int(time.time() * 1000)
    )
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server


def get_smb_server(db: Session, server_id: str) -> Optional[SmbServer]:
    return db.query(SmbServer).filter(SmbServer.id == server_id).first()


def get_smb_servers(db: Session) -> List[SmbServer]:
    return db.query(SmbServer).all()


def update_smb_server(db: Session, server_id: str, server: SmbServerUpdate) -> Optional[SmbServer]:
    db_server = get_smb_server(db, server_id)
    if not db_server:
        return None

    update_data = server.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_server, key, value)

    db.commit()
    db.refresh(db_server)
    return db_server


def delete_smb_server(db: Session, server_id: str) -> bool:
    db_server = get_smb_server(db, server_id)
    if not db_server:
        return False
    db.delete(db_server)
    db.commit()
    return True


def update_smb_server_connection(db: Session, server_id: str, connected: bool) -> Optional[SmbServer]:
    db_server = get_smb_server(db, server_id)
    if not db_server:
        return None

    db_server.is_connected = 1 if connected else 0
    if connected:
        db_server.last_connected_at = int(time.time() * 1000)

    db.commit()
    db.refresh(db_server)
    return db_server


# ==================== Playback History CRUD ====================

def create_playback_history(
    db: Session,
    plan: Plan,
    device: Optional[Device],
    media_url: str,
    media_name: str,
    trigger_type: TriggerType = TriggerType.SCHEDULED,
    network_type: str = "Unknown"
) -> PlaybackHistory:
    now = int(time.time() * 1000)
    db_history = PlaybackHistory(
        id=str(uuid.uuid4()),
        plan_id=plan.id,
        plan_title=plan.title,
        device_id=device.id if device else None,
        device_name=device.name if device else None,
        device_address=device.address if device else None,
        media_url=media_url,
        media_name=media_name,
        media_duration=plan.media_duration,
        actual_start_time=now,
        trigger_type=trigger_type.value,
        network_type=network_type,
        created_at=now
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history


def get_playback_history(db: Session, history_id: str) -> Optional[PlaybackHistory]:
    return db.query(PlaybackHistory).filter(PlaybackHistory.id == history_id).first()


def get_playback_histories(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    plan_id: Optional[str] = None
) -> tuple:
    query = db.query(PlaybackHistory)
    if plan_id:
        query = query.filter(PlaybackHistory.plan_id == plan_id)

    total = query.count()
    items = query.order_by(desc(PlaybackHistory.actual_start_time)).offset(skip).limit(limit).all()
    return total, items


def update_playback_history_progress(
    db: Session,
    history_id: str,
    played_duration: int,
    played_position: int
) -> Optional[PlaybackHistory]:
    db_history = get_playback_history(db, history_id)
    if not db_history:
        return None

    db_history.played_duration = played_duration
    db_history.played_position = played_position

    db.commit()
    db.refresh(db_history)
    return db_history


def end_playback_history(
    db: Session,
    history_id: str,
    played_duration: int,
    played_position: int,
    completed: bool = False,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    stop_reason: Optional[str] = None
) -> Optional[PlaybackHistory]:
    db_history = get_playback_history(db, history_id)
    if not db_history:
        return None

    db_history.actual_end_time = int(time.time() * 1000)
    db_history.played_duration = played_duration
    db_history.played_position = played_position

    if error_code:
        db_history.end_status = EndStatus.ERROR.value
        db_history.error_code = error_code
        db_history.error_message = error_message
    elif completed:
        db_history.end_status = EndStatus.COMPLETED.value
    else:
        db_history.end_status = EndStatus.STOPPED.value

    db_history.stop_reason = stop_reason

    db.commit()
    db.refresh(db_history)
    return db_history


def delete_playback_history(db: Session, history_id: str) -> bool:
    db_history = get_playback_history(db, history_id)
    if not db_history:
        return False
    db.delete(db_history)
    db.commit()
    return True


def clear_playback_history(db: Session) -> int:
    count = db.query(PlaybackHistory).delete()
    db.commit()
    return count


# ==================== Study Task CRUD ====================

def create_study_task(db: Session, task: StudyTaskCreate) -> StudyTask:
    now = int(time.time() * 1000)
    db_task = StudyTask(
        id=str(uuid.uuid4()),
        name=task.name,
        created_at=now,
        updated_at=now
    )
    db.add(db_task)
    db.flush()

    # Add media items
    total_duration = 0
    for i, media in enumerate(task.media_items):
        db_media = StudyTaskMedia(
            id=str(uuid.uuid4()),
            study_task_id=db_task.id,
            media_uri=media.media_uri,
            media_name=media.media_name,
            duration=media.duration,
            sort_order=media.sort_order if media.sort_order else i,
            source_type=media.source_type.value,
            server_id=media.server_id
        )
        db.add(db_media)
        total_duration += media.duration

    db_task.total_duration = total_duration
    db.commit()
    db.refresh(db_task)
    return db_task


def get_study_task(db: Session, task_id: str) -> Optional[StudyTask]:
    return db.query(StudyTask).filter(StudyTask.id == task_id).first()


def get_study_tasks(db: Session) -> List[StudyTask]:
    return db.query(StudyTask).order_by(desc(StudyTask.updated_at)).all()


def update_study_task(db: Session, task_id: str, task: StudyTaskUpdate) -> Optional[StudyTask]:
    db_task = get_study_task(db, task_id)
    if not db_task:
        return None

    if task.name:
        db_task.name = task.name
    db_task.updated_at = int(time.time() * 1000)

    db.commit()
    db.refresh(db_task)
    return db_task


def delete_study_task(db: Session, task_id: str) -> bool:
    db_task = get_study_task(db, task_id)
    if not db_task:
        return False
    db.delete(db_task)
    db.commit()
    return True


def reset_study_task_progress(db: Session, task_id: str) -> Optional[StudyTask]:
    db_task = get_study_task(db, task_id)
    if not db_task:
        return None

    db_task.watched_duration = 0
    db_task.updated_at = int(time.time() * 1000)

    db.commit()
    db.refresh(db_task)
    return db_task


def add_study_task_media(db: Session, task_id: str, media: StudyTaskMediaCreate) -> Optional[StudyTaskMedia]:
    db_task = get_study_task(db, task_id)
    if not db_task:
        return None

    # Get max sort order
    max_order = db.query(StudyTaskMedia).filter(
        StudyTaskMedia.study_task_id == task_id
    ).count()

    db_media = StudyTaskMedia(
        id=str(uuid.uuid4()),
        study_task_id=task_id,
        media_uri=media.media_uri,
        media_name=media.media_name,
        duration=media.duration,
        sort_order=media.sort_order if media.sort_order else max_order,
        source_type=media.source_type.value,
        server_id=media.server_id
    )
    db.add(db_media)

    # Update total duration
    db_task.total_duration += media.duration
    db_task.updated_at = int(time.time() * 1000)

    db.commit()
    db.refresh(db_media)
    return db_media


def remove_study_task_media(db: Session, task_id: str, media_id: str) -> bool:
    db_media = db.query(StudyTaskMedia).filter(
        StudyTaskMedia.id == media_id,
        StudyTaskMedia.study_task_id == task_id
    ).first()

    if not db_media:
        return False

    # Update total duration
    db_task = get_study_task(db, task_id)
    if db_task:
        db_task.total_duration -= db_media.duration
        db_task.updated_at = int(time.time() * 1000)

    db.delete(db_media)
    db.commit()
    return True


def add_watched_duration(db: Session, task_id: str, duration: int) -> Optional[StudyTask]:
    db_task = get_study_task(db, task_id)
    if not db_task:
        return None

    db_task.watched_duration += duration
    db_task.updated_at = int(time.time() * 1000)

    db.commit()
    db.refresh(db_task)
    return db_task


# ==================== Plan-StudyTask Link CRUD ====================

def link_plan_study_task(db: Session, plan_id: str, study_task_id: str, sort_order: int = 0) -> Optional[PlanStudyTask]:
    # Check if already linked
    existing = db.query(PlanStudyTask).filter(
        PlanStudyTask.plan_id == plan_id,
        PlanStudyTask.study_task_id == study_task_id
    ).first()

    if existing:
        return existing

    db_link = PlanStudyTask(
        id=str(uuid.uuid4()),
        plan_id=plan_id,
        study_task_id=study_task_id,
        sort_order=sort_order
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link


def unlink_plan_study_task(db: Session, plan_id: str, study_task_id: str) -> bool:
    db_link = db.query(PlanStudyTask).filter(
        PlanStudyTask.plan_id == plan_id,
        PlanStudyTask.study_task_id == study_task_id
    ).first()

    if not db_link:
        return False

    db.delete(db_link)
    db.commit()
    return True


def get_plan_study_tasks(db: Session, plan_id: str) -> List[StudyTask]:
    links = db.query(PlanStudyTask).filter(
        PlanStudyTask.plan_id == plan_id
    ).order_by(PlanStudyTask.sort_order).all()

    return [link.study_task for link in links if link.study_task]


def get_plan_media_playlist(db: Session, plan_id: str) -> List[StudyTaskMedia]:
    """Get all media items for a plan's linked study tasks."""
    study_tasks = get_plan_study_tasks(db, plan_id)
    media_list = []
    for task in study_tasks:
        media_items = db.query(StudyTaskMedia).filter(
            StudyTaskMedia.study_task_id == task.id
        ).order_by(StudyTaskMedia.sort_order).all()
        media_list.extend(media_items)
    return media_list
