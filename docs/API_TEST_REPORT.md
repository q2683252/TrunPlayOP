# TrunPlay Backend API 测试报告

## 测试环境

- **Mock DLNA 电视**: 9.134.66.94:8089
  - 设备名称: Mock TV (TrunPlay Test)
  - UDN: uuid:8fb01552-142f-40be-8b56-f41dfe4f8763

- **Mock 媒体服务器**: 9.134.66.94:4455
  - 协议: HTTP (模拟 SMB)
  - 测试媒体文件: Videos/sample_video_1.mp4

- **TrunPlay Backend**: 127.0.0.1:8088
  - API 端点: /api/v1
  - 数据库: /data/tbase/TrunPlayOp/tools/test_data/trunplay.db

## 测试结果

### ✅ 1. DLNA 设备发现 (Device Discovery)

**请求:**
```bash
POST /api/v1/devices/discover
```

**响应:**
```json
{
    "message": "Found 1 devices",
    "devices": [{
        "id": "uuid:8fb01552-142f-40be-8b56-f41dfe4f8763",
        "name": "Mock TV (TrunPlay Test)",
        "address": "9.134.66.94",
        "type": "MediaRenderer",
        "manufacturer": "TrunPlay Mock"
    }]
}
```

**状态: PASS** ✅
- 成功通过 SSDP M-SEARCH 发现模拟电视
- 设备信息正确解析

### ✅ 2. 设备列表 (List Devices)

**请求:**
```bash
GET /api/v1/devices
```

**状态: PASS** ✅
- 返回已发现的设备列表
- 设备状态 `is_online: true`
- Location URL 正确

### ✅ 3. 添加媒体服务器 (Add SMB Server)

**请求:**
```bash
POST /api/v1/smb/servers
{
    "name": "Test Media Server",
    "host": "9.134.66.94",
    "port": 4455,
    "protocol": "SMB",
    "username": "guest",
    "password": "",
    "share_path": "/"
}
```

**状态: PASS** ✅
- 成功添加服务器配置
- 生成唯一 server_id

### ✅ 4. 创建播放计划 (Create Plan)

**请求:**
```bash
POST /api/v1/plans
{
    "title": "Morning Cartoon",
    "start_time": "08:00",
    "end_time": "08:30",
    "repeat_days": "1,2,3,4,5",
    "device_id": "uuid:8fb01552-142f-40be-8b56-f41dfe4f8763",
    "media_url": "http://9.134.66.94:4455/Videos/sample_video_1.mp4",
    "is_active": true
}
```

**响应:**
```json
{
    "id": "ef4bea33-242e-402c-a742-17dbd148354c",
    "title": "Morning Cartoon",
    "start_time": "08:00",
    "end_time": "08:30",
    "repeat_days": "1,2,3,4,5",
    "device_id": "uuid:8fb01552-142f-40be-8b56-f41dfe4f8763",
    "media_url": "http://9.134.66.94:4455/Videos/sample_video_1.mp4",
    "is_active": true,
    "play_mode": "SEQUENTIAL"
}
```

**状态: PASS** ✅
- 计划创建成功
- 所有字段正确保存

### ✅ 5. 开始播放 (Start Playback)

**请求:**
```bash
POST /api/v1/playback/play
{
    "plan_id": "ef4bea33-242e-402c-a742-17dbd148354c"
}
```

**响应:**
```json
{
    "message": "Playback started"
}
```

**DLNA 电视日志:**
```
SOAP Action: SetAVTransportURI
Set URI: http://9.134.66.94:4455/Videos/sample_video_1.mp4
SOAP Action: Play
▶ Playing: http://9.134.66.94:4455/Videos/sample_video_1.mp4
```

**状态: PASS** ✅
- 成功向 DLNA 设备发送 SetAVTransportURI
- 成功发送 Play 命令
- 设备开始播放

### ✅ 6. 播放状态查询 (Playback Status)

**请求:**
```bash
GET /api/v1/playback/status
```

**响应:**
```json
{
    "status": "PLAYING",
    "device_id": "uuid:8fb01552-142f-40be-8b56-f41dfe4f8763",
    "device_name": "Mock TV (TrunPlay Test)",
    "plan_id": "ef4bea33-242e-402c-a742-17dbd148354c",
    "plan_title": "Morning Cartoon",
    "media_url": "http://9.134.66.94:4455/Videos/sample_video_1.mp4",
    "media_name": "sample_video_1.mp4",
    "position": 0,
    "duration": 0,
    "volume": 50
}
```

**状态: PASS** ✅
- 正确返回当前播放状态
- 所有播放信息完整

### ✅ 7. 暂停播放 (Pause)

**请求:**
```bash
POST /api/v1/playback/pause
```

**响应:**
```json
{
    "message": "Playback paused"
}
```

**DLNA 电视日志:**
```
SOAP Action: Pause
⏸ Paused
```

**状态: PASS** ✅
- 成功发送 Pause SOAP 命令
- 设备响应正常

### ✅ 8. 停止播放 (Stop)

**请求:**
```bash
POST /api/v1/playback/stop
```

**响应:**
```json
{
    "message": "Playback stopped"
}
```

**DLNA 电视日志:**
```
SOAP Action: Stop
⏹ Stopped
```

**状态: PASS** ✅
- 成功发送 Stop SOAP 命令
- 设备停止播放

## 测试总结

| 测试项 | 状态 | 备注 |
|--------|------|------|
| DLNA 设备发现 | ✅ PASS | SSDP 协议工作正常 |
| 设备列表查询 | ✅ PASS | 数据持久化正常 |
| 添加媒体服务器 | ✅ PASS | SMB 配置保存正常 |
| 创建播放计划 | ✅ PASS | 计划创建和存储正常 |
| 开始播放 | ✅ PASS | SOAP 命令正常发送 |
| 查询播放状态 | ✅ PASS | 状态跟踪正常 |
| 暂停播放 | ✅ PASS | SOAP 控制正常 |
| 停止播放 | ✅ PASS | SOAP 控制正常 |

**通过率: 8/8 (100%)**

## 协议交互流程

```
TrunPlay Backend          Mock DLNA TV
      |                        |
      |---M-SEARCH (SSDP)----->|
      |<----NOTIFY-------------|
      |                        |
      |---GET /description.xml->|
      |<----Device XML---------|
      |                        |
      |---SetAVTransportURI--->|
      |<----200 OK-------------|
      |                        |
      |---Play---------------->|
      |<----200 OK-------------|
      |      [Playing]         |
      |                        |
      |---Pause--------------->|
      |<----200 OK-------------|
      |      [Paused]          |
      |                        |
      |---Stop---------------->|
      |<----200 OK-------------|
      |      [Stopped]         |
```

## 结论

✅ **所有核心功能测试通过**

- DLNA 设备发现和控制功能正常
- 播放计划管理功能正常
- 播放控制（播放/暂停/停止）功能正常
- 与模拟 DLNA 设备的通信协议正确
- API 接口设计合理，返回数据完整

## 测试文件

- 模拟服务启动: `/data/tbase/TrunPlayOp/tools/start_mock_services.sh`
- 后端测试启动: `/data/tbase/TrunPlayOp/tools/start_backend_test.sh`
- API 测试脚本: `/data/tbase/TrunPlayOp/tools/test_apis_simple.sh`
- DLNA 模拟器: `/data/tbase/TrunPlayOp/tools/mock_dlna_device.py`
- 媒体服务器: `/data/tbase/TrunPlayOp/tools/mock_smb_server.py`
