"""
Pytest configuration and shared fixtures for TrunPlay tests.
"""
import os
import sys
import pytest
from typing import Generator

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from tests.mocks import MockDLNAManager, MockSMBClient, MockScheduler
from tests.utils import LogCapture, Factory


# ==================== Database Fixtures ====================

@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    return engine


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Create a database session with tables initialized.

    Each test gets a fresh in-memory database.
    """
    from src.database.models import Base

    # Create all tables
    Base.metadata.create_all(db_engine)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()

    yield session

    session.close()


# ==================== Mock Fixtures ====================

@pytest.fixture
def mock_dlna() -> MockDLNAManager:
    """Create a MockDLNAManager instance."""
    mock = MockDLNAManager()
    yield mock
    mock.reset()


@pytest.fixture
def mock_smb() -> MockSMBClient:
    """Create a MockSMBClient instance."""
    mock = MockSMBClient()
    yield mock
    mock.reset()


@pytest.fixture
def mock_scheduler() -> MockScheduler:
    """Create a MockScheduler instance."""
    mock = MockScheduler()
    yield mock
    mock.reset()


# ==================== Log Capture Fixture ====================

@pytest.fixture
def log_capture(request) -> Generator[LogCapture, None, None]:
    """
    Capture logs during test execution.

    Automatically dumps logs on test failure.
    """
    capture = LogCapture()
    capture.start()

    yield capture

    capture.stop()

    # On test failure, print captured logs
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        print("\n" + "=" * 60)
        print("CAPTURED LOGS ON FAILURE:")
        print("=" * 60)
        print(capture.dump())
        print("=" * 60)


# ==================== API Client Fixture ====================

@pytest.fixture
def client(db_session, mock_dlna, mock_smb, mock_scheduler):
    """
    Create a FastAPI TestClient with all mocks injected.

    This fixture overrides the real service dependencies with mocks.
    """
    from fastapi.testclient import TestClient
    from src.main import app
    from src.database.models import SessionLocal

    # We need to override the database session and services
    # This depends on how the actual app is structured

    # For now, create a basic test client
    # TODO: Implement proper dependency injection when services support it

    with TestClient(app) as test_client:
        yield test_client


# ==================== Sample Data Fixtures ====================

@pytest.fixture
def sample_device(db_session):
    """Create a sample device for testing."""
    return Factory.device(db_session)


@pytest.fixture
def sample_plan(db_session):
    """Create a sample plan for testing."""
    return Factory.plan(db_session)


@pytest.fixture
def sample_smb_server(db_session):
    """Create a sample SMB server for testing."""
    return Factory.smb_server(db_session)


@pytest.fixture
def plan_with_device(db_session):
    """Create a plan with an associated device."""
    return Factory.plan_with_device(db_session)


@pytest.fixture
def complete_setup(db_session, mock_dlna, mock_smb):
    """Create a complete playback setup with all entities."""
    return Factory.complete_playback_setup(db_session, mock_dlna, mock_smb)


# ==================== Pytest Hooks ====================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test results and enable log dumping on failure.
    """
    outcome = yield
    report = outcome.get_result()

    # Store the result for access in fixtures
    setattr(item, f"rep_{report.when}", report)

    # On failure, add extra debug info
    if report.failed and call.when == "call":
        extra_sections = []

        # Add database state if available
        if hasattr(item, "funcargs") and "db_session" in item.funcargs:
            try:
                db_state = _dump_db_state(item.funcargs["db_session"])
                extra_sections.append(("Database State", db_state))
            except Exception as e:
                extra_sections.append(("Database State", f"Error dumping state: {e}"))

        # Add mock states if available
        if hasattr(item, "funcargs"):
            if "mock_dlna" in item.funcargs:
                mock = item.funcargs["mock_dlna"]
                extra_sections.append(("DLNA Mock State", str({
                    "devices": list(mock.devices.keys()),
                    "playback_state": mock.playback_state,
                    "fail_mode": mock.fail_mode,
                })))

            if "mock_smb" in item.funcargs:
                mock = item.funcargs["mock_smb"]
                extra_sections.append(("SMB Mock State", str({
                    "servers": list(mock.servers.keys()),
                    "connections": mock.connections,
                    "fail_mode": mock.fail_mode,
                })))

        for title, content in extra_sections:
            report.sections.append((title, content))


def _dump_db_state(session: Session) -> str:
    """Dump database state for debugging."""
    import json
    from src.database import models

    state = {}

    try:
        state["plans"] = session.query(models.Plan).count()
    except:
        state["plans"] = "N/A"

    try:
        state["devices"] = session.query(models.Device).count()
    except:
        state["devices"] = "N/A"

    try:
        state["smb_servers"] = session.query(models.SmbServer).count()
    except:
        state["smb_servers"] = "N/A"

    try:
        state["playback_history"] = session.query(models.PlaybackHistory).count()
    except:
        state["playback_history"] = "N/A"

    try:
        state["study_tasks"] = session.query(models.StudyTask).count()
    except:
        state["study_tasks"] = "N/A"

    return json.dumps(state, indent=2)


# ==================== Test Markers ====================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "scenario: marks tests as scenario/e2e tests"
    )
