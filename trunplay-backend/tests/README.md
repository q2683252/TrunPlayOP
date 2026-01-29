# TrunPlay 测试指南

## 快速开始

### 安装测试依赖

```bash
cd trunplay-backend
pip install pytest pytest-asyncio pytest-cov httpx
```

### 运行测试

```bash
# 运行所有测试
pytest

# 只运行单元测试 (最快)
pytest tests/unit -v

# 只运行集成测试
pytest tests/integration -v

# 只运行场景测试
pytest tests/scenarios -v

# 运行特定测试文件
pytest tests/unit/test_crud.py -v

# 运行特定测试类
pytest tests/unit/test_crud.py::TestPlanCRUD -v

# 运行特定测试方法
pytest tests/unit/test_crud.py::TestPlanCRUD::test_create_plan_generates_uuid -v
```

## 测试命令速查

| 命令 | 说明 |
|------|------|
| `pytest` | 运行所有测试 |
| `pytest -v` | 详细输出 |
| `pytest -x` | 遇到第一个失败就停止 |
| `pytest --lf` | 只运行上次失败的测试 |
| `pytest --ff` | 先运行上次失败的测试 |
| `pytest -k "keyword"` | 运行名称包含关键字的测试 |
| `pytest -m "marker"` | 运行特定标记的测试 |
| `pytest --cov=src` | 生成覆盖率报告 |
| `pytest --cov=src --cov-report=html` | 生成 HTML 覆盖率报告 |

## 测试目录结构

```
tests/
├── conftest.py          # 共享 fixtures
├── pytest.ini           # pytest 配置
│
├── unit/                # 单元测试
│   ├── test_crud.py     # 数据库 CRUD 测试
│   ├── test_schemas.py  # Schema 验证测试
│   └── test_utils.py    # 工具函数测试
│
├── integration/         # 集成测试
│   ├── test_api_plans.py
│   ├── test_api_devices.py
│   ├── test_api_playback.py
│   ├── test_api_media.py
│   ├── test_api_history.py
│   └── test_api_system.py
│
├── scenarios/           # 场景测试
│   ├── test_scheduled_playback.py  # 播放流程测试
│   ├── test_error_recovery.py      # 错误恢复测试
│   └── test_edge_cases.py          # 边界条件测试
│
├── regression/          # 回归测试 (Bug 转化的用例)
│
├── mocks/               # Mock 实现
│   ├── mock_dlna.py     # DLNA 管理器 Mock
│   ├── mock_smb.py      # SMB 客户端 Mock
│   └── mock_scheduler.py # 调度器 Mock
│
├── utils/               # 测试工具
│   ├── log_capture.py   # 日志捕获
│   ├── fixtures.py      # 数据工厂
│   └── coverage_analyzer.py  # 覆盖率分析
│
└── manual/              # 人工测试
    ├── exploratory_checklist.md   # 探索性测试清单
    ├── acceptance_checklist.md    # 验收测试清单
    └── reproduce_helper.py        # 场景复现工具
```

## 使用 Fixtures

### 数据库 Session

```python
def test_something(db_session):
    # db_session 是内存数据库的 SQLAlchemy session
    # 每个测试都有独立的数据库
    pass
```

### Mock 服务

```python
def test_dlna_operation(mock_dlna):
    # 添加模拟设备
    mock_dlna.add_device("dev1", "Test TV", "192.168.1.100")

    # 设置失败模式
    mock_dlna.fail_mode = "offline"

    # 执行测试...
```

### 日志捕获

```python
def test_with_logs(log_capture):
    # 执行操作...

    # 断言日志
    log_capture.assert_logged("INFO", "Operation completed")
    log_capture.assert_not_logged("ERROR", "failed")
```

### 测试数据工厂

```python
from tests.utils import Factory

def test_with_data(db_session):
    # 创建测试数据
    plan = Factory.plan(db_session, title="Custom Title")
    device = Factory.device(db_session)

    # 创建关联数据
    plan, device = Factory.plan_with_device(db_session)
```

## 覆盖率报告

```bash
# 生成覆盖率报告
pytest --cov=src --cov-report=html

# 打开报告
open coverage_html/index.html  # macOS
xdg-open coverage_html/index.html  # Linux
```

## 人工测试

### 探索性测试

查看 `tests/manual/exploratory_checklist.md` 获取探索性测试清单。

### 验收测试

发版前使用 `tests/manual/acceptance_checklist.md` 进行验收测试。

### 场景复现工具

```bash
# 查看当前数据状态
python tests/manual/reproduce_helper.py status

# 创建测试数据
python tests/manual/reproduce_helper.py setup-devices 5
python tests/manual/reproduce_helper.py setup-plans 10

# 清空测试数据
python tests/manual/reproduce_helper.py clear-all
```

## 编写新测试

### 单元测试示例

```python
# tests/unit/test_example.py

def test_simple_function(db_session):
    """测试简单功能"""
    # Arrange (准备)
    input_data = {...}

    # Act (执行)
    result = some_function(input_data)

    # Assert (断言)
    assert result == expected
```

### 异步测试示例

```python
# tests/scenarios/test_async_example.py
import pytest

@pytest.mark.asyncio
async def test_async_operation(mock_dlna):
    """测试异步操作"""
    mock_dlna.add_device("dev1", "TV", "192.168.1.100")

    result = await mock_dlna.play("dev1", "video.mp4")

    assert result is True
```

### Bug 回归测试

发现 Bug 后:

1. 在 `tests/regression/` 创建 `test_bug_<issue_id>.py`
2. 编写能复现 Bug 的测试 (先确保失败)
3. 修复 Bug
4. 确保测试通过
5. 测试永久保留防止回归

```python
# tests/regression/test_bug_123.py

def test_bug_123_volume_overflow():
    """
    Bug #123: 设置音量超过 100 时崩溃
    修复: 音量值钳制到 0-100 范围
    """
    # 这个测试在修复前会失败
    mock_dlna.set_volume("dev1", 150)
    volume = mock_dlna.get_volume("dev1")
    assert volume == 100  # 应该被钳制到 100
```

## 常见问题

### Q: 测试数据库在哪里?

A: 使用内存数据库 (`sqlite:///:memory:`)，每个测试都有独立的数据库实例。

### Q: 如何跳过某些测试?

A: 使用 `@pytest.mark.skip` 或 `@pytest.mark.skipif`:

```python
@pytest.mark.skip(reason="功能未实现")
def test_future_feature():
    pass

@pytest.mark.skipif(sys.platform == "win32", reason="仅 Linux")
def test_linux_only():
    pass
```

### Q: 如何标记慢测试?

A: 使用自定义标记:

```python
@pytest.mark.slow
def test_long_running():
    pass
```

运行时排除: `pytest -m "not slow"`
