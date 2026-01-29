"""
Test data factory for creating test fixtures.

Provides consistent test data creation across all test modules.
"""
import uuid
from typing import Any, Dict, Optional
from datetime import datetime


class Factory:
    """Factory for creating test data."""

    @staticmethod
    def plan(db_session, **overrides) -> Any:
        """
        Create a test Plan record.

        Args:
            db_session: SQLAlchemy session
            **overrides: Fields to override

        Returns:
            Created Plan instance
        """
        from src.database import crud

        defaults = {
            "id": str(uuid.uuid4()),
            "title": "Test Plan",
            "device_id": None,
            "media_url": "smb://nas/media/video.mp4",
            "media_type": "video",
            "is_active": True,
            "play_mode": "sequential",
            "schedule_time": "08:00",
            "schedule_days": "1,2,3,4,5",
            "current_index": 0,
            "current_position": 0,
            "skip_holidays": False,
        }
        data = {**defaults, **overrides}
        return crud.create_plan(db_session, data)

    @staticmethod
    def device(db_session, **overrides) -> Any:
        """
        Create a test Device record.

        Args:
            db_session: SQLAlchemy session
            **overrides: Fields to override

        Returns:
            Created Device instance
        """
        from src.database import crud

        defaults = {
            "id": str(uuid.uuid4()),
            "name": "Mock TV",
            "address": "192.168.1.100",
            "port": 1400,
            "location": "http://192.168.1.100:1400/description.xml",
            "manufacturer": "Mock",
            "model": "Test Device",
            "is_online": True,
        }
        data = {**defaults, **overrides}
        return crud.create_device(db_session, data)

    @staticmethod
    def smb_server(db_session, **overrides) -> Any:
        """
        Create a test SmbServer record.

        Args:
            db_session: SQLAlchemy session
            **overrides: Fields to override

        Returns:
            Created SmbServer instance
        """
        from src.database import crud

        defaults = {
            "id": str(uuid.uuid4()),
            "name": "Test NAS",
            "address": "192.168.1.200",
            "port": 445,
            "username": "admin",
            "password": "password123",
            "share": "media",
            "is_connected": False,
        }
        data = {**defaults, **overrides}
        return crud.create_smb_server(db_session, data)

    @staticmethod
    def playback_history(db_session, plan_id: str, **overrides) -> Any:
        """
        Create a test PlaybackHistory record.

        Args:
            db_session: SQLAlchemy session
            plan_id: Associated plan ID
            **overrides: Fields to override

        Returns:
            Created PlaybackHistory instance
        """
        from src.database import crud

        defaults = {
            "id": str(uuid.uuid4()),
            "plan_id": plan_id,
            "plan_title": "Test Plan",
            "device_id": None,
            "device_name": "Test Device",
            "media_url": "smb://nas/media/video.mp4",
            "media_name": "video.mp4",
            "status": "completed",
            "trigger": "manual",
            "duration": 3600,
            "position": 3600,
            "error_message": None,
        }
        data = {**defaults, **overrides}
        return crud.create_playback_history(db_session, data)

    @staticmethod
    def study_task(db_session, **overrides) -> Any:
        """
        Create a test StudyTask record.

        Args:
            db_session: SQLAlchemy session
            **overrides: Fields to override

        Returns:
            Created StudyTask instance
        """
        from src.database import crud

        defaults = {
            "id": str(uuid.uuid4()),
            "name": "Test Study Task",
            "description": "A test study task",
            "total_duration": 0,
            "watched_duration": 0,
        }
        data = {**defaults, **overrides}
        return crud.create_study_task(db_session, data)

    @staticmethod
    def study_task_media(db_session, task_id: str, **overrides) -> Any:
        """
        Create a test StudyTaskMedia record.

        Args:
            db_session: SQLAlchemy session
            task_id: Associated study task ID
            **overrides: Fields to override

        Returns:
            Created StudyTaskMedia instance
        """
        from src.database import crud

        defaults = {
            "task_id": task_id,
            "title": "Test Video",
            "url": "smb://nas/media/study/video.mp4",
            "duration": 1800,
            "order": 0,
        }
        data = {**defaults, **overrides}
        return crud.add_study_task_media(db_session, task_id, data)

    # ==================== Convenience Methods ====================

    @staticmethod
    def plan_with_device(db_session, **plan_overrides) -> tuple:
        """
        Create a Plan with an associated Device.

        Returns:
            Tuple of (plan, device)
        """
        device = Factory.device(db_session)
        plan = Factory.plan(db_session, device_id=device.id, **plan_overrides)
        return plan, device

    @staticmethod
    def plan_with_history(db_session, history_count: int = 3, **plan_overrides) -> tuple:
        """
        Create a Plan with PlaybackHistory records.

        Returns:
            Tuple of (plan, list of history records)
        """
        plan = Factory.plan(db_session, **plan_overrides)
        histories = []
        for i in range(history_count):
            history = Factory.playback_history(
                db_session,
                plan_id=plan.id,
                plan_title=plan.title,
                status="completed" if i < history_count - 1 else "playing",
            )
            histories.append(history)
        return plan, histories

    @staticmethod
    def smb_server_with_files(db_session, mock_smb, file_count: int = 5, **server_overrides) -> tuple:
        """
        Create an SmbServer with mock files.

        Args:
            db_session: SQLAlchemy session
            mock_smb: MockSMBClient instance
            file_count: Number of mock files to create
            **server_overrides: Fields to override

        Returns:
            Tuple of (server, list of file entries)
        """
        server = Factory.smb_server(db_session, **server_overrides)

        # Add server to mock
        mock_smb.add_server(server.id, server.name, server.address)

        # Create mock files
        files = []
        for i in range(file_count):
            file_entry = {
                "name": f"video_{i:02d}.mp4",
                "path": f"media/video_{i:02d}.mp4",
                "size": 1024 * 1024 * (i + 1),
                "is_directory": False,
            }
            files.append(file_entry)

        mock_smb.add_files(server.id, "media", files)

        return server, files

    @staticmethod
    def complete_playback_setup(db_session, mock_dlna, mock_smb) -> Dict[str, Any]:
        """
        Create a complete playback setup with all related entities.

        Args:
            db_session: SQLAlchemy session
            mock_dlna: MockDLNAManager instance
            mock_smb: MockSMBClient instance

        Returns:
            Dict with plan, device, smb_server, and files
        """
        # Create device and add to mock
        device = Factory.device(db_session)
        mock_dlna.add_device(device.id, device.name, device.address)

        # Create SMB server with files
        server, files = Factory.smb_server_with_files(db_session, mock_smb)

        # Create plan with device and SMB media
        plan = Factory.plan(
            db_session,
            device_id=device.id,
            media_url=f"smb://{server.id}/{files[0]['path']}",
        )

        return {
            "plan": plan,
            "device": device,
            "smb_server": server,
            "files": files,
        }
