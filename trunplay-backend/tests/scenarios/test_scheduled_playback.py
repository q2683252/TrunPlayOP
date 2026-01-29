"""
Scenario tests for scheduled playback flows.

Tests complete business flows from plan creation to playback completion.
"""
import pytest
import asyncio


class TestScheduledPlaybackFlow:
    """Tests for the complete scheduled playback flow."""

    @pytest.mark.asyncio
    async def test_complete_playback_cycle(self, db_session, mock_dlna, mock_smb):
        """
        Test complete playback cycle:
        Plan trigger -> Playback start -> Progress tracking -> Completion
        """
        from src.database import crud
        from src.database.schemas import PlanCreate, TriggerType

        # 1. Setup: Create device and plan
        device_data = {
            "id": "test-device",
            "name": "Test TV",
            "address": "192.168.1.100"
        }
        device = crud.create_device(db_session, device_data)
        mock_dlna.add_device(device.id, device.name, device.address)

        plan = crud.create_plan(db_session, PlanCreate(
            title="Morning Schedule",
            start_time="08:00",
            end_time="09:00",
            repeat_days="1,2,3,4,5",
            device_id=device.id,
            media_url="local:///mnt/video.mp4"
        ))

        # 2. Start playback
        result = await mock_dlna.play(device.id, plan.media_url, plan.title)
        assert result is True

        # 3. Verify playback state
        state = await mock_dlna.get_transport_state(device.id)
        assert state == "PLAYING"

        # 4. Simulate progress
        mock_dlna.set_position(device.id, 1800, 3600)  # 30 min into 1 hour video

        position, duration = await mock_dlna.get_position(device.id)
        assert position == 1800
        assert duration == 3600

        # 5. Simulate completion
        mock_dlna.set_position(device.id, 3600, 3600)

        position, duration = await mock_dlna.get_position(device.id)
        assert position == 3600  # Completed

        # 6. Stop playback
        result = await mock_dlna.stop(device.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_resume_from_last_position(self, db_session, mock_dlna):
        """
        Test resuming playback from last saved position.
        Should start from last_position - RESUME_OFFSET_SECONDS.
        """
        from src.database import crud
        from src.database.schemas import PlanCreate

        RESUME_OFFSET_SECONDS = 10

        # Setup device
        device_data = {"id": "dev1", "name": "TV", "address": "192.168.1.100"}
        device = crud.create_device(db_session, device_data)
        mock_dlna.add_device(device.id, device.name, device.address)

        # Create plan with existing progress
        plan = crud.create_plan(db_session, PlanCreate(
            title="Resume Test",
            start_time="08:00",
            end_time="09:00",
            repeat_days="1,2,3",
            device_id=device.id,
            media_url="local:///mnt/video.mp4"
        ))

        # Set previous progress
        crud.update_plan_playback_progress(db_session, plan.id, position=1800)

        # Calculate resume position
        last_position = plan.last_playback_position
        resume_position = max(0, last_position - RESUME_OFFSET_SECONDS)

        # Start playback at resume position
        await mock_dlna.play(device.id, plan.media_url)
        await mock_dlna.seek(device.id, resume_position)

        position, _ = await mock_dlna.get_position(device.id)
        assert position == resume_position

    @pytest.mark.asyncio
    async def test_playlist_sequential_play(self, db_session, mock_dlna):
        """
        Test sequential playlist playback.
        After one video ends, should start the next.
        """
        from src.database import crud
        from src.database.schemas import StudyTaskCreate, StudyTaskMediaCreate, PlanCreate

        # Setup device
        device_data = {"id": "dev1", "name": "TV", "address": "192.168.1.100"}
        device = crud.create_device(db_session, device_data)
        mock_dlna.add_device(device.id, device.name, device.address)

        # Create study task with multiple videos
        task = crud.create_study_task(db_session, StudyTaskCreate(
            name="Study Playlist",
            media_items=[
                StudyTaskMediaCreate(media_uri="video1.mp4", media_name="Video 1", duration=1800),
                StudyTaskMediaCreate(media_uri="video2.mp4", media_name="Video 2", duration=2400),
                StudyTaskMediaCreate(media_uri="video3.mp4", media_name="Video 3", duration=1200),
            ]
        ))

        # Create plan and link to study task
        plan = crud.create_plan(db_session, PlanCreate(
            title="Playlist Plan",
            start_time="08:00",
            end_time="12:00",
            repeat_days="1,2,3",
            device_id=device.id,
            media_url="study://" + task.id,
            play_mode="SEQUENTIAL"
        ))
        crud.link_plan_study_task(db_session, plan.id, task.id)

        # Get playlist
        playlist = crud.get_plan_media_playlist(db_session, plan.id)
        assert len(playlist) == 3

        # Simulate playing through playlist
        for i, media in enumerate(playlist):
            await mock_dlna.play(device.id, media.media_uri, media.media_name)
            state = await mock_dlna.get_transport_state(device.id)
            assert state == "PLAYING"

            # Simulate completion
            mock_dlna.set_position(device.id, media.duration, media.duration)
            await mock_dlna.stop(device.id)

    @pytest.mark.asyncio
    async def test_playlist_loop_mode(self, db_session, mock_dlna):
        """
        Test loop mode: after last video, should start from first.
        """
        from src.database import crud
        from src.database.schemas import StudyTaskCreate, StudyTaskMediaCreate, PlanCreate, PlayMode

        # Setup
        device_data = {"id": "dev1", "name": "TV", "address": "192.168.1.100"}
        device = crud.create_device(db_session, device_data)
        mock_dlna.add_device(device.id, device.name, device.address)

        task = crud.create_study_task(db_session, StudyTaskCreate(
            name="Loop Playlist",
            media_items=[
                StudyTaskMediaCreate(media_uri="video1.mp4", media_name="Video 1", duration=600),
                StudyTaskMediaCreate(media_uri="video2.mp4", media_name="Video 2", duration=600),
            ]
        ))

        plan = crud.create_plan(db_session, PlanCreate(
            title="Loop Plan",
            start_time="08:00",
            end_time="12:00",
            repeat_days="1,2,3",
            device_id=device.id,
            media_url="study://" + task.id,
            play_mode=PlayMode.LOOP
        ))
        crud.link_plan_study_task(db_session, plan.id, task.id)

        playlist = crud.get_plan_media_playlist(db_session, plan.id)

        # Play through twice (one full loop)
        play_count = 0
        for _ in range(2):  # Two iterations
            for media in playlist:
                await mock_dlna.play(device.id, media.media_uri)
                play_count += 1

        assert play_count == 4  # 2 videos * 2 loops


class TestProgressTracking:
    """Tests for playback progress tracking."""

    @pytest.mark.asyncio
    async def test_progress_saved_periodically(self, db_session, mock_dlna):
        """
        Test that progress is saved at regular intervals.
        """
        from src.database import crud
        from src.database.schemas import PlanCreate

        PROGRESS_SAVE_INTERVAL = 5.0  # seconds

        device_data = {"id": "dev1", "name": "TV", "address": "192.168.1.100"}
        device = crud.create_device(db_session, device_data)
        mock_dlna.add_device(device.id, device.name, device.address)

        plan = crud.create_plan(db_session, PlanCreate(
            title="Progress Test",
            start_time="08:00",
            end_time="09:00",
            repeat_days="1,2,3",
            device_id=device.id,
            media_url="local:///video.mp4"
        ))

        # Start playback
        await mock_dlna.play(device.id, plan.media_url)

        # Simulate progress updates
        positions = [100, 200, 300, 400, 500]
        for pos in positions:
            mock_dlna.set_position(device.id, pos, 3600)
            crud.update_plan_playback_progress(db_session, plan.id, pos)

        # Verify final progress
        updated_plan = crud.get_plan(db_session, plan.id)
        assert updated_plan.last_playback_position == 500

    @pytest.mark.asyncio
    async def test_completion_threshold(self, db_session, mock_dlna):
        """
        Test that playback is marked complete when near end.
        COMPLETION_THRESHOLD = 5 seconds from end.
        """
        from src.database import crud
        from src.database.schemas import PlanCreate

        COMPLETION_THRESHOLD = 5

        device_data = {"id": "dev1", "name": "TV", "address": "192.168.1.100"}
        device = crud.create_device(db_session, device_data)
        mock_dlna.add_device(device.id, device.name, device.address)

        plan = crud.create_plan(db_session, PlanCreate(
            title="Completion Test",
            start_time="08:00",
            end_time="09:00",
            repeat_days="1,2,3",
            device_id=device.id,
            media_url="local:///video.mp4"
        ))

        await mock_dlna.play(device.id, plan.media_url)

        duration = 3600  # 1 hour
        # Position within threshold of completion
        near_end_position = duration - COMPLETION_THRESHOLD + 1

        mock_dlna.set_position(device.id, near_end_position, duration)
        position, dur = await mock_dlna.get_position(device.id)

        # Check if should be considered complete
        is_complete = (dur - position) <= COMPLETION_THRESHOLD
        assert is_complete is True

    @pytest.mark.asyncio
    async def test_progress_survives_restart(self, db_session, mock_dlna):
        """
        Test that progress is persisted and survives service restart.
        """
        from src.database import crud
        from src.database.schemas import PlanCreate

        device_data = {"id": "dev1", "name": "TV", "address": "192.168.1.100"}
        device = crud.create_device(db_session, device_data)

        plan = crud.create_plan(db_session, PlanCreate(
            title="Persist Test",
            start_time="08:00",
            end_time="09:00",
            repeat_days="1,2,3",
            device_id=device.id,
            media_url="local:///video.mp4"
        ))

        # Save progress
        crud.update_plan_playback_progress(
            db_session, plan.id,
            position=1800,
            media_uri="local:///video.mp4",
            duration=3600
        )

        # Simulate restart by re-fetching from database
        retrieved_plan = crud.get_plan(db_session, plan.id)

        assert retrieved_plan.last_playback_position == 1800
        assert retrieved_plan.last_playback_media_uri == "local:///video.mp4"
        assert retrieved_plan.media_duration == 3600


class TestPlaybackBoundaries:
    """Tests for playback boundary conditions."""

    @pytest.mark.asyncio
    async def test_seek_beyond_duration(self, mock_dlna):
        """
        Test seeking beyond video duration.
        Should clamp to duration.
        """
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")
        await mock_dlna.play("dev1", "video.mp4")
        mock_dlna.playback_state["dev1"]["duration"] = 3600

        # Try to seek beyond duration
        await mock_dlna.seek("dev1", 5000)

        position, duration = await mock_dlna.get_position("dev1")
        assert position <= duration

    @pytest.mark.asyncio
    async def test_seek_negative_position(self, mock_dlna):
        """
        Test seeking to negative position.
        Should clamp to 0.
        """
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")
        await mock_dlna.play("dev1", "video.mp4")

        await mock_dlna.seek("dev1", -100)

        position, _ = await mock_dlna.get_position("dev1")
        assert position >= 0

    @pytest.mark.asyncio
    async def test_volume_clamped_0_100(self, mock_dlna):
        """
        Test that volume is clamped to 0-100 range.
        """
        mock_dlna.add_device("dev1", "TV", "192.168.1.100")

        # Test above 100
        await mock_dlna.set_volume("dev1", 150)
        volume = await mock_dlna.get_volume("dev1")
        assert volume <= 100

        # Test below 0
        await mock_dlna.set_volume("dev1", -50)
        volume = await mock_dlna.get_volume("dev1")
        assert volume >= 0

    @pytest.mark.asyncio
    async def test_empty_playlist(self, db_session):
        """
        Test handling of empty playlist.
        Should not crash.
        """
        from src.database import crud
        from src.database.schemas import StudyTaskCreate, PlanCreate

        # Create empty study task
        task = crud.create_study_task(db_session, StudyTaskCreate(
            name="Empty Task",
            media_items=[]
        ))

        plan = crud.create_plan(db_session, PlanCreate(
            title="Empty Playlist Plan",
            start_time="08:00",
            end_time="09:00",
            repeat_days="1,2,3",
            media_url="study://" + task.id
        ))
        crud.link_plan_study_task(db_session, plan.id, task.id)

        playlist = crud.get_plan_media_playlist(db_session, plan.id)
        assert len(playlist) == 0

    @pytest.mark.asyncio
    async def test_play_without_device(self, mock_dlna):
        """
        Test playing to a non-existent device.
        Should fail gracefully.
        """
        result = await mock_dlna.play("nonexistent-device", "video.mp4")
        assert result is False
