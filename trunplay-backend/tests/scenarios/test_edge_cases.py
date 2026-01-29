"""
Scenario tests for edge cases and boundary conditions.
"""
import pytest


class TestVolumeEdgeCases:
    """Tests for volume control edge cases."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("input_level,expected_min,expected_max", [
        (-100, 0, 0),
        (-1, 0, 0),
        (0, 0, 0),
        (50, 50, 50),
        (100, 100, 100),
        (101, 100, 100),
        (1000, 100, 100),
    ])
    async def test_volume_clamping(self, mock_dlna, input_level, expected_min, expected_max):
        """
        Test volume is clamped to 0-100 range.
        """
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")

        await mock_dlna.set_volume("dev1", input_level)
        volume = await mock_dlna.get_volume("dev1")

        assert expected_min <= volume <= expected_max


class TestSeekEdgeCases:
    """Tests for seek position edge cases."""

    @pytest.mark.asyncio
    async def test_seek_to_exact_start(self, mock_dlna):
        """Seek to position 0."""
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")
        await mock_dlna.play("dev1", "video.mp4")
        mock_dlna.playback_state["dev1"]["duration"] = 3600

        await mock_dlna.seek("dev1", 0)
        position, _ = await mock_dlna.get_position("dev1")
        assert position == 0

    @pytest.mark.asyncio
    async def test_seek_to_exact_end(self, mock_dlna):
        """Seek to exact duration."""
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")
        await mock_dlna.play("dev1", "video.mp4")
        mock_dlna.playback_state["dev1"]["duration"] = 3600

        await mock_dlna.seek("dev1", 3600)
        position, duration = await mock_dlna.get_position("dev1")
        assert position <= duration

    @pytest.mark.asyncio
    async def test_seek_one_second_before_end(self, mock_dlna):
        """Seek to one second before end."""
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")
        await mock_dlna.play("dev1", "video.mp4")
        mock_dlna.playback_state["dev1"]["duration"] = 3600

        await mock_dlna.seek("dev1", 3599)
        position, _ = await mock_dlna.get_position("dev1")
        assert position == 3599


class TestPaginationEdgeCases:
    """Tests for pagination boundary conditions."""

    def test_pagination_page_zero(self, db_session):
        """Page 0 should be treated as page 1."""
        from src.database import crud
        from src.database.schemas import PlanCreate

        # Create some records
        for i in range(5):
            crud.create_plan(db_session, PlanCreate(
                title=f"Plan {i}",
                start_time="08:00",
                end_time="09:00",
                repeat_days="1,2,3",
                media_url=f"video{i}.mp4"
            ))

        # skip=0 should return first page
        plans = crud.get_plans(db_session, skip=0, limit=2)
        assert len(plans) == 2

    def test_pagination_beyond_total(self, db_session):
        """Skip beyond total should return empty."""
        from src.database import crud
        from src.database.schemas import PlanCreate

        for i in range(3):
            crud.create_plan(db_session, PlanCreate(
                title=f"Plan {i}",
                start_time="08:00",
                end_time="09:00",
                repeat_days="1,2,3",
                media_url=f"video{i}.mp4"
            ))

        plans = crud.get_plans(db_session, skip=100, limit=10)
        assert len(plans) == 0

    def test_pagination_limit_zero(self, db_session):
        """Limit 0 should return empty."""
        from src.database import crud

        plans = crud.get_plans(db_session, skip=0, limit=0)
        assert len(plans) == 0


class TestFileNameEdgeCases:
    """Tests for file name handling."""

    @pytest.mark.parametrize("filename", [
        "普通话视频.mp4",
        "日本語ファイル.mp4",
        "한국어파일.mp4",
        "файл на русском.mp4",
        "αρχείο ελληνικά.mp4",
    ])
    def test_unicode_filenames(self, mock_smb, filename):
        """Test handling of unicode filenames."""
        mock_smb.add_server("nas1", "NAS", "192.168.1.200")
        mock_smb.add_file("nas1", "media", filename)

        files = mock_smb.list_files("nas1", "media", "media")
        assert len(files) == 1
        assert files[0]["name"] == filename

    @pytest.mark.parametrize("filename", [
        "file with spaces.mp4",
        "file-with-dashes.mp4",
        "file_with_underscores.mp4",
        "file.multiple.dots.mp4",
        "UPPERCASE.MP4",
    ])
    def test_special_character_filenames(self, mock_smb, filename):
        """Test handling of special characters in filenames."""
        mock_smb.add_server("nas1", "NAS", "192.168.1.200")
        mock_smb.add_file("nas1", "media", filename)

        files = mock_smb.list_files("nas1", "media", "media")
        assert len(files) == 1


class TestTimeEdgeCases:
    """Tests for time-related edge cases."""

    @pytest.mark.parametrize("time_str,days", [
        ("00:00", "1,2,3,4,5,6,7"),  # Midnight
        ("23:59", "1"),              # End of day
        ("12:00", "7"),              # Noon Sunday
        ("06:30", "1,2,3,4,5"),      # Early morning weekdays
    ])
    def test_schedule_time_formats(self, mock_scheduler, time_str, days):
        """Test various valid time formats."""
        result = mock_scheduler.schedule_plan("plan1", time_str, days)
        assert result is True

        schedule = mock_scheduler.get_schedule("plan1")
        assert schedule is not None
        assert schedule["time"] == time_str

    @pytest.mark.parametrize("invalid_time", [
        "25:00",    # Invalid hour
        "12:60",    # Invalid minute
        "noon",     # Text
        "",         # Empty
        "12",       # Missing minute
    ])
    def test_invalid_time_formats(self, mock_scheduler, invalid_time):
        """Test invalid time formats are rejected."""
        result = mock_scheduler.schedule_plan("plan1", invalid_time, "1,2,3")
        assert result is False


class TestEmptyStateEdgeCases:
    """Tests for empty/initial state handling."""

    def test_get_plans_empty_database(self, db_session):
        """Getting plans from empty database."""
        from src.database import crud

        plans = crud.get_plans(db_session)
        assert plans == []
        assert len(plans) == 0

    def test_get_devices_empty_database(self, db_session):
        """Getting devices from empty database."""
        from src.database import crud

        devices = crud.get_devices(db_session)
        assert devices == []

    def test_get_history_empty_database(self, db_session):
        """Getting history from empty database."""
        from src.database import crud

        total, items = crud.get_playback_histories(db_session)
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_stop_without_playing(self, mock_dlna):
        """Stopping when nothing is playing."""
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")

        # Stop without starting - should be safe
        result = await mock_dlna.stop("dev1")
        assert result is False  # Nothing to stop

    @pytest.mark.asyncio
    async def test_pause_without_playing(self, mock_dlna):
        """Pausing when nothing is playing."""
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")

        result = await mock_dlna.pause("dev1")
        assert result is False


class TestConcurrencyEdgeCases:
    """Tests for concurrent operation edge cases."""

    @pytest.mark.asyncio
    async def test_rapid_play_stop_cycles(self, mock_dlna):
        """Test rapid play/stop cycles don't cause issues."""
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")

        for _ in range(10):
            await mock_dlna.play("dev1", "video.mp4")
            await mock_dlna.stop("dev1")

        # Should end in stopped state
        state = await mock_dlna.get_transport_state("dev1")
        assert state == "STOPPED"

    @pytest.mark.asyncio
    async def test_multiple_seek_operations(self, mock_dlna):
        """Test multiple rapid seek operations."""
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")
        await mock_dlna.play("dev1", "video.mp4")
        mock_dlna.playback_state["dev1"]["duration"] = 3600

        positions = [100, 500, 1000, 2000, 3000, 1500, 0]
        for pos in positions:
            await mock_dlna.seek("dev1", pos)

        # Should end at last seek position
        final_pos, _ = await mock_dlna.get_position("dev1")
        assert final_pos == 0


