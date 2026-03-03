#!/bin/sh
# TrunPlay 一键安装脚本

echo "========================================"
echo "TrunPlay 一键安装"
echo "========================================"

cd "$(dirname "$0")"

# 安装后端
echo ""
echo "[1/2] 安装后端服务..."
cd trunplay-backend
./install.sh
cd ..

# 安装 LuCI
echo ""
echo "[2/2] 安装 LuCI 应用..."
cd luci-app-trunplay
./install.sh
cd ..

# 启动服务
echo ""
echo "启动服务..."
/etc/init.d/trunplay start

echo ""
echo "========================================"
echo "安装完成!"
echo "========================================"
echo ""
echo "Web 界面: http://<router-ip>/cgi-bin/luci/admin/services/trunplay"
echo "API 文档: http://<router-ip>:8088/docs"
echo ""
