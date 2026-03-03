#!/bin/sh
#
# TrunPlay Backend 快速部署到 OpenWrt (用于测试)
# 将本地开发的文件复制到 OpenWrt 虚拟机
#

set -e

# 配置
OPENWRT_IP="${1:-192.168.1.1}"  # OpenWrt 虚拟机的 IP
OPENWRT_USER="root"
SOURCE_DIR="/data/tbase/TrunPlayOp"

echo "========================================"
echo "TrunPlay 部署到 OpenWrt 测试环境"
echo "========================================"
echo "目标: ${OPENWRT_USER}@${OPENWRT_IP}"
echo ""

# 检查连接
echo "1. 检查 OpenWrt 连接..."
if ! ssh -o ConnectTimeout=5 ${OPENWRT_USER}@${OPENWRT_IP} "echo 'Connected'" 2>/dev/null; then
    echo "错误: 无法连接到 OpenWrt (${OPENWRT_IP})"
    echo ""
    echo "请确保:"
    echo "  1. OpenWrt 虚拟机正在运行"
    echo "  2. IP 地址正确"
    echo "  3. SSH 密钥已配置或可以使用密码登录"
    echo ""
    echo "用法: $0 <OpenWrt_IP>"
    echo "示例: $0 192.168.122.100"
    exit 1
fi
echo "   ✓ 连接成功"
echo ""

# 创建目录结构
echo "2. 创建目录结构..."
ssh ${OPENWRT_USER}@${OPENWRT_IP} << 'EOF'
mkdir -p /usr/lib/trunplay
mkdir -p /etc/trunplay
mkdir -p /etc/init.d
mkdir -p /usr/bin
echo "   ✓ 目录创建完成"
EOF

# 复制后端文件
echo "3. 复制后端文件..."
scp -r ${SOURCE_DIR}/trunplay-backend/src/* ${OPENWRT_USER}@${OPENWRT_IP}:/usr/lib/trunplay/
scp ${SOURCE_DIR}/trunplay-backend/requirements.txt ${OPENWRT_USER}@${OPENWRT_IP}:/usr/lib/trunplay/
echo "   ✓ 后端文件已复制"

# 复制配置文件
echo "4. 复制配置文件..."
scp ${SOURCE_DIR}/trunplay-backend/root/etc/trunplay/config.json ${OPENWRT_USER}@${OPENWRT_IP}:/etc/trunplay/
echo "   ✓ 配置文件已复制"

# 复制 init 脚本
echo "5. 复制 init 脚本..."
scp ${SOURCE_DIR}/trunplay-backend/root/etc/init.d/trunplay ${OPENWRT_USER}@${OPENWRT_IP}:/etc/init.d/
scp ${SOURCE_DIR}/trunplay-backend/root/usr/bin/trunplay-trigger ${OPENWRT_USER}@${OPENWRT_IP}:/usr/bin/
ssh ${OPENWRT_USER}@${OPENWRT_IP} "chmod +x /etc/init.d/trunplay /usr/bin/trunplay-trigger"
echo "   ✓ init 脚本已复制"

# 复制 LuCI 文件
echo "6. 复制 LuCI 应用..."
ssh ${OPENWRT_USER}@${OPENWRT_IP} << 'EOF'
mkdir -p /usr/lib/lua/luci/controller
mkdir -p /usr/lib/lua/luci/view/trunplay
mkdir -p /usr/share/luci/menu.d
mkdir -p /usr/share/rpcd/acl.d
EOF

scp ${SOURCE_DIR}/luci-app-trunplay/luasrc/controller/trunplay.lua \
    ${OPENWRT_USER}@${OPENWRT_IP}:/usr/lib/lua/luci/controller/

scp ${SOURCE_DIR}/luci-app-trunplay/luasrc/view/trunplay/*.htm \
    ${OPENWRT_USER}@${OPENWRT_IP}:/usr/lib/lua/luci/view/trunplay/

scp ${SOURCE_DIR}/luci-app-trunplay/root/usr/share/luci/menu.d/luci-app-trunplay.json \
    ${OPENWRT_USER}@${OPENWRT_IP}:/usr/share/luci/menu.d/

scp ${SOURCE_DIR}/luci-app-trunplay/root/usr/share/rpcd/acl.d/luci-app-trunplay.json \
    ${OPENWRT_USER}@${OPENWRT_IP}:/usr/share/rpcd/acl.d/

echo "   ✓ LuCI 文件已复制"

# 安装 Python 依赖
echo "7. 安装 Python 依赖..."
ssh ${OPENWRT_USER}@${OPENWRT_IP} << 'EOF'
echo "   检查 Python 和 pip..."
which python3 || echo "   警告: python3 未安装"
which pip3 || echo "   警告: pip3 未安装"

if command -v pip3 > /dev/null; then
    echo "   安装依赖包..."
    pip3 install --no-cache-dir fastapi uvicorn sqlalchemy pydantic pysmb 2>&1 | grep -v "Requirement already satisfied" || true
    echo "   ✓ Python 依赖已安装"
else
    echo "   ⚠️  请手动安装: opkg install python3-pip"
    echo "   然后运行: pip3 install fastapi uvicorn sqlalchemy pydantic pysmb"
fi
EOF

# 清理 LuCI 缓存
echo "8. 清理 LuCI 缓存..."
ssh ${OPENWRT_USER}@${OPENWRT_IP} "rm -rf /tmp/luci-* 2>/dev/null || true"
echo "   ✓ LuCI 缓存已清理"

# 启动服务
echo "9. 启动 TrunPlay 服务..."
ssh ${OPENWRT_USER}@${OPENWRT_IP} << 'EOF'
# 停止旧服务
/etc/init.d/trunplay stop 2>/dev/null || true
pkill -f "uvicorn" || true
sleep 2

# 启动服务
/etc/init.d/trunplay start

sleep 3

# 检查状态
if pgrep -f "uvicorn" > /dev/null; then
    echo "   ✓ TrunPlay 服务已启动"
    echo ""
    echo "   进程信息:"
    ps | grep uvicorn | grep -v grep
else
    echo "   ✗ TrunPlay 服务启动失败"
    echo "   查看日志: logread | tail -50"
fi
EOF

# 测试 API
echo ""
echo "10. 测试 API 连接..."
sleep 2
if ssh ${OPENWRT_USER}@${OPENWRT_IP} "curl -s -m 5 http://127.0.0.1:8088/health" 2>/dev/null | grep -q "ok"; then
    echo "   ✓ API 响应正常"
    ssh ${OPENWRT_USER}@${OPENWRT_IP} "curl -s http://127.0.0.1:8088/health"
else
    echo "   ✗ API 无响应"
    echo "   在 OpenWrt 上执行: logread | grep trunplay"
fi

echo ""
echo "========================================"
echo "部署完成!"
echo "========================================"
echo ""
echo "访问 LuCI 界面:"
echo "  http://${OPENWRT_IP}/cgi-bin/luci/admin/services/trunplay"
echo ""
echo "API 地址:"
echo "  http://${OPENWRT_IP}:8088/docs"
echo ""
echo "常用命令:"
echo "  启动: ssh ${OPENWRT_USER}@${OPENWRT_IP} '/etc/init.d/trunplay start'"
echo "  停止: ssh ${OPENWRT_USER}@${OPENWRT_IP} '/etc/init.d/trunplay stop'"
echo "  日志: ssh ${OPENWRT_USER}@${OPENWRT_IP} 'logread | grep trunplay'"
echo ""
