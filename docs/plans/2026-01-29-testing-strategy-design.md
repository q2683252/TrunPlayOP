# TrunPlay 测试方案设计

## 概述

本文档定义 TrunPlay 项目的完整测试方案，包括自动化测试、人工测试、日志分析和闭环机制。

**设计目标**：
- 覆盖核心播放流程和所有边缘场景
- 纯 Mock 模拟外部依赖，本地开发机可运行
- 结构化日志便于问题定位
- 测试失败能快速闭环

---

## 一、测试目录结构

```
trunplay-backend/
├── tests/
│   ├── conftest.py              # pytest fixtures 和全局配置
│   ├── pytest.ini               # pytest 配置
│   │
│   ├── unit/                    # 单元测试（纯逻辑，无外部依赖）
│   │   ├── test_crud.py         # 数据库 CRUD 操作
│   │   ├── test_schemas.py      # Pydantic 模型验证
│   │   └── test_utils.py        # 工具函数
│   │
│   ├── integration/             # 集成测试（API + Mock 服务）
│   │   ├── test_api_plans.py
│   │   ├── test_api_devices.py
│   │   ├── test_api_playback.py
│   │   └── ...
│   │
│   ├── scenarios/               # 场景测试（完整业务流程）
│   │   ├── test_scheduled_playback.py
│   │   ├── test_error_recovery.py
│   │   └── test_edge_cases.py
│   │
│   ├── regression/              # 回归测试（Bug 转化的用例）
│   │
│   ├── mocks/                   # Mock 实现
│   │   ├── mock_dlna.py
│   │   ├── mock_smb.py
│   │   └── mock_scheduler.py
│   │
│   ├── utils/                   # 测试工具
│   │   ├── log_capture.py       # 日志捕获和断言
│   │   ├── fixtures.py          # 测试数据工厂
│   │   └── coverage_analyzer.py # 覆盖率分析
│   │
│   ├── manual/                  # 人工测试
│   │   ├── exploratory_checklist.md
│   │   ├── acceptance_checklist.md
│   │   └── reproduce_helper.py
│   │
│   └── README.md                # 测试运行指南
```

**框架选型**：pytest + pytest-asyncio + pytest-cov

---

## 二、Mock 体系设计

为每个外部依赖创建可控的 Mock 实现，支持模拟正常响应和错误场景。

### 2.1 MockDLNAManager

```python
# tests/mocks/mock_dlna.py
class MockDLNAManager:
    def __init__(self):
        self.devices = {}           # 模拟设备列表
        self.playback_state = {}    # 模拟播放状态
        self.fail_mode = None       # 注入错误: "offline", "timeout", "soap_error"

    async def discover_devices(self, timeout=5.0):
        if self.fail_mode == "timeout":
            raise asyncio.TimeoutError()
        return list(self.devices.values())

    async def play(self, device_id, url):
        if self.fail_mode == "offline":
            return False
        self.playback_state[device_id] = {"state": "PLAYING", "url": url}
        return True

    async def pause(self, device_id):
        if device_id in self.playback_state:
            self.playback_state[device_id]["state"] = "PAUSED"
            return True
        return False

    async def stop(self, device_id):
        if device_id in self.playback_state:
            del self.playback_state[device_id]
            return True
        return False

    async def get_position(self, device_id):
        state = self.playback_state.get(device_id, {})
        return state.get("position", 0), state.get("duration", 0)

    async def seek(self, device_id, position):
        if device_id in self.playback_state:
            self.playback_state[device_id]["position"] = position
            return True
        return False

    # 测试辅助方法
    def add_device(self, device_id, name, address):
        self.devices[device_id] = {"id": device_id, "name": name, "address": address}

    def set_position(self, device_id, position, duration):
        if device_id in self.playback_state:
            self.playback_state[device_id].update({"position": position, "duration": duration})
```

### 2.2 MockSMBClient

