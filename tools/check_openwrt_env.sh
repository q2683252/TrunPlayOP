#!/bin/bash
#
# OpenWrt 环境检查脚本
# 用于检查 OpenWrt 虚拟机是否满足 TrunPlay 的运行条件
#

OPENWRT_IP="${1}"

if [ -z "$OPENWRT_IP" ]; then
    echo "用法: $0 <OpenWrt_IP>"
    echo "示例: $0 192.168.1.1"
    exit 1
fi

echo "========================================"
echo "OpenWrt 环境检查"
echo "========================================"
echo "目标: root@${OPENWRT_IP}"
echo ""

# 测试连接
echo "1. 测试 SSH 连接..."
if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@${OPENWRT_IP} "echo 'OK'" 2>/dev/null; then
    echo "   ✗ 无法连接"
    echo ""
    echo "请先配置 SSH 访问:"
    echo "   1. 从本机复制公钥: ssh-copy-id root@${OPENWRT_IP}"
    echo "   2. 或在 OpenWrt 中设置 root 密码: passwd"
    exit 1
fi
echo "   ✓ 连接成功"
echo ""

# 检查系统信息
echo "2. 系统信息..."
ssh root@${OPENWRT_IP} << 'EOF'
echo "   系统: $(cat /etc/openwrt_release | grep DISTRIB_DESCRIPTION | cut -d"'" -f2)"
echo "   架构: $(uname -m)"
echo "   内核: $(uname -r)"
EOF
echo ""

# 检查已安装的包
echo "3. 检查必需的包..."
ssh root@${OPENWRT_IP} << 'EOF'
check_package() {
    if opkg list-installed | grep -q "^$1 "; then
        echo "   ✓ $1"
        return 0
    else
        echo "   ✗ $1 (未安装)"
        return 1
    fi
}

MISSING=0
check_package "python3" || MISSING=1
check_package "python3-pip" || MISSING=1
check_package "python3-sqlite3" || MISSING=1
check_package "python3-asyncio" || MISSING=1
check_package "python3-logging" || MISSING=1
check_package "luci" || MISSING=1
check_package "curl" || MISSING=1

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "   缺少必需的包，请运行:"
    echo "   opkg update"
    echo "   opkg install python3 python3-pip python3-sqlite3 python3-asyncio python3-logging python3-email python3-urllib curl"
fi

exit $MISSING
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  请先安装缺失的包"
    exit 1
fi
echo ""

# 检查存储空间
echo "4. 检查存储空间..."
ssh root@${OPENWRT_IP} << 'EOF'
df -h / | awk 'NR==2 {print "   根分区: " $2 " (已用 " $5 ")"}'
df -h /tmp | awk 'NR==2 {print "   临时分区: " $2 " (已用 " $5 ")"}'
EOF
echo ""

# 检查 Python 模块
echo "5. 检查 Python 环境..."
ssh root@${OPENWRT_IP} << 'EOF'
echo "   Python 版本: $(python3 --version 2>&1)"
echo "   pip 版本: $(pip3 --version 2>&1 | cut -d' ' -f1-2)"
echo ""
echo "   已安装的 Python 包:"
pip3 list 2>/dev/null | grep -E "(fastapi|uvicorn|sqlalchemy|pydantic|pysmb)" || echo "   (无相关包)"
EOF
echo ""

# 检查端口占用
echo "6. 检查端口占用..."
ssh root@${OPENWRT_IP} << 'EOF'
if netstat -tln 2>/dev/null | grep -q ":8088 "; then
    echo "   ⚠️  端口 8088 已被占用"
    netstat -tlnp | grep ":8088 "
else
    echo "   ✓ 端口 8088 可用"
fi
EOF
echo ""

# 检查防火墙
echo "7. 检查防火墙配置..."
ssh root@${OPENWRT_IP} << 'EOF'
if command -v fw3 > /dev/null 2>&1; then
    echo "   防火墙: fw3"
    if uci show firewall | grep -q "dest_port.*8088"; then
        echo "   ✓ 已有 8088 端口规则"
    else
        echo "   ⚠️  未发现 8088 端口规则"
        echo "   建议添加: uci add firewall rule && uci set firewall.@rule[-1].dest_port=8088 && uci commit && /etc/init.d/firewall restart"
    fi
else
    echo "   未检测到防火墙"
fi
EOF
echo ""

echo "========================================"
echo "环境检查完成"
echo "========================================"
echo ""
echo "下一步: 运行部署脚本"
echo "  ./deploy_to_openwrt.sh ${OPENWRT_IP}"
echo ""
