#!/bin/bash
#
# TrunPlay 本地打包脚本
# 生成可直接部署到 OpenWrt 的 tar.gz 包
#

set -e

VERSION="1.0.0"
BUILD_DIR="build"
DIST_DIR="dist"

echo "========================================"
echo "TrunPlay 打包脚本 v${VERSION}"
echo "========================================"

# 清理旧的构建
rm -rf "${BUILD_DIR}" "${DIST_DIR}"
mkdir -p "${BUILD_DIR}/trunplay-backend" "${BUILD_DIR}/luci-app-trunplay" "${DIST_DIR}"

echo ""
echo "[1/4] 打包后端服务..."

# 复制后端文件
cp -r trunplay-backend/src "${BUILD_DIR}/trunplay-backend/"
cp -r trunplay-backend/root "${BUILD_DIR}/trunplay-backend/"
cp trunplay-backend/requirements.txt "${BUILD_DIR}/trunplay-backend/"

# 清理 Python 缓存
find "${BUILD_DIR}/trunplay-backend" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}/trunplay-backend" -type f -name "*.pyc" -delete 2>/dev/null || true

# 创建安装脚本
cat > "${BUILD_DIR}/trunplay-backend/install.sh" << 'INSTALL_EOF'
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
INSTALL_EOF
chmod +x "${BUILD_DIR}/trunplay-backend/install.sh"

echo "[2/4] 打包 LuCI 应用..."

# 复制 LuCI 文件
cp -r luci-app-trunplay/htdocs "${BUILD_DIR}/luci-app-trunplay/" 2>/dev/null || true
cp -r luci-app-trunplay/luasrc "${BUILD_DIR}/luci-app-trunplay/"
cp -r luci-app-trunplay/root "${BUILD_DIR}/luci-app-trunplay/"
cp -r luci-app-trunplay/po "${BUILD_DIR}/luci-app-trunplay/"

# 创建 LuCI 安装脚本
cat > "${BUILD_DIR}/luci-app-trunplay/install.sh" << 'INSTALL_EOF'
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
INSTALL_EOF
chmod +x "${BUILD_DIR}/luci-app-trunplay/install.sh"

echo "[3/4] 创建发布包..."

# 打包后端
cd "${BUILD_DIR}"
tar -czvf "../${DIST_DIR}/trunplay-backend-${VERSION}.tar.gz" trunplay-backend/
cd ..

# 打包 LuCI
cd "${BUILD_DIR}"
tar -czvf "../${DIST_DIR}/luci-app-trunplay-${VERSION}.tar.gz" luci-app-trunplay/
cd ..

# 创建一体化安装包
cat > "${BUILD_DIR}/install-all.sh" << 'INSTALL_ALL_EOF'
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
INSTALL_ALL_EOF
chmod +x "${BUILD_DIR}/install-all.sh"

cd "${BUILD_DIR}"
tar -czvf "../${DIST_DIR}/trunplay-full-${VERSION}.tar.gz" .
cd ..

echo "[4/4] 生成校验和..."
cd "${DIST_DIR}"
sha256sum *.tar.gz > SHA256SUMS
cd ..

echo ""
echo "========================================"
echo "打包完成!"
echo "========================================"
echo ""
echo "输出文件:"
ls -lh "${DIST_DIR}/"
echo ""
echo "安装方法:"
echo "  1. 上传到 OpenWrt 设备"
echo "  2. 解压: tar -xzf trunplay-full-${VERSION}.tar.gz"
echo "  3. 运行: ./install-all.sh"
echo ""
