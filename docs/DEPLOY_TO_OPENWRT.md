# TrunPlay 部署到 OpenWrt 虚拟机指南

## 概述

本指南帮助你将 TrunPlay 部署到 QEMU 运行的 OpenWrt 虚拟机中进行测试。

## 前置条件

### 1. OpenWrt 虚拟机要求

- OpenWrt 21.02 或更高版本
- 至少 128MB RAM
- 至少 50MB 可用存储空间
- 网络连接正常

### 2. 宿主机要求

- SSH 客户端
- 能够访问 OpenWrt 虚拟机的网络连接
- TrunPlay 源代码位于 `/data/tbase/TrunPlayOp`

## 部署步骤

### 步骤 1: 准备 OpenWrt 环境

#### 1.1 连接到 OpenWrt

```bash
ssh root@<OpenWrt_IP>
```

如果是首次连接，需要设置 root 密码：
```bash
passwd
```

#### 1.2 更新软件包列表

```bash
opkg update
```

#### 1.3 安装必需的包

```bash
opkg install python3 python3-pip python3-sqlite3 python3-asyncio \
             python3-logging python3-email python3-urllib curl
```

#### 1.4 安装 Python 依赖

```bash
pip3 install --no-cache-dir fastapi uvicorn sqlalchemy pydantic pysmb
```

**注意**: 如果存储空间不足，可以使用 `--no-cache-dir` 选项。

### 步骤 2: 检查环境

在宿主机上运行环境检查脚本：

```bash
cd /data/tbase/TrunPlayOp/tools
./check_openwrt_env.sh <OpenWrt_IP>
```

确保所有检查项都通过。

### 步骤 3: 部署 TrunPlay

运行部署脚本：

```bash
./deploy_to_openwrt.sh <OpenWrt_IP>
```

该脚本会自动：
1. 创建必要的目录结构
2. 复制后端代码到 `/usr/lib/trunplay`
3. 复制配置文件到 `/etc/trunplay`
4. 安装 init 脚本到 `/etc/init.d/trunplay`
5. 复制 LuCI 界面文件
6. 启动 TrunPlay 服务

### 步骤 4: 验证部署

#### 4.1 检查服务状态

在 OpenWrt 上：
```bash
/etc/init.d/trunplay status
ps | grep uvicorn
```

#### 4.2 测试 API

```bash
curl http://127.0.0.1:8088/health
```

应该返回：
```json
{"status":"ok"}
```

#### 4.3 访问 LuCI 界面

在浏览器中打开：
```
http://<OpenWrt_IP>/cgi-bin/luci/admin/services/trunplay
```

## 手动部署步骤（如果脚本失败）

### 1. 创建目录结构

```bash
ssh root@<OpenWrt_IP> << 'EOF'
mkdir -p /usr/lib/trunplay
mkdir -p /etc/trunplay
mkdir -p /etc/init.d
mkdir -p /usr/bin
mkdir -p /usr/lib/lua/luci/controller
mkdir -p /usr/lib/lua/luci/view/trunplay
mkdir -p /usr/share/luci/menu.d
mkdir -p /usr/share/rpcd/acl.d
EOF
```

### 2. 复制后端文件

```bash
# 后端代码
scp -r /data/tbase/TrunPlayOp/trunplay-backend/src/* root@<OpenWrt_IP>:/usr/lib/trunplay/

# 配置文件
scp /data/tbase/TrunPlayOp/trunplay-backend/root/etc/trunplay/config.json \
    root@<OpenWrt_IP>:/etc/trunplay/

# init 脚本
scp /data/tbase/TrunPlayOp/trunplay-backend/root/etc/init.d/trunplay \
    root@<OpenWrt_IP>:/etc/init.d/
scp /data/tbase/TrunPlayOp/trunplay-backend/root/usr/bin/trunplay-trigger \
    root@<OpenWrt_IP>:/usr/bin/

# 设置权限
ssh root@<OpenWrt_IP> "chmod +x /etc/init.d/trunplay /usr/bin/trunplay-trigger"
```

### 3. 复制 LuCI 文件

```bash
# 控制器
scp /data/tbase/TrunPlayOp/luci-app-trunplay/luasrc/controller/trunplay.lua \
    root@<OpenWrt_IP>:/usr/lib/lua/luci/controller/

# 视图
scp /data/tbase/TrunPlayOp/luci-app-trunplay/luasrc/view/trunplay/*.htm \
    root@<OpenWrt_IP>:/usr/lib/lua/luci/view/trunplay/

# 菜单和权限
scp /data/tbase/TrunPlayOp/luci-app-trunplay/root/usr/share/luci/menu.d/luci-app-trunplay.json \
    root@<OpenWrt_IP>:/usr/share/luci/menu.d/
scp /data/tbase/TrunPlayOp/luci-app-trunplay/root/usr/share/rpcd/acl.d/luci-app-trunplay.json \
    root@<OpenWrt_IP>:/usr/share/rpcd/acl.d/
```

