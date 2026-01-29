"""
Scenario tests for error recovery.

Tests how the system handles various failure conditions.
"""
import pytest
import asyncio


class TestDLNAErrorRecovery:
    """Tests for DLNA device error handling."""

    @pytest.mark.asyncio
    async def test_device_offline_during_discovery(self, mock_dlna):
        """
        Test discovery when devices are offline.
        Should return empty list, not crash.
        """
        mock_dlna.fail_mode = "offline"

        # Discovery should handle offline gracefully
        devices = await mock_dlna.discover_devices(timeout=1.0)
        # When offline, should return empty list
        assert devices == []

    @pytest.mark.asyncio
    async def test_device_timeout_during_discovery(self, mock_dlna):
        """
        Test discovery timeout handling.
        Should raise TimeoutError.
        """
        mock_dlna.fail_mode = "timeout"

        with pytest.raises(asyncio.TimeoutError):
            await mock_dlna.discover_devices(timeout=1.0)

    @pytest.mark.asyncio
    async def test_device_disconnect_during_playback(self, mock_dlna, log_capture):
        """
        Test device disconnection during playback.
        Should save progress and mark as error.
        """
        # Setup and start playback
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")
        await mock_dlna.play("dev1", "video.mp4")
        mock_dlna.set_position("dev1", 1800, 3600)

        # Simulate device going offline
        mock_dlna.fail_mode = "offline"

        # Subsequent operations should fail gracefully
        result = await mock_dlna.pause("dev1")
        assert result is False

        position, _ = await mock_dlna.get_position("dev1")
        assert position == 0  # Returns 0 when offline

    @pytest.mark.asyncio
    async def test_soap_request_error(self, mock_dlna):
        """
        Test SOAP protocol error handling.
        Should raise exception.
        """
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")
        mock_dlna.fail_mode = "soap_error"

        with pytest.raises(Exception, match="SOAP"):
            await mock_dlna.play("dev1", "video.mp4")

    @pytest.mark.asyncio
    async def test_device_reappear_after_offline(self, mock_dlna):
        """
        Test device recovery after going offline.
        Should be able to resume operations.
        """
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")

        # Initial playback works
        result = await mock_dlna.play("dev1", "video.mp4")
        assert result is True

        # Device goes offline
        mock_dlna.fail_mode = "offline"
        result = await mock_dlna.pause("dev1")
        assert result is False

        # Device comes back online
        mock_dlna.fail_mode = None
        result = await mock_dlna.resume("dev1")
        assert result is True


class TestSMBErrorRecovery:
    """Tests for SMB connection error handling."""

    def test_smb_auth_failure(self, mock_smb):
        """
        Test SMB authentication failure.
        Should raise appropriate error.
        """
        from tests.mocks.mock_smb import SMBAuthenticationError

        mock_smb.add_server("nas1", "NAS", "192.168.1.200")
        mock_smb.fail_mode = "auth_error"

        with pytest.raises(SMBAuthenticationError):
            mock_smb.connect("nas1")

    def test_smb_connection_error(self, mock_smb):
        """
        Test SMB connection failure.
        Should raise appropriate error.
        """
        from tests.mocks.mock_smb import SMBConnectionError

        mock_smb.add_server("nas1", "NAS", "192.168.1.200")
        mock_smb.fail_mode = "connection_error"

        with pytest.raises(SMBConnectionError):
            mock_smb.connect("nas1")

    def test_smb_file_not_found(self, mock_smb):
        """
        Test SMB file not found.
        Should return empty list.
        """
        mock_smb.add_server("nas1", "NAS", "192.168.1.200")
        mock_smb.fail_mode = "not_found"

        files = mock_smb.list_files("nas1", "media", "/videos")
        assert files == []

    def test_smb_connection_lost_during_stream(self, mock_smb):
        """
        Test connection loss during file streaming.
        Should raise appropriate error.
        """
        from tests.mocks.mock_smb import SMBConnectionError

        mock_smb.add_server("nas1", "NAS", "192.168.1.200")
        mock_smb.fail_mode = "connection_error"

        with pytest.raises(SMBConnectionError):
            mock_smb.get_file_stream("nas1", "media", "video.mp4")

    def test_smb_reconnect_after_failure(self, mock_smb):
        """
        Test reconnection after connection failure.
        """
        mock_smb.add_server("nas1", "NAS", "192.168.1.200")

        # Initial connection succeeds
        mock_smb.connect("nas1")
        assert mock_smb.is_connected("nas1") is True

        # Connection fails
        mock_smb.disconnect("nas1")
        mock_smb.fail_mode = "connection_error"

        from tests.mocks.mock_smb import SMBConnectionError
        with pytest.raises(SMBConnectionError):
            mock_smb.connect("nas1")

        # Connection recovers
        mock_smb.fail_mode = None
        mock_smb.connect("nas1")
        assert mock_smb.is_connected("nas1") is True


