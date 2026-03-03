#!/bin/sh
# TrunPlay Backend 安装脚本

echo "安装 TrunPlay Backend..."

# 创建目录
mkdir -p /usr/lib/trunplay
mkdir -p /etc/trunplay

# 复制文件
cp -r src/* /usr/lib/trunplay/
cp requirements.txt /usr/lib/trunplay/
cp root/etc/init.d/trunplay /etc/init.d/
cp root/usr/bin/trunplay-trigger /usr/bin/
cp root/etc/trunplay/config.json /etc/trunplay/

# 设置权限
chmod +x /etc/init.d/trunplay
chmod +x /usr/bin/trunplay-trigger

# 安装 Python 依赖
echo "安装 Python 依赖..."
pip3 install -r /usr/lib/trunplay/requirements.txt || {
    echo "警告: Python 依赖安装失败，请手动安装:"
    echo "  pip3 install fastapi uvicorn sqlalchemy pydantic pysmb"
}

# 启用服务
/etc/init.d/trunplay enable
echo "安装完成！使用 '/etc/init.d/trunplay start' 启动服务"