```python
# tests/mocks/mock_smb.py
class MockSMBClient:
    def __init__(self):
        self.servers = {}           # server_id -> config
        self.file_tree = {}         # server_id -> {path: [files]}
        self.fail_mode = None       # "auth_error", "connection_error", "not_found"

    def connect(self, server_id):
        if self.fail_mode == "auth_error":
            raise AuthenticationError("Invalid credentials")
        if self.fail_mode == "connection_error":
            raise ConnectionError("Cannot connect to server")
        return True

    def list_shares(self, server_id):
        if self.fail_mode:
            return []
        return self.servers.get(server_id, {}).get("shares", [])

    def list_files(self, server_id, path):
        if self.fail_mode == "not_found":
            return []
        tree = self.file_tree.get(server_id, {})
        return tree.get(path, [])

    def get_file_stream(self, server_id, path):
        if self.fail_mode:
            return None
        return io.BytesIO(b"mock file content")

    # 测试辅助方法
    def add_server(self, server_id, config):
        self.servers[server_id] = config

    def add_files(self, server_id, path, files):
        if server_id not in self.file_tree:
            self.file_tree[server_id] = {}
        self.file_tree[server_id][path] = files
```

### 2.3 MockScheduler

```python
# tests/mocks/mock_scheduler.py
class MockScheduler:
    def __init__(self):
        self.scheduled_jobs = {}    # plan_id -> cron_expression
        self.fail_mode = None

    def schedule_plan(self, plan_id, time_str, days):
        if self.fail_mode:
            return False
        cron_expr = self._build_cron(time_str, days)
        self.scheduled_jobs[plan_id] = cron_expr
        return True

    def cancel_plan(self, plan_id):
        if plan_id in self.scheduled_jobs:
            del self.scheduled_jobs[plan_id]
            return True
        return False

    def is_scheduled(self, plan_id):
        return plan_id in self.scheduled_jobs

    def _build_cron(self, time_str, days):
        hour, minute = time_str.split(":")
        return f"{minute} {hour} * * {days}"
```

### 2.4 错误注入机制

每个 Mock 支持 `fail_mode` 属性动态切换：

| fail_mode | 说明 |
|-----------|------|
| `None` | 正常工作 |
| `"timeout"` | 操作超时 |
| `"connection_error"` | 连接失败 |
| `"auth_error"` | 认证失败 |
| `"not_found"` | 资源不存在 |
| `"offline"` | 设备离线 |
| `"soap_error"` | SOAP 协议错误 |

---

## 三、结构化日志系统

### 3.1 日志格式化器

```python
# src/utils/logging.py
import json
import logging
from datetime import datetime
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default=None)

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "context": getattr(record, "context", {}),
            "trace_id": trace_id_var.get(),
            "file": record.filename,
            "line": record.lineno
        }, ensure_ascii=False)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    return logger
```

### 3.2 业务上下文注入

```python
# 在 playback_service.py 中使用
logger.info("Playback started", extra={
    "context": {
        "plan_id": plan.id,
        "device_id": device.id,
        "media_url": url,
        "trigger": "manual"  # or "scheduled"
    }
})

logger.info("Playback completed", extra={
    "context": {
        "plan_id": plan.id,
        "duration": duration,
        "position": position
    }
})

logger.error("Playback failed", extra={
    "context": {
        "plan_id": plan.id,
        "error": str(e),
        "stage": "device_connect"
    }
})
```

### 3.3 Trace ID 中间件

```python
# src/api/middleware.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        trace_id_var.set(trace_id)
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response
```

### 3.4 日志级别规范

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| DEBUG | 详细调试信息 | SOAP 请求内容、文件列表详情 |
| INFO | 状态变更 | 播放开始/停止/完成、设备发现 |
| WARNING | 可恢复错误 | 设备暂时离线、SMB 重连 |
| ERROR | 需要关注的失败 | 播放失败、认证错误 |

---

## 四、测试日志捕获与断言

### 4.1 LogCapture 类