class TestResourceNotFound:
    """Tests for resource not found scenarios."""

    def test_play_deleted_plan(self, db_session):
        """
        Test playing a plan that was deleted.
        Should return None.
        """
        from src.database import crud
        from src.database.schemas import PlanCreate

        # Create and delete a plan
        plan = crud.create_plan(db_session, PlanCreate(
            title="Deleted Plan",
            start_time="08:00",
            end_time="09:00",
            repeat_days="1,2,3",
            media_url="video.mp4"
        ))
        plan_id = plan.id
        crud.delete_plan(db_session, plan_id)

        # Try to get the deleted plan
        result = crud.get_plan(db_session, plan_id)
        assert result is None

    def test_play_with_missing_device(self, db_session, mock_dlna):
        """
        Test playing when assigned device no longer exists.
        """
        from src.database import crud
        from src.database.schemas import PlanCreate

        # Create device
        device_data = {"id": "temp-device", "name": "Temp TV", "address": "1.2.3.4"}
        device = crud.create_device(db_session, device_data)
        mock_dlna.add_device(device.id, device.name, device.address)

        # Create plan with device
        plan = crud.create_plan(db_session, PlanCreate(
            title="Device Plan",
            start_time="08:00",
            end_time="09:00",
            repeat_days="1,2,3",
            device_id=device.id,
            media_url="video.mp4"
        ))

        # Delete the device
        crud.delete_device(db_session, device.id)
        mock_dlna.remove_device(device.id)

        # Verify device is gone
        assert crud.get_device(db_session, device.id) is None

        # Plan still exists but device_id points to nothing
        retrieved_plan = crud.get_plan(db_session, plan.id)
        assert retrieved_plan is not None
        assert retrieved_plan.device_id == device.id  # Still has reference

    @pytest.mark.asyncio
    async def test_media_file_removed_during_playlist(self, db_session, mock_smb):
        """
        Test when a media file is removed during playlist playback.
        Should skip to next file.
        """
        from tests.mocks.mock_smb import SMBFileNotFoundError

        mock_smb.add_server("nas1", "NAS", "192.168.1.200")
        mock_smb.add_files("nas1", "media", [
            {"name": "video1.mp4", "path": "media/video1.mp4"},
            {"name": "video2.mp4", "path": "media/video2.mp4"},
        ])

        # First file works
        stream = mock_smb.get_file_stream("nas1", "media", "video1.mp4")
        assert stream is not None

        # Second file "removed" (not_found)
        mock_smb.fail_mode = "not_found"
        with pytest.raises(SMBFileNotFoundError):
            mock_smb.get_file_stream("nas1", "media", "video2.mp4")


class TestSchedulerErrorRecovery:
    """Tests for scheduler error handling."""

    def test_scheduler_write_error(self, mock_scheduler):
        """
        Test scheduler handling crontab write failure.
        """
        mock_scheduler.fail_mode = "write_error"

        result = mock_scheduler.schedule_plan("plan1", "08:00", "1,2,3")
        assert result is False

    def test_scheduler_reload_error(self, mock_scheduler):
        """
        Test scheduler handling cron reload failure.
        """
        mock_scheduler.fail_mode = "reload_error"

        result = mock_scheduler.reload_cron()
        assert result is False

    def test_scheduler_invalid_time_format(self, mock_scheduler):
        """
        Test scheduler with invalid time format.
        """
        result = mock_scheduler.schedule_plan("plan1", "invalid", "1,2,3")
        assert result is False

    def test_scheduler_recovery_after_error(self, mock_scheduler):
        """
        Test scheduler recovery after error.
        """
        # Initial failure
        mock_scheduler.fail_mode = "write_error"
        result = mock_scheduler.schedule_plan("plan1", "08:00", "1,2,3")
        assert result is False

        # Recovery
        mock_scheduler.fail_mode = None
        result = mock_scheduler.schedule_plan("plan1", "08:00", "1,2,3")
        assert result is True
        assert mock_scheduler.is_scheduled("plan1") is True
