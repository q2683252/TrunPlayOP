"""
Unit tests for database CRUD operations.
"""
import pytest
from src.database import crud
from src.database.schemas import (
    PlanCreate, PlanUpdate, PlayMode,
    SmbServerCreate, SmbServerUpdate,
    StudyTaskCreate, StudyTaskUpdate, StudyTaskMediaCreate,
    MediaSourceType, TriggerType, EndStatus
)


class TestPlanCRUD:
    """Tests for Plan CRUD operations."""

    def test_create_plan_generates_uuid(self, db_session):
        """Creating a plan should generate a UUID."""
        plan_data = PlanCreate(
            title="Test Plan",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3,4,5",
            media_url="smb://nas/video.mp4"
        )
        plan = crud.create_plan(db_session, plan_data)

        assert plan.id is not None
        assert len(plan.id) == 36  # UUID format
        assert plan.title == "Test Plan"

    def test_create_plan_with_all_fields(self, db_session):
        """Creating a plan with all optional fields."""
        plan_data = PlanCreate(
            title="Full Plan",
            start_time="08:00",
            end_time="18:00",
            repeat_days="1,2,3,4,5,6,7",
            skip_holidays=True,
            device_id="device-123",
            media_url="smb://nas/media/video.mp4",
            is_active=False,
            play_mode=PlayMode.LOOP
        )
        plan = crud.create_plan(db_session, plan_data)

        assert plan.skip_holidays == 1
        assert plan.is_active == 0
        assert plan.play_mode == "LOOP"
        assert plan.device_id == "device-123"

    def test_get_plan_existing(self, db_session):
        """Getting an existing plan by ID."""
        plan_data = PlanCreate(
            title="Get Test",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/video.mp4"
        )
        created = crud.create_plan(db_session, plan_data)
        retrieved = crud.get_plan(db_session, created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Get Test"

    def test_get_plan_nonexistent(self, db_session):
        """Getting a non-existent plan returns None."""
        result = crud.get_plan(db_session, "nonexistent-id")
        assert result is None

    def test_get_plans_empty(self, db_session):
        """Getting plans when none exist."""
        plans = crud.get_plans(db_session)
        assert plans == []

    def test_get_plans_with_pagination(self, db_session):
        """Getting plans with skip and limit."""
        # Create 5 plans
        for i in range(5):
            crud.create_plan(db_session, PlanCreate(
                title=f"Plan {i}",
                start_time="09:00",
                end_time="17:00",
                repeat_days="1,2,3",
                media_url=f"smb://nas/video{i}.mp4"
            ))

        # Test pagination
        page1 = crud.get_plans(db_session, skip=0, limit=2)
        assert len(page1) == 2

        page2 = crud.get_plans(db_session, skip=2, limit=2)
        assert len(page2) == 2

        page3 = crud.get_plans(db_session, skip=4, limit=2)
        assert len(page3) == 1

    def test_get_active_plans(self, db_session):
        """Getting only active plans."""
        crud.create_plan(db_session, PlanCreate(
            title="Active Plan",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/active.mp4",
            is_active=True
        ))
        crud.create_plan(db_session, PlanCreate(
            title="Inactive Plan",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/inactive.mp4",
            is_active=False
        ))

        active = crud.get_active_plans(db_session)
        assert len(active) == 1
        assert active[0].title == "Active Plan"

    def test_update_plan_partial_fields(self, db_session):
        """Updating only some fields should preserve others."""
        plan = crud.create_plan(db_session, PlanCreate(
            title="Original Title",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/video.mp4",
            is_active=True
        ))

        updated = crud.update_plan(db_session, plan.id, PlanUpdate(title="New Title"))

        assert updated.title == "New Title"
        assert updated.is_active == 1  # Preserved
        assert updated.start_time == "09:00"  # Preserved

    def test_update_plan_nonexistent(self, db_session):
        """Updating a non-existent plan returns None."""
        result = crud.update_plan(db_session, "nonexistent", PlanUpdate(title="New"))
        assert result is None

    def test_delete_plan_existing(self, db_session):
        """Deleting an existing plan."""
        plan = crud.create_plan(db_session, PlanCreate(
            title="To Delete",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/video.mp4"
        ))

        result = crud.delete_plan(db_session, plan.id)
        assert result is True

        # Verify deleted
        assert crud.get_plan(db_session, plan.id) is None

    def test_delete_plan_nonexistent(self, db_session):
        """Deleting a non-existent plan returns False."""
        result = crud.delete_plan(db_session, "nonexistent")
        assert result is False

    def test_update_plan_playback_progress(self, db_session):
        """Updating playback progress."""
        plan = crud.create_plan(db_session, PlanCreate(
            title="Progress Test",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/video.mp4"
        ))

        updated = crud.update_plan_playback_progress(
            db_session,
            plan.id,
            position=1800,
            media_uri="smb://nas/video.mp4",
            duration=3600
        )

        assert updated.last_playback_position == 1800
        assert updated.last_playback_media_uri == "smb://nas/video.mp4"
        assert updated.media_duration == 3600
        assert updated.last_playback_time > 0

    def test_reset_plan_progress(self, db_session):
        """Resetting plan progress."""
        plan = crud.create_plan(db_session, PlanCreate(
            title="Reset Test",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/video.mp4"
        ))

        # Set some progress
        crud.update_plan_playback_progress(db_session, plan.id, 1800, "uri", 3600)

        # Reset
        reset = crud.reset_plan_progress(db_session, plan.id)

        assert reset.last_playback_position == 0
        assert reset.last_playback_media_uri == ""
        assert reset.last_playback_time == 0


class TestDeviceCRUD:
    """Tests for Device CRUD operations."""

    def test_create_device(self, db_session):
        """Creating a device."""
        device_data = {
            "id": "device-001",
            "name": "Living Room TV",
            "address": "192.168.1.100",
            "type": "MediaRenderer",
            "manufacturer": "Samsung"
        }
        device = crud.create_device(db_session, device_data)

        assert device.id == "device-001"
        assert device.name == "Living Room TV"

    def test_get_device_existing(self, db_session):
        """Getting an existing device."""
        device_data = {
            "id": "device-002",
            "name": "Bedroom TV",
            "address": "192.168.1.101"
        }
        crud.create_device(db_session, device_data)
        retrieved = crud.get_device(db_session, "device-002")

        assert retrieved is not None
        assert retrieved.name == "Bedroom TV"

    def test_get_device_nonexistent(self, db_session):
        """Getting a non-existent device returns None."""
        result = crud.get_device(db_session, "nonexistent")
        assert result is None

    def test_get_devices_all(self, db_session):
        """Getting all devices."""
        crud.create_device(db_session, {"id": "d1", "name": "TV1", "address": "192.168.1.1"})
        crud.create_device(db_session, {"id": "d2", "name": "TV2", "address": "192.168.1.2"})

        devices = crud.get_devices(db_session)
        assert len(devices) == 2

    def test_update_device(self, db_session):
        """Updating a device."""
        crud.create_device(db_session, {"id": "d1", "name": "Old Name", "address": "192.168.1.1"})

        updated = crud.update_device(db_session, "d1", {"name": "New Name"})

        assert updated.name == "New Name"
        assert updated.address == "192.168.1.1"  # Preserved

    def test_upsert_device_insert(self, db_session):
        """Upserting a new device inserts it."""
        device_data = {"id": "new-device", "name": "New TV", "address": "192.168.1.50"}
        device = crud.upsert_device(db_session, device_data)

        assert device.id == "new-device"
        assert device.name == "New TV"

    def test_upsert_device_update(self, db_session):
        """Upserting an existing device updates it."""
        crud.create_device(db_session, {"id": "existing", "name": "Old", "address": "192.168.1.1"})

        updated = crud.upsert_device(db_session, {"id": "existing", "name": "Updated", "address": "192.168.1.2"})

        assert updated.name == "Updated"
        assert updated.address == "192.168.1.2"

        # Should still be only one device
        devices = crud.get_devices(db_session)
        assert len(devices) == 1

    def test_delete_device_existing(self, db_session):
        """Deleting an existing device."""
        crud.create_device(db_session, {"id": "to-delete", "name": "Delete Me", "address": "192.168.1.1"})

        result = crud.delete_device(db_session, "to-delete")
        assert result is True
        assert crud.get_device(db_session, "to-delete") is None

    def test_delete_device_nonexistent(self, db_session):
        """Deleting a non-existent device returns False."""
        result = crud.delete_device(db_session, "nonexistent")
        assert result is False


class TestSmbServerCRUD:
    """Tests for SmbServer CRUD operations."""

    def test_create_smb_server(self, db_session):
        """Creating an SMB server."""
        server_data = SmbServerCreate(
            name="NAS",
            host="192.168.1.200",
            port=445,
            username="admin",
            password="secret",
            share_path="/media"
        )
        server = crud.create_smb_server(db_session, server_data)

        assert server.id is not None
        assert server.name == "NAS"
        assert server.host == "192.168.1.200"

    def test_get_smb_server(self, db_session):
        """Getting an SMB server by ID."""
        server_data = SmbServerCreate(
            name="Test NAS",
            host="192.168.1.201"
        )
        created = crud.create_smb_server(db_session, server_data)
        retrieved = crud.get_smb_server(db_session, created.id)

        assert retrieved is not None
        assert retrieved.name == "Test NAS"

    def test_get_smb_servers(self, db_session):
        """Getting all SMB servers."""
        crud.create_smb_server(db_session, SmbServerCreate(name="NAS1", host="192.168.1.1"))
        crud.create_smb_server(db_session, SmbServerCreate(name="NAS2", host="192.168.1.2"))

        servers = crud.get_smb_servers(db_session)
        assert len(servers) == 2

    def test_update_smb_server(self, db_session):
        """Updating an SMB server."""
        server = crud.create_smb_server(db_session, SmbServerCreate(
            name="Original",
            host="192.168.1.1",
            username="old_user"
        ))

        updated = crud.update_smb_server(db_session, server.id, SmbServerUpdate(
            name="Updated",
            username="new_user"
        ))

        assert updated.name == "Updated"
        assert updated.username == "new_user"
        assert updated.host == "192.168.1.1"  # Preserved

    def test_delete_smb_server(self, db_session):
        """Deleting an SMB server."""
        server = crud.create_smb_server(db_session, SmbServerCreate(name="Delete", host="192.168.1.1"))

        result = crud.delete_smb_server(db_session, server.id)
        assert result is True
        assert crud.get_smb_server(db_session, server.id) is None

    def test_update_smb_server_connection(self, db_session):
        """Updating SMB server connection status."""
        server = crud.create_smb_server(db_session, SmbServerCreate(name="Test", host="192.168.1.1"))

        # Set connected
        updated = crud.update_smb_server_connection(db_session, server.id, True)
        assert updated.is_connected == 1
        assert updated.last_connected_at > 0

        # Set disconnected
        updated = crud.update_smb_server_connection(db_session, server.id, False)
        assert updated.is_connected == 0


class TestPlaybackHistoryCRUD:
    """Tests for PlaybackHistory CRUD operations."""

    def _create_plan_and_device(self, db_session):
        """Helper to create a plan and device for history tests."""
        plan = crud.create_plan(db_session, PlanCreate(
            title="Test Plan",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/video.mp4"
        ))
        device_data = {"id": "dev1", "name": "Test TV", "address": "192.168.1.100"}
        device = crud.create_device(db_session, device_data)
        return plan, device

    def test_create_playback_history(self, db_session):
        """Creating a playback history record."""
        plan, device = self._create_plan_and_device(db_session)

        history = crud.create_playback_history(
            db_session,
            plan=plan,
            device=device,
            media_url="smb://nas/video.mp4",
            media_name="video.mp4",
            trigger_type=TriggerType.MANUAL
        )

        assert history.id is not None
        assert history.plan_id == plan.id
        assert history.device_id == device.id
        assert history.trigger_type == "MANUAL"

    def test_get_playback_history(self, db_session):
        """Getting a playback history record by ID."""
        plan, device = self._create_plan_and_device(db_session)
        created = crud.create_playback_history(
            db_session, plan, device, "url", "name"
        )

        retrieved = crud.get_playback_history(db_session, created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_playback_histories_pagination(self, db_session):
        """Getting playback histories with pagination."""
        plan, device = self._create_plan_and_device(db_session)

        # Create multiple records
        for i in range(10):
            crud.create_playback_history(
                db_session, plan, device, f"url{i}", f"name{i}"
            )

        total, items = crud.get_playback_histories(db_session, skip=0, limit=5)
        assert total == 10
        assert len(items) == 5

    def test_get_playback_histories_filter_by_plan(self, db_session):
        """Filtering playback histories by plan ID."""
        plan1, device = self._create_plan_and_device(db_session)
        plan2 = crud.create_plan(db_session, PlanCreate(
            title="Plan 2",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/video2.mp4"
        ))

        crud.create_playback_history(db_session, plan1, device, "url1", "name1")
        crud.create_playback_history(db_session, plan1, device, "url2", "name2")
        crud.create_playback_history(db_session, plan2, device, "url3", "name3")

        total, items = crud.get_playback_histories(db_session, plan_id=plan1.id)
        assert total == 2

    def test_update_playback_history_progress(self, db_session):
        """Updating playback progress in history."""
        plan, device = self._create_plan_and_device(db_session)
        history = crud.create_playback_history(db_session, plan, device, "url", "name")

        updated = crud.update_playback_history_progress(
            db_session, history.id, played_duration=1800, played_position=1800
        )

        assert updated.played_duration == 1800
        assert updated.played_position == 1800

    def test_end_playback_history_completed(self, db_session):
        """Ending playback history with completed status."""
        plan, device = self._create_plan_and_device(db_session)
        history = crud.create_playback_history(db_session, plan, device, "url", "name")

        ended = crud.end_playback_history(
            db_session, history.id,
            played_duration=3600,
            played_position=3600,
            completed=True
        )

        assert ended.end_status == "COMPLETED"
        assert ended.actual_end_time > 0

    def test_end_playback_history_error(self, db_session):
        """Ending playback history with error status."""
        plan, device = self._create_plan_and_device(db_session)
        history = crud.create_playback_history(db_session, plan, device, "url", "name")

        ended = crud.end_playback_history(
            db_session, history.id,
            played_duration=1000,
            played_position=1000,
            error_code="DEVICE_OFFLINE",
            error_message="Device disconnected"
        )

        assert ended.end_status == "ERROR"
        assert ended.error_code == "DEVICE_OFFLINE"

    def test_delete_playback_history(self, db_session):
        """Deleting a playback history record."""
        plan, device = self._create_plan_and_device(db_session)
        history = crud.create_playback_history(db_session, plan, device, "url", "name")

        result = crud.delete_playback_history(db_session, history.id)
        assert result is True
        assert crud.get_playback_history(db_session, history.id) is None

    def test_clear_playback_history(self, db_session):
        """Clearing all playback history."""
        plan, device = self._create_plan_and_device(db_session)

        for i in range(5):
            crud.create_playback_history(db_session, plan, device, f"url{i}", f"name{i}")

        count = crud.clear_playback_history(db_session)
        assert count == 5

        total, items = crud.get_playback_histories(db_session)
        assert total == 0


class TestStudyTaskCRUD:
    """Tests for StudyTask CRUD operations."""

    def test_create_study_task_empty(self, db_session):
        """Creating a study task without media items."""
        task_data = StudyTaskCreate(name="Empty Task")
        task = crud.create_study_task(db_session, task_data)

        assert task.id is not None
        assert task.name == "Empty Task"
        assert task.total_duration == 0

    def test_create_study_task_with_media(self, db_session):
        """Creating a study task with media items."""
        task_data = StudyTaskCreate(
            name="Study Task",
            media_items=[
                StudyTaskMediaCreate(media_uri="uri1", media_name="Video 1", duration=1800),
                StudyTaskMediaCreate(media_uri="uri2", media_name="Video 2", duration=2400),
            ]
        )
        task = crud.create_study_task(db_session, task_data)

        assert task.total_duration == 4200  # 1800 + 2400
        assert len(task.media_items) == 2

    def test_get_study_task(self, db_session):
        """Getting a study task by ID."""
        created = crud.create_study_task(db_session, StudyTaskCreate(name="Test"))
        retrieved = crud.get_study_task(db_session, created.id)

        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_get_study_tasks(self, db_session):
        """Getting all study tasks."""
        crud.create_study_task(db_session, StudyTaskCreate(name="Task 1"))
        crud.create_study_task(db_session, StudyTaskCreate(name="Task 2"))

        tasks = crud.get_study_tasks(db_session)
        assert len(tasks) == 2

    def test_update_study_task(self, db_session):
        """Updating a study task."""
        task = crud.create_study_task(db_session, StudyTaskCreate(name="Original"))

        updated = crud.update_study_task(db_session, task.id, StudyTaskUpdate(name="Updated"))

        assert updated.name == "Updated"

    def test_delete_study_task(self, db_session):
        """Deleting a study task."""
        task = crud.create_study_task(db_session, StudyTaskCreate(name="Delete"))

        result = crud.delete_study_task(db_session, task.id)
        assert result is True
        assert crud.get_study_task(db_session, task.id) is None

    def test_reset_study_task_progress(self, db_session):
        """Resetting study task progress."""
        task = crud.create_study_task(db_session, StudyTaskCreate(name="Reset Test"))
        crud.add_watched_duration(db_session, task.id, 1000)

        reset = crud.reset_study_task_progress(db_session, task.id)
        assert reset.watched_duration == 0

    def test_add_study_task_media(self, db_session):
        """Adding media to a study task."""
        task = crud.create_study_task(db_session, StudyTaskCreate(name="Test"))

        media = crud.add_study_task_media(db_session, task.id, StudyTaskMediaCreate(
            media_uri="new_uri",
            media_name="New Video",
            duration=3600
        ))

        assert media is not None
        assert media.media_name == "New Video"

        # Check total duration updated
        updated_task = crud.get_study_task(db_session, task.id)
        assert updated_task.total_duration == 3600

    def test_remove_study_task_media(self, db_session):
        """Removing media from a study task."""
        task = crud.create_study_task(db_session, StudyTaskCreate(
            name="Test",
            media_items=[StudyTaskMediaCreate(media_uri="uri", media_name="Video", duration=1800)]
        ))
        media_id = task.media_items[0].id

        result = crud.remove_study_task_media(db_session, task.id, media_id)
        assert result is True

        updated_task = crud.get_study_task(db_session, task.id)
        assert updated_task.total_duration == 0
        assert len(updated_task.media_items) == 0

    def test_add_watched_duration(self, db_session):
        """Adding watched duration to a study task."""
        task = crud.create_study_task(db_session, StudyTaskCreate(name="Watch Test"))

        crud.add_watched_duration(db_session, task.id, 500)
        crud.add_watched_duration(db_session, task.id, 300)

        updated = crud.get_study_task(db_session, task.id)
        assert updated.watched_duration == 800


class TestPlanStudyTaskLinkCRUD:
    """Tests for Plan-StudyTask link operations."""

    def _create_plan_and_task(self, db_session):
        """Helper to create a plan and study task."""
        plan = crud.create_plan(db_session, PlanCreate(
            title="Test Plan",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/video.mp4"
        ))
        task = crud.create_study_task(db_session, StudyTaskCreate(name="Test Task"))
        return plan, task

    def test_link_plan_study_task(self, db_session):
        """Linking a plan to a study task."""
        plan, task = self._create_plan_and_task(db_session)

        link = crud.link_plan_study_task(db_session, plan.id, task.id)

        assert link is not None
        assert link.plan_id == plan.id
        assert link.study_task_id == task.id

    def test_link_plan_study_task_idempotent(self, db_session):
        """Linking the same plan and task twice should be idempotent."""
        plan, task = self._create_plan_and_task(db_session)

        link1 = crud.link_plan_study_task(db_session, plan.id, task.id)
        link2 = crud.link_plan_study_task(db_session, plan.id, task.id)

        assert link1.id == link2.id  # Same link returned

    def test_unlink_plan_study_task(self, db_session):
        """Unlinking a plan from a study task."""
        plan, task = self._create_plan_and_task(db_session)
        crud.link_plan_study_task(db_session, plan.id, task.id)

        result = crud.unlink_plan_study_task(db_session, plan.id, task.id)
        assert result is True

        tasks = crud.get_plan_study_tasks(db_session, plan.id)
        assert len(tasks) == 0

    def test_unlink_nonexistent(self, db_session):
        """Unlinking a non-existent link returns False."""
        result = crud.unlink_plan_study_task(db_session, "nonexistent", "nonexistent")
        assert result is False

    def test_get_plan_study_tasks(self, db_session):
        """Getting study tasks linked to a plan."""
        plan = crud.create_plan(db_session, PlanCreate(
            title="Test Plan",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/video.mp4"
        ))
        task1 = crud.create_study_task(db_session, StudyTaskCreate(name="Task 1"))
        task2 = crud.create_study_task(db_session, StudyTaskCreate(name="Task 2"))

        crud.link_plan_study_task(db_session, plan.id, task1.id, sort_order=1)
        crud.link_plan_study_task(db_session, plan.id, task2.id, sort_order=0)

        tasks = crud.get_plan_study_tasks(db_session, plan.id)
        assert len(tasks) == 2
        # Should be ordered by sort_order
        assert tasks[0].name == "Task 2"
        assert tasks[1].name == "Task 1"

    def test_get_plan_media_playlist(self, db_session):
        """Getting flattened media playlist for a plan."""
        plan = crud.create_plan(db_session, PlanCreate(
            title="Test Plan",
            start_time="09:00",
            end_time="17:00",
            repeat_days="1,2,3",
            media_url="smb://nas/video.mp4"
        ))
        task = crud.create_study_task(db_session, StudyTaskCreate(
            name="Task",
            media_items=[
                StudyTaskMediaCreate(media_uri="uri1", media_name="Video 1", duration=1800),
                StudyTaskMediaCreate(media_uri="uri2", media_name="Video 2", duration=2400),
            ]
        ))
        crud.link_plan_study_task(db_session, plan.id, task.id)

        playlist = crud.get_plan_media_playlist(db_session, plan.id)
        assert len(playlist) == 2
        assert playlist[0].media_name == "Video 1"
        assert playlist[1].media_name == "Video 2"