```python
# tests/utils/log_capture.py
import json
import logging

class LogCapture:
    def __init__(self):
        self.records = []
        self.handler = None

    def start(self, logger_name=None):
        """开始捕获日志"""
        self.handler = CaptureHandler(self.records)
        logger = logging.getLogger(logger_name)
        logger.addHandler(self.handler)

    def stop(self):
        """停止捕获"""
        if self.handler:
            logging.getLogger().removeHandler(self.handler)

    def assert_logged(self, level: str, message_contains: str, context_match: dict = None):
        """断言特定日志被记录"""
        for r in self.records:
            if r["level"] != level:
                continue
            if message_contains not in r["message"]:
                continue
            if context_match is None:
                return True
            if all(r.get("context", {}).get(k) == v for k, v in context_match.items()):
                return True
        raise AssertionError(
            f"Expected log not found: level={level}, message contains '{message_contains}', "
            f"context={context_match}\n\nCaptured logs:\n{self.dump()}"
        )

    def assert_not_logged(self, level: str, message_contains: str):
        """断言特定日志未被记录"""
        for r in self.records:
            if r["level"] == level and message_contains in r["message"]:
                raise AssertionError(
                    f"Unexpected log found: level={level}, message contains '{message_contains}'"
                )

    def get_by_trace_id(self, trace_id: str) -> list:
        """获取某次请求的完整日志链"""
        return [r for r in self.records if r.get("trace_id") == trace_id]

    def get_by_level(self, level: str) -> list:
        """获取特定级别的所有日志"""
        return [r for r in self.records if r["level"] == level]

    def dump(self) -> str:
        """输出所有捕获的日志"""
        return "\n".join(json.dumps(r, indent=2, ensure_ascii=False) for r in self.records)

    def clear(self):
        """清空捕获的日志"""
        self.records.clear()


class CaptureHandler(logging.Handler):
    def __init__(self, records: list):
        super().__init__()
        self.records = records

    def emit(self, record):
        self.records.append({
            "timestamp": record.created,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "context": getattr(record, "context", {}),
            "trace_id": getattr(record, "trace_id", None),
            "file": record.filename,
            "line": record.lineno
        })
```

### 4.2 pytest fixture 集成

```python
# tests/conftest.py
import pytest

@pytest.fixture
def log_capture(request):
    capture = LogCapture()
    capture.start()
    yield capture
    capture.stop()

    # 测试失败时自动输出日志
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        print("\n=== Captured Logs ===")
        print(capture.dump())
```

### 4.3 使用示例

```python
async def test_playback_logs_completion(log_capture, mock_dlna, db_session):
    # 准备
    plan = Factory.plan(db_session)
    mock_dlna.add_device("dev1", "Test TV", "192.168.1.100")

    # 执行播放
    service = get_playback_service()
    await service.play(plan.id)

    # 模拟播放完成
    mock_dlna.set_position("dev1", 3600, 3600)
    await service.check_progress()

    # 断言日志
    log_capture.assert_logged("INFO", "Playback started", {"plan_id": plan.id})
    log_capture.assert_logged("INFO", "Playback completed", {"plan_id": plan.id})
    log_capture.assert_not_logged("ERROR", "failed")
```

---

## 五、测试用例设计

### 5.1 核心播放流程测试

