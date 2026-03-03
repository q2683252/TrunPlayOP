#!/bin/bash
#
# TrunPlay 单一 IPK 包构建脚本 (OpenWrt 兼容)
#

set -e

VERSION="1.0.0"
PKG_RELEASE="1"
ARCH="all"
PKG_NAME="trunplay"
BUILD_DIR="$(pwd)/build-ipk"
DIST_DIR="$(pwd)/dist"

echo "========================================"
echo "构建 ${PKG_NAME}_${VERSION}-${PKG_RELEASE}_${ARCH}.ipk"
echo "========================================"

rm -rf "${BUILD_DIR}" "${DIST_DIR}"
mkdir -p "${BUILD_DIR}/CONTROL" "${BUILD_DIR}/data" "${DIST_DIR}"

# === 后端文件 ===
echo "[1/3] 复制后端文件..."
mkdir -p "${BUILD_DIR}/data/usr/lib/trunplay"
mkdir -p "${BUILD_DIR}/data/etc/init.d"
mkdir -p "${BUILD_DIR}/data/etc/trunplay"
mkdir -p "${BUILD_DIR}/data/usr/bin"

cp -r trunplay-backend/src/* "${BUILD_DIR}/data/usr/lib/trunplay/"
cp trunplay-backend/requirements.txt "${BUILD_DIR}/data/usr/lib/trunplay/"
cp trunplay-backend/root/etc/init.d/trunplay "${BUILD_DIR}/data/etc/init.d/"
cp trunplay-backend/root/etc/trunplay/config.json "${BUILD_DIR}/data/etc/trunplay/"
cp trunplay-backend/root/usr/bin/trunplay-trigger "${BUILD_DIR}/data/usr/bin/"

chmod 755 "${BUILD_DIR}/data/etc/init.d/trunplay"
chmod 755 "${BUILD_DIR}/data/usr/bin/trunplay-trigger"

# === LuCI 文件 ===
echo "[2/3] 复制 LuCI 文件..."
mkdir -p "${BUILD_DIR}/data/usr/lib/lua/luci/controller"
mkdir -p "${BUILD_DIR}/data/usr/lib/lua/luci/view/trunplay"
mkdir -p "${BUILD_DIR}/data/usr/share/luci/menu.d"
mkdir -p "${BUILD_DIR}/data/usr/share/rpcd/acl.d"

cp luci-app-trunplay/luasrc/controller/trunplay.lua "${BUILD_DIR}/data/usr/lib/lua/luci/controller/"
cp luci-app-trunplay/luasrc/view/trunplay/*.htm "${BUILD_DIR}/data/usr/lib/lua/luci/view/trunplay/"
cp luci-app-trunplay/root/usr/share/luci/menu.d/luci-app-trunplay.json "${BUILD_DIR}/data/usr/share/luci/menu.d/"
cp luci-app-trunplay/root/usr/share/rpcd/acl.d/luci-app-trunplay.json "${BUILD_DIR}/data/usr/share/rpcd/acl.d/"

# 清理缓存
find "${BUILD_DIR}/data" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}/data" -name "*.pyc" -delete 2>/dev/null || true

# 计算大小 (KB)
SIZE=$(du -sk "${BUILD_DIR}/data" | cut -f1)

# === CONTROL 文件 ===
echo "[3/3] 生成控制文件..."

cat > "${BUILD_DIR}/CONTROL/control" << EOF
Package: ${PKG_NAME}
Version: ${VERSION}-${PKG_RELEASE}
Depends: libc, python3, python3-sqlite3, python3-asyncio, python3-logging, python3-email, python3-urllib, luci-base
License: MIT
Section: luci
Architecture: ${ARCH}
Installed-Size: ${SIZE}
Description: TrunPlay - Scheduled DLNA media casting with LuCI interface
EOF

cat > "${BUILD_DIR}/CONTROL/conffiles" << 'EOF'
/etc/trunplay/config.json
EOF

cat > "${BUILD_DIR}/CONTROL/postinst" << 'EOF'
#!/bin/sh
[ "${IPKG_NO_SCRIPT}" = "1" ] && exit 0
[ -z "${IPKG_INSTROOT}" ] || exit 0

echo "Installing Python dependencies..."
pip3 install --no-cache-dir fastapi uvicorn sqlalchemy pydantic pysmb 2>/dev/null || {
    echo "Warning: Failed to install Python deps. Run manually:"
    echo "  pip3 install fastapi uvicorn sqlalchemy pydantic pysmb"
}

/etc/init.d/trunplay enable
/etc/init.d/trunplay start
rm -f /tmp/luci-indexcache /tmp/luci-modulecache/* 2>/dev/null || true

exit 0
EOF
chmod 755 "${BUILD_DIR}/CONTROL/postinst"

cat > "${BUILD_DIR}/CONTROL/prerm" << 'EOF'
#!/bin/sh
[ -z "${IPKG_INSTROOT}" ] || exit 0
/etc/init.d/trunplay stop 2>/dev/null || true
/etc/init.d/trunplay disable 2>/dev/null || true
exit 0
EOF
chmod 755 "${BUILD_DIR}/CONTROL/prerm"

cat > "${BUILD_DIR}/CONTROL/postrm" << 'EOF'
#!/bin/sh
[ -z "${IPKG_INSTROOT}" ] || exit 0
rm -f /tmp/luci-indexcache /tmp/luci-modulecache/* 2>/dev/null || true
exit 0
EOF
chmod 755 "${BUILD_DIR}/CONTROL/postrm"

# === 打包 ===
echo ""
echo "打包中..."

cd "${BUILD_DIR}"

# debian-binary
printf "2.0\n" > debian-binary

# control.tar.gz - 使用 GNU tar 格式，owner/group 设为 0
tar --format=gnu --numeric-owner --owner=0 --group=0 \
    -czf control.tar.gz -C CONTROL .

# data.tar.gz
tar --format=gnu --numeric-owner --owner=0 --group=0 \
    -czf data.tar.gz -C data .

# 使用 ar 创建 IPK
# OpenWrt opkg 需要标准 ar 格式（成员名不带斜杠）
IPK_FILE="${DIST_DIR}/${PKG_NAME}_${VERSION}-${PKG_RELEASE}_${ARCH}.ipk"
rm -f "${IPK_FILE}"

# 使用 Python 生成正确格式的 ar 档案
IPK_FILE="${IPK_FILE}" python3 << 'PYTHON_EOF'
import os

ipk_file = os.environ['IPK_FILE']

def ar_header(name, size):
    """Generate ar member header (60 bytes)"""
    # Format: name/16, mtime/12, uid/6, gid/6, mode/8, size/10, magic/2
    header = "%-16s%-12d%-6d%-6d%-8s%-10d`\n" % (
        name, 0, 0, 0, "100644", size
    )
    return header.encode('ascii')

with open(ipk_file, 'wb') as ipk:
    # ar magic
    ipk.write(b'!<arch>\n')

    # debian-binary
    with open('debian-binary', 'rb') as f:
        content = f.read()
    ipk.write(ar_header('debian-binary', len(content)))
    ipk.write(content)
    if len(content) % 2:
        ipk.write(b'\n')

    # control.tar.gz
    with open('control.tar.gz', 'rb') as f:
        content = f.read()
    ipk.write(ar_header('control.tar.gz', len(content)))
    ipk.write(content)
    if len(content) % 2:
        ipk.write(b'\n')

    # data.tar.gz
    with open('data.tar.gz', 'rb') as f:
        content = f.read()
    ipk.write(ar_header('data.tar.gz', len(content)))
    ipk.write(content)
    if len(content) % 2:
        ipk.write(b'\n')

print(f"Created {ipk_file}")
PYTHON_EOF

cd "${DIST_DIR}"
sha256sum *.ipk > SHA256SUMS

rm -rf "${BUILD_DIR}"

echo ""
echo "========================================"
echo "打包完成!"
echo "========================================"
ls -lh "${DIST_DIR}"/*.ipk
echo ""
cat SHA256SUMS
echo ""
echo "安装: opkg install ${PKG_NAME}_${VERSION}-${PKG_RELEASE}_${ARCH}.ipk"
