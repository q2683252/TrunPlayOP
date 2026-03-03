#!/bin/bash
#
# TrunPlay 服务诊断脚本
# 用于检查 TrunPlay 后端服务状态和连接问题
#

echo "=========================================="
echo "TrunPlay 服务诊断"
echo "=========================================="
echo ""

# 1. 检查后端进程
echo "1. 检查后端进程..."
if pgrep -f "uvicorn src.main:app" > /dev/null; then
    echo "  ✓ 后端进程运行中"
    ps aux | grep -E "uvicorn src.main:app" | grep -v grep
else
    echo "  ✗ 后端进程未运行"
fi
echo ""

# 2. 检查端口监听
echo "2. 检查端口监听..."
if netstat -tlnp 2>/dev/null | grep -q ":8088 " || ss -tlnp 2>/dev/null | grep -q ":8088 "; then
    echo "  ✓ 8088 端口正在监听"
    netstat -tlnp 2>/dev/null | grep ":8088 " || ss -tlnp 2>/dev/null | grep ":8088 "
else
    echo "  ✗ 8088 端口未监听"
fi
echo ""

# 3. 测试本地连接
echo "3. 测试本地连接 (127.0.0.1:8088)..."
if curl -s -m 5 http://127.0.0.1:8088/health > /dev/null 2>&1; then
    echo "  ✓ 本地连接成功"
    curl -s http://127.0.0.1:8088/health
else
    echo "  ✗ 本地连接失败"
fi
echo ""

# 4. 测试外部连接
LOCAL_IP=$(ip route get 1 | awk '{print $7;exit}' 2>/dev/null)
echo "4. 测试外部连接 (${LOCAL_IP}:8088)..."
if [ -n "$LOCAL_IP" ]; then
    if curl -s -m 5 http://${LOCAL_IP}:8088/health > /dev/null 2>&1; then
        echo "  ✓ 外部连接成功"
        curl -s http://${LOCAL_IP}:8088/health
    else
        echo "  ✗ 外部连接失败 (可能有防火墙规则)"
    fi
else
    echo "  ✗ 无法获取本机 IP"
fi
echo ""

# 5. 检查数据库
echo "5. 检查数据库..."
if [ -f /etc/trunplay/trunplay.db ]; then
    echo "  ✓ 数据库文件存在: /etc/trunplay/trunplay.db"
    ls -lh /etc/trunplay/trunplay.db
elif [ -f /data/tbase/TrunPlayOp/tools/test_data/trunplay.db ]; then
    echo "  ✓ 测试数据库存在: /data/tbase/TrunPlayOp/tools/test_data/trunplay.db"
    ls -lh /data/tbase/TrunPlayOp/tools/test_data/trunplay.db
else
    echo "  ✗ 数据库文件不存在"
fi
echo ""

# 6. 检查配置文件
echo "6. 检查配置文件..."
if [ -f /etc/trunplay/config.json ]; then
    echo "  ✓ 配置文件存在: /etc/trunplay/config.json"
    cat /etc/trunplay/config.json
elif [ -f /data/tbase/TrunPlayOp/tools/test_data/config.json ]; then
    echo "  ✓ 测试配置存在"
else
    echo "  ✗ 配置文件不存在"
fi
echo ""

# 7. 检查后端日志
echo "7. 最近的后端日志..."
if [ -f /data/tbase/TrunPlayOp/tools/backend.log ]; then
    echo "  测试环境日志 (最后20行):"
    tail -20 /data/tbase/TrunPlayOp/tools/backend.log
elif [ -f /var/log/trunplay.log ]; then
    echo "  生产环境日志 (最后20行):"
    tail -20 /var/log/trunplay.log
else
    echo "  ✗ 未找到日志文件"
fi
echo ""

# 8. 测试 API 端点
echo "8. 测试关键 API 端点..."
endpoints=(
    "/health"
    "/api/v1/devices"
    "/api/v1/plans"
    "/api/v1/playback/status"
)

for endpoint in "${endpoints[@]}"; do
    response=$(curl -s -m 3 -w "\n%{http_code}" http://127.0.0.1:8088${endpoint} 2>&1)
    http_code=$(echo "$response" | tail -1)
    if [ "$http_code" = "200" ]; then
        echo "  ✓ ${endpoint} - OK"
    else
        echo "  ✗ ${endpoint} - 失败 (HTTP $http_code)"
    fi
done
echo ""

# 9. 检查防火墙规则
echo "9. 检查防火墙规则 (8088 端口)..."
if command -v iptables > /dev/null; then
    iptables -L INPUT -n | grep -q "8088" && echo "  发现 iptables 规则" || echo "  未发现特定规则"
fi
if command -v firewall-cmd > /dev/null 2>&1; then
    firewall-cmd --list-ports 2>/dev/null | grep -q "8088" && echo "  防火墙已开放 8088" || echo "  防火墙未明确开放 8088"
fi
echo ""

# 10. 建议
echo "=========================================="
echo "诊断建议:"
echo "=========================================="

if ! pgrep -f "uvicorn src.main:app" > /dev/null; then
    echo "⚠️  后端服务未运行"
    echo "   启动命令: cd /data/tbase/TrunPlayOp/trunplay-backend && python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8088"
    echo ""
fi

if ! curl -s -m 3 http://127.0.0.1:8088/health > /dev/null 2>&1; then
    echo "⚠️  本地无法连接到后端"
    echo "   检查后端是否正常启动"
    echo "   查看日志: tail -f /var/log/trunplay.log"
    echo ""
fi

if [ -n "$LOCAL_IP" ] && ! curl -s -m 3 http://${LOCAL_IP}:8088/health > /dev/null 2>&1; then
    echo "⚠️  外部无法连接到后端"
    echo "   可能需要调整防火墙规则"
    echo "   OpenWrt: uci add firewall rule && uci set firewall.@rule[-1].dest_port=8088 && uci commit && /etc/init.d/firewall restart"
    echo ""
fi

echo "=========================================="