```python
# tests/scenarios/test_scheduled_playback.py

class TestScheduledPlaybackFlow:
    async def test_complete_playback_cycle(self, client, mock_dlna, db_session):
        """计划触发 → 播放开始 → 进度追踪 → 正常完成"""
        # 1. 创建计划和设备
        # 2. 触发播放
        # 3. 模拟进度推进
        # 4. 验证完成状态和历史记录

    async def test_resume_from_last_position(self, client, mock_dlna, db_session):
        """断点续播：从上次位置 - 10秒处恢复"""
        # 1. 创建有进度的计划
        # 2. 触发播放
        # 3. 验证起始位置 = last_position - 10

    async def test_playlist_sequential_play(self, client, mock_dlna, db_session):
        """播放列表顺序播放，自动切换下一个"""

    async def test_playlist_loop_mode(self, client, mock_dlna, db_session):
        """列表循环模式：播完最后一个回到第一个"""


class TestProgressTracking:
    async def test_progress_saved_every_5_seconds(self):
        """验证 PROGRESS_SAVE_INTERVAL = 5.0"""

    async def test_completion_threshold(self):
        """距离结束 < 5秒时标记为完成"""

    async def test_progress_survives_restart(self):
        """重启后能从数据库恢复进度"""


class TestPlaybackBoundaries:
    async def test_seek_beyond_duration(self):
        """seek 超过总时长的处理"""

    async def test_volume_clamped_0_100(self):
        """音量值被限制在 0-100"""

    async def test_empty_playlist(self):
        """空播放列表不应崩溃"""
```

### 5.2 错误恢复测试

```python
# tests/scenarios/test_error_recovery.py

class TestDLNAErrorRecovery:
    async def test_device_offline_during_discovery(self, mock_dlna):
        """发现设备时设备离线"""
        mock_dlna.fail_mode = "offline"
        # 验证返回空列表，不抛异常

    async def test_device_disconnect_during_playback(self, mock_dlna, log_capture):
        """播放中设备断开连接"""
        # 验证: 记录错误日志，更新历史状态为 error
        log_capture.assert_logged("ERROR", "device disconnected")

    async def test_soap_request_timeout(self, mock_dlna):
        """DLNA SOAP 请求超时"""
        mock_dlna.fail_mode = "timeout"

    async def test_device_reappear_after_offline(self, mock_dlna):
        """设备离线后重新上线"""


class TestSMBErrorRecovery:
    async def test_smb_auth_failure(self, mock_smb):
        """SMB 认证失败"""
        mock_smb.fail_mode = "auth_error"

    async def test_smb_connection_lost_during_stream(self, mock_smb):
        """流媒体传输中 SMB 连接断开"""

    async def test_smb_file_not_found(self, mock_smb):
        """请求的 SMB 文件不存在"""
        mock_smb.fail_mode = "not_found"

    async def test_smb_share_permission_denied(self, mock_smb):
        """SMB 共享目录无权限"""


class TestResourceNotFound:
    async def test_play_deleted_plan(self, client):
        """播放已删除的计划"""
        resp = client.post("/api/v1/playback/play", json={"plan_id": "nonexistent"})
        assert resp.status_code == 404

    async def test_play_with_missing_device(self, client, db_session):
        """计划关联的设备已被删除"""

    async def test_media_file_removed_during_playlist(self):
        """播放列表中的文件在播放过程中被删除"""
```

### 5.3 数据库 CRUD 测试

```python
# tests/unit/test_crud.py

class TestPlanCRUD:
    def test_create_plan_generates_uuid(self, db_session):
        """创建计划时自动生成 UUID"""
        plan = crud.create_plan(db_session, {"title": "Test"})
        assert plan.id is not None
        assert len(plan.id) == 36  # UUID format

    def test_update_plan_partial_fields(self, db_session):
        """部分字段更新不影响其他字段"""
        plan = Factory.plan(db_session, title="Original", is_active=True)
        crud.update_plan(db_session, plan.id, {"title": "Updated"})
        updated = crud.get_plan(db_session, plan.id)
        assert updated.title == "Updated"
        assert updated.is_active == True  # 未变

    def test_delete_plan_cascades_history(self, db_session):
        """删除计划时关联的历史记录处理"""

    def test_get_active_plans_filter(self, db_session):
        """只返回 is_active=True 的计划"""
        Factory.plan(db_session, is_active=True)
        Factory.plan(db_session, is_active=False)
        active = crud.get_active_plans(db_session)
        assert len(active) == 1


class TestPlaybackHistoryCRUD:
    def test_pagination_respects_limit(self, db_session):
        """分页 limit 最大 100"""
        for _ in range(150):
            Factory.playback_history(db_session, plan_id="test")
        result = crud.get_playback_histories(db_session, page_size=200)
        assert len(result) <= 100

    def test_filter_by_plan_id(self, db_session):
        """按 plan_id 过滤历史记录"""

    def test_clear_history_removes_all(self, db_session):
        """清空历史删除所有记录"""


class TestCRUDBoundaries:
    def test_duplicate_device_upsert(self, db_session):
        """相同 ID 设备 upsert 更新而非插入"""

    def test_link_plan_study_task_idempotent(self, db_session):
        """重复关联不报错"""

    def test_empty_study_task_media_list(self, db_session):
        """学习任务可以没有媒体项"""
```

