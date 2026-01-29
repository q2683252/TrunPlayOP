# TrunPlay OpenWrt Package

TrunPlay 定时投屏 - OpenWrt/LuCI 版本

## 项目结构

```
TrunPlayOp/
├── trunplay-backend/          # 后端服务 (Python + FastAPI)
│   ├── Makefile               # OpenWrt 打包 Makefile
│   ├── requirements.txt       # Python 依赖
│   ├── src/                   # 源代码
│   │   ├── main.py            # FastAPI 主入口
│   │   ├── config.py          # 配置管理
│   │   ├── api/               # REST API 端点
│   │   ├── database/          # 数据库模型和操作
│   │   └── services/          # 核心服务
│   └── root/                  # 系统文件
│       └── etc/
│           ├── init.d/trunplay          # procd 服务脚本
│           └── trunplay/config.json     # 默认配置
│
└── luci-app-trunplay/         # LuCI 前端
    ├── Makefile               # OpenWrt 打包 Makefile
    ├── luasrc/
    │   ├── controller/trunplay.lua      # Lua 控制器
    │   └── view/trunplay/               # HTML 模板
    ├── root/
    │   └── usr/share/
    │       ├── luci/menu.d/             # 菜单注册
    │       └── rpcd/acl.d/              # ACL 权限
    └── po/                    # 国际化文件
```

## 构建要求

- OpenWrt SDK 或完整编译环境
- LuCI feeds 已安装

## 构建步骤

### 1. 准备 OpenWrt 编译环境

```bash
# 克隆 OpenWrt (以 23.05 为例)
git clone https://git.openwrt.org/openwrt/openwrt.git
cd openwrt
git checkout v23.05.0

# 更新 feeds
./scripts/feeds update -a
./scripts/feeds install -a
```

### 2. 添加 TrunPlay 包

```bash
# 将 TrunPlayOp 目录复制到 package 目录
cp -r /path/to/TrunPlayOp/trunplay-backend package/
cp -r /path/to/TrunPlayOp/luci-app-trunplay package/

# 或者创建软链接
ln -s /path/to/TrunPlayOp/trunplay-backend package/trunplay-backend
ln -s /path/to/TrunPlayOp/luci-app-trunplay package/luci-app-trunplay
```

### 3. 配置和编译

```bash
# 运行 menuconfig
make menuconfig

# 选择:
# - Multimedia -> trunplay-backend
# - LuCI -> Applications -> luci-app-trunplay

# 编译单个包
make package/trunplay-backend/compile V=s
make package/luci-app-trunplay/compile V=s

# 或编译所有
make -j$(nproc)
```

### 4. 获取 IPK 文件

编译完成后，IPK 文件位于:
```
bin/packages/<arch>/base/trunplay-backend_1.0.0-1_all.ipk
bin/packages/<arch>/luci/luci-app-trunplay_1.0.0-1_all.ipk
```

## 安装

### 在 OpenWrt 设备上安装

```bash
# 通过 opkg 安装
opkg update
opkg install trunplay-backend_1.0.0-1_all.ipk
opkg install luci-app-trunplay_1.0.0-1_all.ipk

# 安装 Python 依赖 (如果自动安装失败)
pip3 install fastapi uvicorn sqlalchemy pydantic pysmb
```

### 服务管理

```bash
# 启动服务
/etc/init.d/trunplay start

# 停止服务
/etc/init.d/trunplay stop

# 重启服务
/etc/init.d/trunplay restart

# 开机自启
/etc/init.d/trunplay enable

# 禁用自启
/etc/init.d/trunplay disable

# 查看状态
/etc/init.d/trunplay status
```

## 访问 Web 界面

安装完成后，访问:
```
http://<router-ip>/cgi-bin/luci/admin/services/trunplay
```

## 配置文件

主配置文件: `/etc/trunplay/config.json`

```json
{
    "api_port": 8088,
    "media_port": 8089,
    "db_path": "/etc/trunplay/trunplay.db",
    "media_dirs": ["/mnt", "/root"],
    "log_level": "INFO"
}
```

## API 端点

后端 API 运行在端口 8088，主要端点:

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/plans` | GET/POST | 播放计划管理 |
| `/api/devices` | GET/POST | DLNA 设备管理 |
| `/api/devices/discover` | POST | 发现 DLNA 设备 |
| `/api/smb/servers` | GET/POST | SMB 服务器管理 |
| `/api/media/local` | GET | 浏览本地文件 |
| `/api/media/smb/{server_id}` | GET | 浏览 SMB 文件 |
| `/api/playback/start` | POST | 开始播放 |
| `/api/playback/stop` | POST | 停止播放 |
| `/api/playback/status` | GET | 播放状态 |
| `/api/history` | GET | 播放历史 |
| `/api/study/tasks` | GET/POST | 学习任务 |
| `/api/system/status` | GET | 系统状态 |

## 功能特性

- **DLNA 投屏**: 自动发现局域网内的 DLNA 设备并投屏
- **定时播放**: 支持 cron 表达式定义播放时间
- **SMB 支持**: 从网络共享 (NAS) 获取媒体文件
- **播放模式**: 顺序、随机、列表循环、单曲循环
- **学习任务**: 跟踪学习进度
- **播放历史**: 记录所有播放记录

## 依赖

### 系统依赖
- python3 (>= 3.7)
- python3-pip
- luci-base

### Python 依赖
- fastapi >= 0.68.0
- uvicorn >= 0.15.0
- sqlalchemy >= 1.4.0,<2.0.0
- pydantic >= 1.8.0,<2.0.0
- pysmb >= 1.2.0

## 许可证

MIT License
