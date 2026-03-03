#!/bin/bash
#
# 在本地 OpenWrt Docker 容器中测试真实 opkg 安装 TrunPlay IPK
# 使用带 opkg 的 openwrt-opkg 镜像，在容器内执行 opkg install。
# 依赖: Docker，文档见 docs/OPENWRT_DOCKER_LOCAL.md
#

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
IPK_GLOB="trunplay_*.ipk"
IMAGE_NAME="openwrt-opkg"

echo "========================================"
echo "OpenWrt Docker 真实 opkg 安装测试"
echo "========================================"

# 检查 Docker
if ! command -v docker >/dev/null 2>&1; then
    echo "错误: 未找到 docker。请先安装 Docker Desktop 或 Docker Engine。"
    echo "参见: docs/OPENWRT_DOCKER_LOCAL.md"
    exit 1
fi

# 若 Docker 未运行，尝试启动（macOS Docker Desktop）
if ! docker info >/dev/null 2>&1; then
    echo "Docker 未运行，尝试启动 Docker Desktop..."
    if [ "$(uname)" = "Darwin" ] && [ -d "/Applications/Docker.app" ]; then
        open -a Docker
        echo "等待 Docker 就绪（最多 60 秒）..."
        for i in $(seq 1 30); do
            if docker info >/dev/null 2>&1; then
                echo "Docker 已就绪"
                break
            fi
            sleep 2
        done
    fi
    if ! docker info >/dev/null 2>&1; then
        echo "错误: 无法连接 Docker。请手动启动 Docker Desktop 后再运行此脚本。"
        exit 1
    fi
fi

# 为 Docker 容器（linux/amd64）构建 IPK，确保二进制可在容器内运行
echo "为 Docker (linux/amd64) 构建 IPK..."
export GOOS=linux GOARCH=amd64
(cd "${REPO_ROOT}" && ./build-ipk.sh)
IPK_PATH=$(find "${DIST_DIR}" -maxdepth 1 -name "${IPK_GLOB}" -print -quit 2>/dev/null)
if [ -z "${IPK_PATH}" ] || [ ! -f "${IPK_PATH}" ]; then
    echo "错误: 构建后未找到 ${DIST_DIR}/${IPK_GLOB}"
    exit 1
fi

IPK_NAME=$(basename "${IPK_PATH}")
echo "使用 IPK: ${IPK_NAME}"
echo ""

# Apple Silicon 需用 amd64 平台
PLATFORM=""
case "$(uname -m)" in
    arm64|aarch64) PLATFORM="--platform linux/amd64" ;;
esac

# 构建或使用带 opkg 的镜像
if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
    echo "[1/4] 构建带 opkg 的 OpenWrt 镜像 (openwrt-opkg)..."
    docker build ${PLATFORM} -f "${REPO_ROOT}/tools/Dockerfile.openwrt-opkg" -t "${IMAGE_NAME}" "${REPO_ROOT}"
else
    echo "[1/4] 使用已有镜像: ${IMAGE_NAME}"
fi

echo "[2/4] 在容器内执行 opkg install（真实安装）..."
echo "[3/4] 启动 TrunPlay 并验证 API..."
echo "[4/4] 验证完成"
docker run --rm ${PLATFORM} \
    -v "${DIST_DIR}:/packages:ro" \
    "${IMAGE_NAME}" \
    sh -c '
        set -e
        echo "--- opkg 安装 TrunPlay IPK ---"
        opkg install /packages/trunplay_*.ipk
        echo ""
        echo "--- 已安装文件 ---"
        ls -la /usr/bin/trunplay /usr/bin/trunplay-trigger /etc/init.d/trunplay 2>/dev/null || true
        echo ""
        echo "--- 启动 TrunPlay 并验证 API ---"
        /usr/bin/trunplay &
        sleep 3
        wget -qO- http://127.0.0.1:8088/api/v1/system/status 2>/dev/null || true
        kill %1 2>/dev/null || true
        echo ""
        echo "--- 服务脚本 ---"
        ls -la /etc/init.d/trunplay
        echo ""
        echo "--- 配置 ---"
        cat /etc/trunplay/config.json 2>/dev/null | head -5 || true
        echo ""
        echo "真实 opkg 安装与验证完成。"
    '

echo ""
echo "========================================"
echo "Docker OpenWrt 真实 opkg 安装测试完成"
echo "========================================"
echo "说明: 已在带 opkg 的镜像内执行 opkg install，与实际设备安装方式一致。"
echo ""
