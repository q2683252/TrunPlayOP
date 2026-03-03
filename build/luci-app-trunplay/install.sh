#!/bin/sh
# TrunPlay LuCI App 安装脚本

echo "安装 TrunPlay LuCI 应用..."

# 复制 Lua 控制器
mkdir -p /usr/lib/lua/luci/controller
mkdir -p /usr/lib/lua/luci/view/trunplay
cp luasrc/controller/trunplay.lua /usr/lib/lua/luci/controller/

# 复制视图文件
cp -r luasrc/view/trunplay/* /usr/lib/lua/luci/view/trunplay/

# 复制静态文件
if [ -d "htdocs" ]; then
    mkdir -p /www
    cp -r htdocs/* /www/
fi

# 复制菜单和 ACL 配置
cp -r root/usr/share/* /usr/share/

# 清理 LuCI 缓存
rm -rf /tmp/luci-*

echo "安装完成！请刷新浏览器访问 LuCI 界面"
