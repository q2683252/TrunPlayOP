"""
SQLAlchemy database models for TrunPlay.
Mirrors the Android Room database structure.
"""
import os
from sqlalchemy import (
    create_engine, Column, String, Integer, Text, ForeignKey,
    Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Database path
DB_PATH = os.environ.get("TRUNPLAY_DB_PATH", "/etc/trunplay/trunplay.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Plan(Base):
    """播放计划表"""
    __tablename__ = "plans"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    start_time = Column(String, nullable=False)  # "09:00"
    end_time = Column(String, nullable=False)    # "17:00"
    repeat_days = Column(String, nullable=False) # "1,2,3,4,5"
    skip_holidays = Column(Integer, default=0)
    device_id = Column(String, ForeignKey("devices.id"), nullable=True)
    media_url = Column(Text, nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(Integer, nullable=False)
    last_playback_position = Column(Integer, default=0)
    last_playback_media_uri = Column(Text, default="")
    last_playback_time = Column(Integer, default=0)
    media_duration = Column(Integer, default=0)
    media_name = Column(String, default="")
    play_mode = Column(String, default="SEQUENTIAL")

    # Relationships
    device = relationship("Device", back_populates="plans")
    study_task_links = relationship("PlanStudyTask", back_populates="plan", cascade="all, delete-orphan")


class Device(Base):
    """DLNA 设备表"""
    __tablename__ = "devices"

    id = Column(String, primary_key=True)  # UDN
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)  # IP
    type = Column(String, default="MediaRenderer")
    manufacturer = Column(String, default="")
    is_online = Column(Integer, default=0)
    last_seen = Column(Integer, default=0)
    location_url = Column(Text, default="")
    source = Column(String, default="DISCOVERED")  # DISCOVERED / MANUAL

    # Relationships
    plans = relationship("Plan", back_populates="device")


class SmbServer(Base):
    """SMB 服务器表"""
    __tablename__ = "smb_servers"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    host = Column(String, nullable=False)
    port = Column(Integer, default=445)
    protocol = Column(String, default="SMB")
    username = Column(String, default="")
    password = Column(String, default="")
    share_path = Column(String, default="")
    is_connected = Column(Integer, default=0)
    last_connected_at = Column(Integer, default=0)
    created_at = Column(Integer, nullable=False)
    hostname = Column(String, default="")
    last_known_host = Column(String, default="")


class PlaybackHistory(Base):
    """播放历史表"""
    __tablename__ = "playback_history"

    id = Column(String, primary_key=True)
    plan_id = Column(String, nullable=False)
    plan_title = Column(String, nullable=False)
    device_id = Column(String, nullable=True)
    device_name = Column(String, nullable=True)
    device_address = Column(String, nullable=True)
    media_url = Column(Text, nullable=False)
    media_name = Column(String, nullable=False)
    media_duration = Column(Integer, default=0)
    actual_start_time = Column(Integer, nullable=False)
    actual_end_time = Column(Integer, nullable=True)
    played_duration = Column(Integer, default=0)
    played_position = Column(Integer, default=0)
    end_status = Column(String, default="IN_PROGRESS")
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    stop_reason = Column(String, nullable=True)
    network_type = Column(String, nullable=True)
    trigger_type = Column(String, default="SCHEDULED")
    created_at = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_history_plan_id", "plan_id"),
        Index("idx_history_start_time", "actual_start_time"),
        Index("idx_history_end_status", "end_status"),
    )


class StudyTask(Base):
    """学习任务表"""
    __tablename__ = "study_tasks"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    total_duration = Column(Integer, default=0)
    watched_duration = Column(Integer, default=0)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)

    # Relationships
    media_items = relationship("StudyTaskMedia", back_populates="study_task", cascade="all, delete-orphan")
    plan_links = relationship("PlanStudyTask", back_populates="study_task", cascade="all, delete-orphan")


class StudyTaskMedia(Base):
    """学习任务媒体表"""
    __tablename__ = "study_task_media"

    id = Column(String, primary_key=True)
    study_task_id = Column(String, ForeignKey("study_tasks.id", ondelete="CASCADE"), nullable=False)
    media_uri = Column(Text, nullable=False)
    media_name = Column(String, nullable=False)
    duration = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    source_type = Column(String, default="LOCAL")
    server_id = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)

    # Relationships
    study_task = relationship("StudyTask", back_populates="media_items")

    __table_args__ = (
        Index("idx_study_media_task_id", "study_task_id"),
        Index("idx_study_media_sort_order", "sort_order"),
    )


class PlanStudyTask(Base):
    """计划与学习任务关联表"""
    __tablename__ = "plan_study_tasks"

    id = Column(String, primary_key=True)
    plan_id = Column(String, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    study_task_id = Column(String, ForeignKey("study_tasks.id", ondelete="CASCADE"), nullable=False)
    sort_order = Column(Integer, default=0)

    # Relationships
    plan = relationship("Plan", back_populates="study_task_links")
    study_task = relationship("StudyTask", back_populates="plan_links")

    __table_args__ = (
        UniqueConstraint("plan_id", "study_task_id", name="uq_plan_study_task"),
        Index("idx_plan_study_tasks_plan", "plan_id"),
        Index("idx_plan_study_tasks_study_task", "study_task_id"),
    )


def init_db():
    """Initialize database tables."""
    # Ensure directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    Base.metadata.create_all(bind=engine)
