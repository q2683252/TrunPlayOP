"""
Playback Service - Orchestrates playback operations.
Coordinates DLNA manager, media server, and database.
"""
import asyncio
import logging
import time
from typing import Optional, List
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..database import crud
from ..database.models import Plan, Device, SmbServer
from ..database.schemas import TriggerType, PlaybackStatus
from .dlna_manager import get_dlna_manager, DlnaDevice, PlaybackState
from .media_server import get_media_server
from .smb_client import get_smb_client

logger = logging.getLogger(__name__)


# Resume offset (seconds to rewind when resuming)
RESUME_OFFSET_SECONDS = 10
# Progress save interval
PROGRESS_SAVE_INTERVAL = 5.0
# Completion threshold (seconds before end to consider complete)
COMPLETION_THRESHOLD = 5


@dataclass
class PlaybackInfo:
    """Current playback information."""
    status: PlaybackStatus
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    plan_id: Optional[str] = None
    plan_title: Optional[str] = None
    media_url: Optional[str] = None
    media_name: Optional[str] = None
    position: int = 0
    duration: int = 0
    volume: int = 50


class PlaybackService:
    """
    Manages playback lifecycle and progress tracking.
    """

    def __init__(self):
        self._dlna_manager = get_dlna_manager()
        self._media_server = get_media_server()
        self._smb_client = get_smb_client()
        self._progress_task: Optional[asyncio.Task] = None
        self._current_plan_id: Optional[str] = None
        self._current_history_id: Optional[str] = None
        self._playback_start_time: int = 0
        self._db_session_factory = None

    def set_db_session_factory(self, factory):
        """Set database session factory for progress tracking."""
        self._db_session_factory = factory

    async def start_playback(
        self,
        db: Session,
        plan: Plan,
        trigger_type: TriggerType = TriggerType.SCHEDULED,
        start_position: int = 0
    ) -> bool:
        """
        Start playback for a plan.
        """
        logger.info(f"[start_playback] plan={plan.id}, trigger={trigger_type}, pos={start_position}")

        # Get device
        if not plan.device_id:
            logger.error("No device assigned to plan")
            return False

        device_model = crud.get_device(db, plan.device_id)
        if not device_model:
            logger.error(f"Device not found: {plan.device_id}")
            return False

        # Ensure device is in DLNA manager cache
        dlna_device = self._dlna_manager.get_device(device_model.id)
        if not dlna_device:
            # Try to add from database
            dlna_device = DlnaDevice(
                id=device_model.id,
                name=device_model.name,
                address=device_model.address,
                type=device_model.type,
                manufacturer=device_model.manufacturer,
                location_url=device_model.location_url
            )
            self._dlna_manager._devices[device_model.id] = dlna_device

        # Prepare media URL
        media_url = plan.media_url
        media_name = plan.media_name or self._extract_filename(media_url)

        # Convert to HTTP URL if needed
        http_url = await self._prepare_media_url(db, media_url, media_name)
        if not http_url:
            logger.error(f"Failed to prepare media URL: {media_url}")
            return False

        # Calculate resume position
        resume_pos = start_position
        if resume_pos == 0 and plan.last_playback_position > 0:
            resume_pos = max(0, plan.last_playback_position - RESUME_OFFSET_SECONDS)
            logger.info(f"Resuming from position: {resume_pos}s (saved: {plan.last_playback_position})")

        # Stop any existing playback
        await self.stop_playback(db)

        # Create playback history record
        self._current_history_id = crud.create_playback_history(
            db=db,
            plan=plan,
            device=device_model,
            media_url=media_url,
            media_name=media_name,
            trigger_type=trigger_type
        ).id
        self._playback_start_time = int(time.time() * 1000)

        # Start playback
        success = await self._dlna_manager.play_media(
            device=dlna_device,
            media_url=http_url,
            media_name=media_name,
            start_position=resume_pos,
            plan_id=plan.id,
            plan_title=plan.title
        )

        if success:
            self._current_plan_id = plan.id
            # Start progress tracking
            self._start_progress_tracking(plan.id)
            logger.info(f"Playback started for plan {plan.id}")
        else:
            # Record failure
            if self._current_history_id:
                crud.end_playback_history(
                    db=db,
                    history_id=self._current_history_id,
                    played_duration=0,
                    played_position=0,
                    error_code="PLAYBACK_FAILED",
                    error_message="Failed to start playback on device"
                )
            self._current_history_id = None
            logger.error("Failed to start playback")

        return success

    async def stop_playback(self, db: Optional[Session] = None) -> bool:
        """Stop current playback."""
        # Stop progress tracking
        self._stop_progress_tracking()

        # Record end in history
        if db and self._current_history_id:
            playback = self._dlna_manager.current_playback
            played_duration = int(time.time() * 1000) - self._playback_start_time
            crud.end_playback_history(
                db=db,
                history_id=self._current_history_id,
                played_duration=played_duration,
                played_position=playback.position,
                stop_reason="USER_STOP"
            )

        # Stop DLNA playback
        success = await self._dlna_manager.stop()

        # Clear state
        self._current_plan_id = None
        self._current_history_id = None
        self._playback_start_time = 0

        # Clear media server registrations
        self._media_server.clear_all_media()

        return success

    async def pause(self) -> bool:
        """Pause playback."""
        return await self._dlna_manager.pause()

    async def resume(self) -> bool:
        """Resume playback."""
        return await self._dlna_manager.resume()

    async def seek(self, position: int) -> bool:
        """Seek to position."""
        return await self._dlna_manager.seek(position)

    async def set_volume(self, level: int) -> bool:
        """Set volume."""
        return await self._dlna_manager.set_volume(level)

    async def get_volume(self) -> int:
        """Get current volume."""
        return await self._dlna_manager.get_volume()

    def get_playback_info(self) -> PlaybackInfo:
        """Get current playback information."""
        playback = self._dlna_manager.current_playback

        status_map = {
            PlaybackState.STOPPED: PlaybackStatus.STOPPED,
            PlaybackState.LOADING: PlaybackStatus.LOADING,
            PlaybackState.PLAYING: PlaybackStatus.PLAYING,
            PlaybackState.PAUSED: PlaybackStatus.PAUSED,
            PlaybackState.ERROR: PlaybackStatus.ERROR,
        }

        return PlaybackInfo(
            status=status_map.get(playback.state, PlaybackStatus.STOPPED),
            device_id=playback.device.id if playback.device else None,
            device_name=playback.device.name if playback.device else None,
            plan_id=playback.plan_id,
            plan_title=playback.plan_title,
            media_url=playback.media_url,
            media_name=playback.media_name,
            position=playback.position,
            duration=playback.duration,
            volume=playback.volume
        )

    async def get_position_info(self) -> Optional[dict]:
        """Get position info from device."""
        info = await self._dlna_manager.get_position_info()
        if info:
            return {"position": info.position, "duration": info.duration}
        return None

    async def _prepare_media_url(
        self,
        db: Session,
        media_url: str,
        media_name: str
    ) -> Optional[str]:
        """Convert media URL to HTTP URL for DLNA."""
        # Already HTTP
        if media_url.startswith("http://") or media_url.startswith("https://"):
            return media_url

        # SMB URL
        if media_url.startswith("smb://"):
            return await self._prepare_smb_url(db, media_url, media_name)

        # Local file
        if media_url.startswith("/") or media_url.startswith("file://"):
            path = media_url.replace("file://", "")
            return self._media_server.register_local_media(path, media_name)

        logger.warning(f"Unknown URL scheme: {media_url}")
        return None

    async def _prepare_smb_url(
        self,
        db: Session,
        smb_url: str,
        media_name: str
    ) -> Optional[str]:
        """Convert SMB URL to HTTP URL."""
        try:
            # Parse SMB URL: smb://host/share/path
            url_without_scheme = smb_url[6:]  # Remove "smb://"
            parts = url_without_scheme.split("/", 1)
            host = parts[0]
            path = "/" + parts[1] if len(parts) > 1 else "/"

            # Find matching SMB server config
            servers = crud.get_smb_servers(db)
            server = None
            for s in servers:
                if s.host == host or host.startswith(s.host):
                    server = s
                    break

            if not server:
                logger.warning(f"No SMB server config found for host: {host}")
                # Create anonymous connection
                server = SmbServer(
                    id="temp",
                    name=host,
                    host=host,
                    port=445,
                    username="",
                    password=""
                )

            # Get file size
            file_size = await self._smb_client.get_file_size(
                host=server.host,
                path=path,
                port=server.port,
                username=server.username,
                password=server.password
            )

            # Register with media server
            http_url = self._media_server.register_smb_media(
                smb_path=path,
                file_name=media_name,
                file_size=file_size,
                smb_host=server.host,
                smb_port=server.port,
                smb_username=server.username,
                smb_password=server.password
            )

            return http_url

        except Exception as e:
            logger.error(f"Error preparing SMB URL: {e}")
            return None

    def _start_progress_tracking(self, plan_id: str):
        """Start background progress tracking task."""
        self._stop_progress_tracking()

        async def track_progress():
            while True:
                await asyncio.sleep(PROGRESS_SAVE_INTERVAL)

                try:
                    # Check playback state
                    state = self._dlna_manager.playback_state
                    if state not in (PlaybackState.PLAYING, PlaybackState.PAUSED):
                        logger.debug(f"Progress tracking stopped: state={state}")
                        break

                    # Get position from device
                    pos_info = await self._dlna_manager.get_position_info()
                    if not pos_info:
                        continue

                    position = pos_info.position
                    duration = pos_info.duration

                    # Save progress to database
                    if self._db_session_factory:
                        db = self._db_session_factory()
                        try:
                            crud.update_plan_playback_progress(
                                db=db,
                                plan_id=plan_id,
                                position=position,
                                duration=duration * 1000  # Convert to ms
                            )

                            # Update history
                            if self._current_history_id:
                                played_duration = int(time.time() * 1000) - self._playback_start_time
                                crud.update_playback_history_progress(
                                    db=db,
                                    history_id=self._current_history_id,
                                    played_duration=played_duration,
                                    played_position=position
                                )
                        finally:
                            db.close()

                    # Check for completion
                    if duration > 0 and position >= duration - COMPLETION_THRESHOLD:
                        logger.info(f"Playback complete: {position}/{duration}")
                        if self._db_session_factory:
                            db = self._db_session_factory()
                            try:
                                crud.reset_plan_progress(db, plan_id)
                                if self._current_history_id:
                                    crud.end_playback_history(
                                        db=db,
                                        history_id=self._current_history_id,
                                        played_duration=int(time.time() * 1000) - self._playback_start_time,
                                        played_position=position,
                                        completed=True
                                    )
                            finally:
                                db.close()
                        break

                except Exception as e:
                    logger.error(f"Progress tracking error: {e}")

        self._progress_task = asyncio.create_task(track_progress())
        logger.debug(f"Progress tracking started for plan {plan_id}")

    def _stop_progress_tracking(self):
        """Stop progress tracking task."""
        if self._progress_task:
            self._progress_task.cancel()
            self._progress_task = None

    def _extract_filename(self, url: str) -> str:
        """Extract filename from URL."""
        try:
            from urllib.parse import urlparse, unquote
            path = urlparse(url).path
            return unquote(path.split("/")[-1])
        except Exception:
            return "Media"


# Global instance
_playback_service: Optional[PlaybackService] = None


def get_playback_service() -> PlaybackService:
    """Get global playback service instance."""
    global _playback_service
    if _playback_service is None:
        _playback_service = PlaybackService()
    return _playback_service