### 5.4 API 集成测试

```python
# tests/integration/test_api_playback.py

class TestPlaybackAPI:
    def test_play_returns_200(self, client, sample_plan):
        """POST /api/v1/playback/play 正常返回"""
        resp = client.post("/api/v1/playback/play", json={"plan_id": sample_plan.id})
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_play_invalid_plan_returns_404(self, client):
        """播放不存在的计划返回 404"""
        resp = client.post("/api/v1/playback/play", json={"plan_id": "nonexistent"})
        assert resp.status_code == 404

    def test_pause_without_active_playback_returns_400(self, client):
        """无活动播放时暂停返回 400"""
        resp = client.post("/api/v1/playback/pause")
        assert resp.status_code == 400

    def test_seek_negative_position_returns_400(self, client):
        """seek 负数位置返回 400"""

    def test_volume_out_of_range_clamped(self, client, active_playback):
        """音量超范围被自动钳制"""
        resp = client.post("/api/v1/playback/volume", json={"level": 150})
        assert resp.status_code == 200
        assert resp.json()["level"] == 100


class TestPathSecurity:
    def test_path_traversal_blocked(self, client):
        """../../../etc/passwd 被拒绝"""
        resp = client.get("/api/v1/media/local", params={"path": "../../../etc"})
        assert resp.status_code == 403

    def test_hidden_files_not_listed(self, client, tmp_media_dir):
        """.开头的文件不返回"""
        # 创建 .hidden 文件
        resp = client.get("/api/v1/media/local", params={"path": str(tmp_media_dir)})
        files = resp.json()["files"]
        assert not any(f["name"].startswith(".") for f in files)
```

---

## 六、测试数据工厂

```python
# tests/utils/fixtures.py
import uuid
from src.database import crud

class Factory:
    """测试数据工厂"""

    @staticmethod
    def plan(db_session, **overrides):
        """创建测试计划"""
        defaults = {
            "id": str(uuid.uuid4()),
            "title": "Test Plan",
            "device_id": None,
            "media_url": "smb://nas/video.mp4",
            "is_active": True,
            "play_mode": "sequential",
            "schedule_time": "08:00",
            "schedule_days": "1,2,3,4,5",
            "current_position": 0,
        }
        data = {**defaults, **overrides}
        return crud.create_plan(db_session, data)

    @staticmethod
    def device(db_session, **overrides):
        """创建测试设备"""
        defaults = {
            "id": str(uuid.uuid4()),
            "name": "Mock TV",
            "address": "192.168.1.100",
            "port": 1400,
            "is_online": True,
        }
        data = {**defaults, **overrides}
        return crud.create_device(db_session, data)

    @staticmethod
    def smb_server(db_session, **overrides):
        """创建测试 SMB 服务器"""
        defaults = {
            "id": str(uuid.uuid4()),
            "name": "Test NAS",
            "address": "192.168.1.200",
            "username": "admin",
            "password": "password",
            "share": "media",
        }
        data = {**defaults, **overrides}
        return crud.create_smb_server(db_session, data)

    @staticmethod
    def playback_history(db_session, plan_id, **overrides):
        """创建播放历史记录"""
        defaults = {
            "plan_id": plan_id,
            "status": "completed",
            "duration": 3600,
            "position": 3600,
        }
        data = {**defaults, **overrides}
        return crud.create_playback_history(db_session, data)

    @staticmethod
    def study_task(db_session, **overrides):
        """创建学习任务"""
        defaults = {
            "id": str(uuid.uuid4()),
            "name": "Test Study Task",
            "media_items": [],
        }
        data = {**defaults, **overrides}
        return crud.create_study_task(db_session, data)
```

