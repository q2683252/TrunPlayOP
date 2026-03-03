#!/bin/bash
#
# TrunPlay 部署脚本 - 部署到 OpenWrt 测试环境
# 用法: ./deploy-to-openwrt.sh [SSH_PORT] [SSH_HOST]
#

set -e

# 配置
SSH_PORT="${1:-2222}"
SSH_HOST="${2:-127.0.0.1}"
SSH_USER="root"
SSH_CMD="ssh -o StrictHostKeyChecking=no -p $SSH_PORT $SSH_USER@$SSH_HOST"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/trunplay-backend"
LUCI_DIR="$SCRIPT_DIR/luci-app-trunplay"

echo "=============================================="
echo "  TrunPlay 部署到 OpenWrt 测试环境"
echo "=============================================="
echo "SSH 连接: $SSH_USER@$SSH_HOST:$SSH_PORT"
echo ""

# 检查 SSH 连接
log_info "检查 SSH 连接..."
if ! $SSH_CMD "echo 'SSH OK'" > /dev/null 2>&1; then
    log_error "无法连接到 OpenWrt: $SSH_HOST:$SSH_PORT"
    exit 1
fi
log_info "SSH 连接成功"

# 检查源代码目录
if [ ! -d "$BACKEND_DIR/src" ]; then
    log_error "后端源码目录不存在: $BACKEND_DIR/src"
    exit 1
fi

if [ ! -d "$LUCI_DIR/luasrc" ]; then
    log_error "LuCI 源码目录不存在: $LUCI_DIR/luasrc"
    exit 1
fi

# 1. 停止现有服务
log_info "停止现有 TrunPlay 服务..."
$SSH_CMD "kill \$(ps | grep 'python.*main.py' | grep -v grep | awk '{print \$1}') 2>/dev/null || true"
sleep 2

# 2. 创建目录
log_info "创建部署目录..."
$SSH_CMD "mkdir -p /opt/trunplay /etc/trunplay /var/lib/trunplay"

# 3. 部署后端代码
log_info "部署后端代码..."
cd "$BACKEND_DIR"
tar czf - src requirements.txt | $SSH_CMD "cd /opt/trunplay && rm -rf src && tar xzf -"

# 4. 部署 LuCI 前端
log_info "部署 LuCI 前端..."
cd "$LUCI_DIR"

# 部署控制器
tar czf - luasrc/controller/trunplay.lua | $SSH_CMD "cd / && tar xzf - && cp /luasrc/controller/trunplay.lua /usr/lib/lua/luci/controller/ && rm -rf /luasrc"

# 部署视图
$SSH_CMD "mkdir -p /usr/lib/lua/luci/view/trunplay"
tar czf - luasrc/view/trunplay | $SSH_CMD "cd / && tar xzf - && cp /luasrc/view/trunplay/*.htm /usr/lib/lua/luci/view/trunplay/ && rm -rf /luasrc"

# 5. 清理 LuCI 缓存
log_info "清理 LuCI 缓存..."
$SSH_CMD "rm -rf /tmp/luci-*"

# 6. 检查并安装 Python 依赖
log_info "检查 Python 依赖..."
$SSH_CMD "pip3 install sqlalchemy uvicorn async-upnp-client 2>&1 | grep -E '(Installing|already satisfied)' || true"

# 7. 启动后端服务
log_info "启动 TrunPlay 后端服务..."
$SSH_CMD "cd /opt/trunplay && python3 src/main.py > /tmp/trunplay.log 2>&1 &"

# 等待启动
log_info "等待服务启动..."
sleep 5

# 8. 验证服务
log_info "验证服务状态..."
MAX_RETRIES=5
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if $SSH_CMD "wget -qO- 'http://127.0.0.1:8088/api/v1/system/status' 2>/dev/null" | grep -q "version"; then
        log_info "后端服务启动成功!"
        break
    fi
    RETRY=$((RETRY + 1))
    log_warn "等待服务就绪... ($RETRY/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    log_error "后端服务启动失败，查看日志:"
    $SSH_CMD "cat /tmp/trunplay.log | tail -20"
    exit 1
fi

# 显示部署结果
echo ""
echo "=============================================="
echo -e "${GREEN}  部署完成!${NC}"
echo "=============================================="
echo ""
echo "访问方式:"
echo "  - LuCI 管理界面: http://$SSH_HOST:8091/cgi-bin/luci/admin/services/trunplay"
echo "  - API 接口: http://$SSH_HOST:8088/api/v1/"
echo ""
echo "常用命令:"
echo "  查看日志: ssh -p $SSH_PORT $SSH_USER@$SSH_HOST 'cat /tmp/trunplay.log'"
echo "  重启服务: ssh -p $SSH_PORT $SSH_USER@$SSH_HOST 'kill \$(ps | grep python.*main.py | grep -v grep | awk \"{print \\\$1}\"); cd /opt/trunplay && python3 src/main.py > /tmp/trunplay.log 2>&1 &'"
echo ""

# 显示服务状态
log_info "当前服务状态:"
$SSH_CMD "wget -qO- 'http://127.0.0.1:8088/api/v1/system/status'" | python3 -m json.tool 2>/dev/null || true