### 4. 启动服务

```bash
ssh root@<OpenWrt_IP> << 'EOF'
# 清理 LuCI 缓存
rm -rf /tmp/luci-*

# 启用并启动服务
/etc/init.d/trunplay enable
/etc/init.d/trunplay start
EOF
```

## 常见问题排查

### 问题 1: 服务启动失败

**检查日志：**
```bash
ssh root@<OpenWrt_IP> "logread | grep trunplay"
```

**常见原因：**
- Python 依赖未安装完全
- 端口 8088 已被占用
- 权限问题

### 问题 2: LuCI 界面显示"后端服务未响应"

**检查后端状态：**
```bash
ssh root@<OpenWrt_IP> "curl http://127.0.0.1:8088/health"
```

**如果无响应：**
```bash
# 重启服务
ssh root@<OpenWrt_IP> "/etc/init.d/trunplay restart"

# 查看进程
ssh root@<OpenWrt_IP> "ps | grep uvicorn"
```

### 问题 3: 外部无法访问 API

**检查防火墙：**
```bash
ssh root@<OpenWrt_IP> << 'EOF'
# 添加防火墙规则
uci add firewall rule
uci set firewall.@rule[-1].name='Allow-TrunPlay-API'
uci set firewall.@rule[-1].src='wan'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].dest_port='8088'
uci set firewall.@rule[-1].target='ACCEPT'
uci commit firewall
/etc/init.d/firewall restart
EOF
```

### 问题 4: 存储空间不足

**清理临时文件：**
```bash
ssh root@<OpenWrt_IP> << 'EOF'
rm -rf /tmp/*
opkg clean
pip3 cache purge
EOF
```

**使用外部存储（如果有 USB）：**
```bash
# 挂载 USB 存储
mount /dev/sda1 /mnt/usb

# 移动 Python 包到 USB
mv /usr/lib/python3.* /mnt/usb/
ln -s /mnt/usb/python3.* /usr/lib/
```

## 服务管理命令

### 启动服务
```bash
ssh root@<OpenWrt_IP> "/etc/init.d/trunplay start"
```

### 停止服务
```bash
ssh root@<OpenWrt_IP> "/etc/init.d/trunplay stop"
```

### 重启服务
```bash
ssh root@<OpenWrt_IP> "/etc/init.d/trunplay restart"
```

### 查看状态
```bash
ssh root@<OpenWrt_IP> "/etc/init.d/trunplay status"
```

### 查看日志
```bash
ssh root@<OpenWrt_IP> "logread -f | grep trunplay"
```

## 测试模拟设备

部署完成后，你可以在宿主机上启动模拟 DLNA 设备和媒体服务器：

```bash
cd /data/tbase/TrunPlayOp/tools
./start_mock_services.sh --create-samples
```

然后在 OpenWrt 的 LuCI 界面中：
1. 进入"设备管理" → 点击"发现设备"
2. 应该能看到 "Mock TV (TrunPlay Test)"
3. 创建播放计划并测试播放功能

## 卸载

如果需要完全卸载 TrunPlay：

```bash
ssh root@<OpenWrt_IP> << 'EOF'
# 停止服务
/etc/init.d/trunplay stop
/etc/init.d/trunplay disable

# 删除文件
rm -rf /usr/lib/trunplay
rm -rf /etc/trunplay
rm -f /etc/init.d/trunplay
rm -f /usr/bin/trunplay-trigger
rm -f /usr/lib/lua/luci/controller/trunplay.lua
rm -rf /usr/lib/lua/luci/view/trunplay
rm -f /usr/share/luci/menu.d/luci-app-trunplay.json
rm -f /usr/share/rpcd/acl.d/luci-app-trunplay.json

# 清理 LuCI 缓存
rm -rf /tmp/luci-*

# 卸载 Python 包（可选）
pip3 uninstall -y fastapi uvicorn sqlalchemy pydantic pysmb
EOF
```

## 性能优化建议

### 1. 使用 SQLite WAL 模式
在 OpenWrt 上编辑 `/etc/trunplay/config.json`:
```json
{
  "database": {
    "wal_mode": true
  }
}
```

### 2. 限制日志级别
编辑 `/etc/init.d/trunplay`，设置环境变量：
```bash
export TRUNPLAY_LOG_LEVEL=WARNING
```

### 3. 减少 uvicorn workers
默认配置已经针对嵌入式设备优化（1 worker），无需修改。

## 参考

- OpenWrt 官方文档: https://openwrt.org/docs/start
- TrunPlay 项目地址: /data/tbase/TrunPlayOp
- API 文档: http://<OpenWrt_IP>:8088/docs