---

## 七、pytest 配置

### 7.1 pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
addopts =
    --cov=src
    --cov-report=html:coverage_html
    --cov-report=term-missing
    --cov-fail-under=70
    -v

[coverage:run]
branch = True
omit =
    src/main.py
    tests/*
```

### 7.2 conftest.py

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.main import app
from src.database.models import Base
from src.services.dlna_manager import get_dlna_manager
from src.services.smb_client import get_smb_client
from src.services.scheduler import get_scheduler

from tests.mocks.mock_dlna import MockDLNAManager
from tests.mocks.mock_smb import MockSMBClient
from tests.mocks.mock_scheduler import MockScheduler
from tests.utils.log_capture import LogCapture
from tests.utils.fixtures import Factory


@pytest.fixture
def db_session():
    """每个测试使用独立的内存数据库"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_dlna():
    """DLNA 管理器 Mock"""
    return MockDLNAManager()


@pytest.fixture
def mock_smb():
    """SMB 客户端 Mock"""
    return MockSMBClient()


@pytest.fixture
def mock_scheduler():
    """调度器 Mock"""
    return MockScheduler()


@pytest.fixture
def client(db_session, mock_dlna, mock_smb, mock_scheduler):
    """注入所有 Mock 依赖的测试客户端"""
    app.dependency_overrides[get_dlna_manager] = lambda: mock_dlna
    app.dependency_overrides[get_smb_client] = lambda: mock_smb
    app.dependency_overrides[get_scheduler] = lambda: mock_scheduler
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def log_capture(request):
    """日志捕获器"""
    capture = LogCapture()
    capture.start()
    yield capture
    capture.stop()

    # 测试失败时自动输出日志
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        print("\n=== Captured Logs ===")
        print(capture.dump())


@pytest.fixture
def sample_plan(db_session):
    """示例计划"""
    return Factory.plan(db_session)


@pytest.fixture
def sample_device(db_session):
    """示例设备"""
    return Factory.device(db_session)


@pytest.fixture
def plan_with_device(db_session):
    """带设备的计划"""
    device = Factory.device(db_session)
    plan = Factory.plan(db_session, device_id=device.id)
    return plan, device


# pytest hook: 记录测试结果用于日志输出
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
```

---

## 八、人工测试支持

### 8.1 探索性测试清单

```markdown
# tests/manual/exploratory_checklist.md

## DLNA 设备兼容性
- [ ] 小米电视：发现、播放、暂停、进度条拖动
- [ ] 索尼电视：同上
- [ ] 投屏盒子（如天猫魔盒）：同上
- [ ] 多设备同时在线时的发现和选择

## SMB 存储兼容性
- [ ] 群晖 NAS：连接、浏览、播放大文件 (>4GB)
- [ ] Windows 共享文件夹：认证、中文路径
- [ ] OpenWrt 本地 Samba：同上

## 边缘操作
- [ ] 播放中拔掉网线，恢复后行为
- [ ] 播放中关闭电视电源，再开启
- [ ] 同时创建多个相同时间的定时计划
- [ ] 快速连续点击播放/暂停按钮

## 长时间运行
- [ ] 连续播放 24 小时稳定性
- [ ] 内存占用是否持续增长
- [ ] 数据库文件大小增长情况
```

### 8.2 验收测试清单

```markdown
# tests/manual/acceptance_checklist.md

## 发版前必检项

### 安装与启动
- [ ] 全新安装：opkg install 后服务正常启动
- [ ] 升级安装：保留原有数据库和配置
- [ ] 服务管理：start/stop/restart/status 正常

### LuCI 界面
- [ ] 所有页面可访问，无 JS 错误
- [ ] 中文显示正常
- [ ] 移动端浏览器适配

### 核心功能
- [ ] 创建计划 → 保存成功
- [ ] 发现设备 → 显示设备列表
- [ ] 手动播放 → 电视开始播放
- [ ] 定时触发 → 按时自动播放
- [ ] 进度保存 → 重启后能续播

### 错误处理
- [ ] 设备离线时给出明确提示
- [ ] SMB 连接失败时给出明确提示
- [ ] 无效参数返回合理错误信息
```

### 8.3 场景复现工具

```python
# tests/manual/reproduce_helper.py
"""快速复现特定场景的辅助脚本"""
import click
import httpx

API_BASE = "http://localhost:8088/api/v1"

@click.group()
def cli():
    """TrunPlay 测试场景复现工具"""
    pass

@cli.command()
@click.option("--count", default=5, help="设备数量")
def multiple_devices(count):
    """创建多个模拟设备"""
    for i in range(count):
        httpx.post(f"{API_BASE}/devices/add", json={
            "address": f"192.168.1.{100+i}",
            "port": 1400,
            "name": f"Mock TV {i+1}"
        })
    click.echo(f"已创建 {count} 个模拟设备")

@cli.command()
@click.option("--count", default=10, help="记录数量")
def failed_history(count):
    """创建失败的播放历史记录"""
    # 实现...
    click.echo(f"已创建 {count} 条失败记录")

@cli.command()
def large_playlist():
    """创建包含大量媒体的播放列表"""
    # 实现...
    click.echo("已创建大型播放列表")

@cli.command()
def clear_all():
    """清空所有测试数据"""
    httpx.delete(f"{API_BASE}/history")
    click.echo("已清空测试数据")

if __name__ == "__main__":
    cli()
```

---

## 九、闭环机制

### 9.1 覆盖率分析工具

```python
# tests/utils/coverage_analyzer.py
"""覆盖率缺口分析工具"""
import json
from pathlib import Path

class CoverageAnalyzer:
    def __init__(self, report_path="coverage.json"):
        self.report_path = report_path

    def find_untested_paths(self):
        """识别未覆盖的代码路径"""
        with open(self.report_path) as f:
            data = json.load(f)

        gaps = []
        for file_path, file_data in data["files"].items():
            missing = file_data.get("missing_lines", [])
            if missing:
                gaps.append({
                    "file": file_path,
                    "missing_lines": missing,
                    "coverage": file_data.get("summary", {}).get("percent_covered", 0)
                })

        return sorted(gaps, key=lambda x: x["coverage"])

    def generate_gap_report(self):
        """生成覆盖率缺口报告"""
        gaps = self.find_untested_paths()

        print("=" * 60)
        print("覆盖率缺口报告")
        print("=" * 60)

        for gap in gaps:
            print(f"\n{gap['file']} ({gap['coverage']:.1f}%)")
            print(f"  未覆盖行: {gap['missing_lines'][:10]}...")

        print("\n" + "=" * 60)
        print(f"共 {len(gaps)} 个文件存在覆盖缺口")

if __name__ == "__main__":
    analyzer = CoverageAnalyzer()
    analyzer.generate_gap_report()
```

### 9.2 Bug→测试转化流程

```markdown
## Bug 闭环流程

1. **发现 Bug**
   - 记录复现步骤到 issue
   - 标注影响范围和严重程度

2. **编写失败测试**
   - 在 `tests/regression/` 创建 `test_bug_<issue_id>.py`
   - 测试必须能复现 Bug（红色状态）

3. **修复代码**
   - 修复后测试变绿
   - 确保不影响其他测试

4. **归档**
   - 测试保留在 regression 目录
   - 每次 CI 运行防止回归
```

### 9.3 失败定位增强

```python
# tests/conftest.py 中添加

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.failed and call.when == "call":
        # 附加调试信息
        extra_info = []

        # 1. 捕获的日志
        if hasattr(item, "log_capture"):
            extra_info.append(("Captured Logs", item.log_capture.dump()))

        # 2. 数据库状态
        if hasattr(item, "db_session"):
            extra_info.append(("DB State", dump_db_state(item.db_session)))

        # 3. Mock 状态
        if hasattr(item, "mock_dlna"):
            extra_info.append(("DLNA Mock State", str(item.mock_dlna.playback_state)))

        for title, content in extra_info:
            report.sections.append((title, content))

def dump_db_state(session):
    """导出数据库当前状态"""
    from src.database import models
    state = {}
    state["plans"] = session.query(models.Plan).count()
    state["devices"] = session.query(models.Device).count()
    state["history"] = session.query(models.PlaybackHistory).count()
    return json.dumps(state, indent=2)
```

---

## 十、测试运行命令

```bash
# 运行全部测试
pytest

# 只运行单元测试（快速反馈，<10s）
pytest tests/unit -v

# 只运行特定场景
pytest tests/scenarios/test_scheduled_playback.py -v

# 运行单个测试方法
pytest tests/unit/test_crud.py::TestPlanCRUD::test_create_plan_generates_uuid -v

# 查看覆盖率报告
pytest --cov=src --cov-report=html && xdg-open coverage_html/index.html

# 只运行上次失败的测试
pytest --lf

# 显示详细日志输出
pytest -v --log-cli-level=DEBUG

# 生成覆盖率缺口报告
python -m tests.utils.coverage_analyzer

# 快速测试（单元测试 + 失败优先）
pytest tests/unit -v -x --ff
```

---

## 十一、测试场景矩阵

### 核心流程矩阵

| 场景 | 触发方式 | 媒体来源 | 播放模式 | 预期结果 |
|------|---------|---------|---------|---------|
| 手动播放本地文件 | API 调用 | 本地 | 单次 | 播放完成，记录历史 |
| 手动播放 SMB 文件 | API 调用 | SMB | 单次 | 播放完成，记录历史 |
| 定时触发播放 | Cron | 本地/SMB | 顺序 | 按时触发，顺序播放 |
| 断点续播 | API 调用 | 任意 | 任意 | 从上次位置-10s 恢复 |
| 列表循环播放 | 定时触发 | 任意 | 循环 | 播完重头开始 |
| 随机播放 | 任意 | 任意 | 随机 | 随机选择下一个 |

### 错误场景矩阵

| 错误类型 | 发生阶段 | 预期行为 | 日志级别 |
|---------|---------|---------|---------|
| 设备离线 | 播放前 | 返回错误，不创建历史 | ERROR |
| 设备断连 | 播放中 | 保存进度，标记 error | ERROR |
| SMB 认证失败 | 准备媒体 | 返回 401，记录日志 | ERROR |
| SMB 文件不存在 | 准备媒体 | 返回 404，跳到下一个 | WARNING |
| 路径越权访问 | 浏览文件 | 返回 403 | WARNING |
| SOAP 超时 | 控制设备 | 重试或返回失败 | WARNING |
| 数据库锁 | CRUD 操作 | 重试后成功或失败 | ERROR |

### 边界条件矩阵

| 边界 | 测试值 | 预期行为 |
|-----|-------|---------|
| 音量 | -10, 0, 50, 100, 150 | 钳制到 0-100 |
| Seek 位置 | -1, 0, duration-1, duration+100 | 钳制到有效范围 |
| 分页 page_size | 0, 1, 100, 200 | 限制 1-100 |
| 文件名 | 中文、空格、特殊字符 | 正确处理编码 |
| 空播放列表 | [] | 不崩溃，返回提示 |

---

## 十二、预期成果

| 指标 | 目标 |
|------|------|
| 核心模块覆盖率 | >80% |
| 整体覆盖率 | >70% |
| 单元测试运行时间 | <10s |
| 全量测试运行时间 | <60s |
| Bug 闭环周期 | <1 天 |