class TestDatabaseConstraintEdgeCases:
    """Tests for database constraint edge cases."""

    def test_create_duplicate_device_id(self, db_session):
        """Creating device with duplicate ID should be handled."""
        from src.database import crud

        device1 = crud.create_device(db_session, {
            "id": "same-id",
            "name": "First Device",
            "address": "192.168.1.1"
        })

        # Upsert with same ID should update
        device2 = crud.upsert_device(db_session, {
            "id": "same-id",
            "name": "Updated Device",
            "address": "192.168.1.2"
        })

        assert device2.name == "Updated Device"

        # Should still be only one device
        devices = crud.get_devices(db_session)
        assert len(devices) == 1

    def test_link_same_plan_task_twice(self, db_session):
        """Linking same plan and task twice should be idempotent."""
        from src.database import crud
        from src.database.schemas import PlanCreate, StudyTaskCreate

        plan = crud.create_plan(db_session, PlanCreate(
            title="Plan",
            start_time="08:00",
            end_time="09:00",
            repeat_days="1,2,3",
            media_url="video.mp4"
        ))
        task = crud.create_study_task(db_session, StudyTaskCreate(name="Task"))

        link1 = crud.link_plan_study_task(db_session, plan.id, task.id)
        link2 = crud.link_plan_study_task(db_session, plan.id, task.id)

        # Should return same link
        assert link1.id == link2.id

        # Should only have one link
        tasks = crud.get_plan_study_tasks(db_session, plan.id)
        assert len(tasks) == 1
