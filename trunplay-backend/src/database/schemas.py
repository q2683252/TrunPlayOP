"""
Pydantic schemas for API request/response validation.
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# ==================== Enums ====================

class PlayMode(str, Enum):
    SEQUENTIAL = "SEQUENTIAL"
    RANDOM = "RANDOM"
    LOOP = "LOOP"
    SINGLE_LOOP = "SINGLE_LOOP"


class DeviceSource(str, Enum):
    DISCOVERED = "DISCOVERED"
    MANUAL = "MANUAL"


class TriggerType(str, Enum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"


class EndStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class PlaybackStatus(str, Enum):
    STOPPED = "STOPPED"
    LOADING = "LOADING"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class MediaSourceType(str, Enum):
    LOCAL = "LOCAL"
    SMB = "SMB"


class MediaType(str, Enum):
    FOLDER = "FOLDER"
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    UNKNOWN = "UNKNOWN"


# ==================== Base Response ====================

class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Optional[dict] = None


# ==================== Plan Schemas ====================

class PlanBase(BaseModel):
    title: str
    start_time: str  # "09:00"
    end_time: str    # "17:00"
    repeat_days: str  # "1,2,3,4,5"
    skip_holidays: bool = False
    device_id: Optional[str] = None
    media_url: str
    is_active: bool = True
    play_mode: PlayMode = PlayMode.SEQUENTIAL


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    repeat_days: Optional[str] = None
    skip_holidays: Optional[bool] = None
    device_id: Optional[str] = None
    media_url: Optional[str] = None
    is_active: Optional[bool] = None
    play_mode: Optional[PlayMode] = None


class PlanResponse(PlanBase):
    id: str
    created_at: int
    last_playback_position: int = 0
    last_playback_media_uri: str = ""
    last_playback_time: int = 0
    media_duration: int = 0
    media_name: str = ""

    class Config:
        orm_mode = True


# ==================== Device Schemas ====================

class DeviceBase(BaseModel):
    name: str
    address: str
    type: str = "MediaRenderer"
    manufacturer: str = ""


class DeviceCreate(BaseModel):
    address: str
    port: int = 8200


class DeviceResponse(DeviceBase):
    id: str
    is_online: bool = False
    last_seen: int = 0
    location_url: str = ""
    source: DeviceSource = DeviceSource.DISCOVERED

    class Config:
        orm_mode = True


# ==================== SMB Server Schemas ====================

class SmbServerBase(BaseModel):
    name: str
    host: str
    port: int = 445
    protocol: str = "SMB"
    username: str = ""
    password: str = ""
    share_path: str = ""


class SmbServerCreate(SmbServerBase):
    pass


class SmbServerUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    share_path: Optional[str] = None


class SmbServerResponse(SmbServerBase):
    id: str
    is_connected: bool = False
    last_connected_at: int = 0
    created_at: int
    hostname: str = ""

    class Config:
        orm_mode = True


class SmbTestRequest(BaseModel):
    host: str
    port: int = 445
    username: str = ""
    password: str = ""


# ==================== Media Schemas ====================

class MediaItem(BaseModel):
    id: str
    name: str
    path: str
    uri: str
    type: MediaType
    source_type: MediaSourceType = MediaSourceType.LOCAL
    server_id: Optional[str] = None
    size: int = 0
    last_modified: int = 0


class MediaBrowseResponse(BaseModel):
    path: str
    parent_path: Optional[str] = None
    items: List[MediaItem] = []


# ==================== Playback Schemas ====================

class PlaybackState(BaseModel):
    status: PlaybackStatus = PlaybackStatus.STOPPED
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    plan_id: Optional[str] = None
    plan_title: Optional[str] = None
    media_url: Optional[str] = None
    media_name: Optional[str] = None
    position: int = 0
    duration: int = 0
    volume: int = 50


class PlayRequest(BaseModel):
    plan_id: str
    start_position: int = 0


class SeekRequest(BaseModel):
    position: int


class VolumeRequest(BaseModel):
    level: int = Field(..., ge=0, le=100)


# ==================== History Schemas ====================

class PlaybackHistoryResponse(BaseModel):
    id: str
    plan_id: str
    plan_title: str
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    device_address: Optional[str] = None
    media_url: str
    media_name: str
    media_duration: int = 0
    actual_start_time: int
    actual_end_time: Optional[int] = None
    played_duration: int = 0
    played_position: int = 0
    end_status: EndStatus = EndStatus.IN_PROGRESS
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    stop_reason: Optional[str] = None
    trigger_type: TriggerType = TriggerType.SCHEDULED
    created_at: int

    class Config:
        orm_mode = True


class HistoryListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[PlaybackHistoryResponse]


# ==================== Study Task Schemas ====================

class StudyTaskMediaBase(BaseModel):
    media_uri: str
    media_name: str
    duration: int = 0
    sort_order: int = 0
    source_type: MediaSourceType = MediaSourceType.LOCAL
    server_id: Optional[str] = None


class StudyTaskMediaCreate(StudyTaskMediaBase):
    pass


class StudyTaskMediaResponse(StudyTaskMediaBase):
    id: str
    study_task_id: str
    thumbnail_path: Optional[str] = None

    class Config:
        orm_mode = True


class StudyTaskBase(BaseModel):
    name: str


class StudyTaskCreate(StudyTaskBase):
    media_items: List[StudyTaskMediaCreate] = []


class StudyTaskUpdate(BaseModel):
    name: Optional[str] = None


class StudyTaskResponse(StudyTaskBase):
    id: str
    total_duration: int = 0
    watched_duration: int = 0
    created_at: int
    updated_at: int
    media_items: List[StudyTaskMediaResponse] = []

    class Config:
        orm_mode = True


# ==================== System Schemas ====================

class SystemStatus(BaseModel):
    version: str
    uptime: int
    db_size: int
    playback_status: PlaybackStatus
    active_plans: int
    total_devices: int


class SystemConfig(BaseModel):
    api_port: int = 8088
    media_port: int = 8089
    local_media_paths: List[str] = ["/mnt", "/tmp"]
    log_level: str = "INFO"


# ==================== Share Info ====================

class SmbShareInfo(BaseModel):
    name: str
    path: str
