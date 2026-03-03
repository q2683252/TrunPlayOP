# 本地使用 OpenWrt Docker 测试 opkg 安装

在 macOS/Windows/Linux 上通过 Docker 运行带 **opkg** 的 OpenWrt 根文件系统，用于本地**真实**执行 `opkg install` 安装 TrunPlay IPK。

## 1. 安装 Docker

### macOS

1. 安装 [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)。
2. 安装完成后启动 Docker Desktop，确认菜单栏有 Docker 图标且状态为 Running。
3. 终端中执行 `docker --version` 确认可用。

### Windows

安装 [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)，启动后可在 WSL2 或 PowerShell 中使用 `docker`。

### Linux

```bash
# 以 Debian/Ubuntu 为例
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://downloads.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://downloads.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
# 当前用户免 sudo 运行（可选）
sudo usermod -aG docker $USER
```

## 2. 带 opkg 的 OpenWrt 镜像（openwrt-opkg）

测试脚本使用自定义镜像 **openwrt-opkg**，基于 `openwrt/rootfs`，在构建时从 OpenWrt 23.05.2 x86_64 base 仓库安装 opkg 及其依赖，使容器内可执行真实的 `opkg update` / `opkg install`。

首次运行测试脚本时会自动构建该镜像（约需数分钟）；之后会直接使用已有镜像。

如需手动构建：

```bash
cd /path/to/TrunPlayOp
# Apple Silicon 请加: docker build --platform linux/amd64 ...
docker build -f tools/Dockerfile.openwrt-opkg -t openwrt-opkg .
```

## 3. 使用脚本一键测试（推荐）

在项目根目录执行：

```bash
./tools/openwrt-docker-opkg-test.sh
```

脚本会：

1. 若 Docker 未运行则尝试启动（macOS 会打开 Docker Desktop）；
2. 使用 **GOOS=linux GOARCH=amd64** 构建 TrunPlay IPK（确保容器内可运行二进制）；
3. 若本地尚无 **openwrt-opkg** 镜像，则自动构建（含 opkg）；
4. 将 `dist/` 挂载到容器内，在容器内执行 **opkg install /packages/trunplay_*.ipk**（真实安装）；
5. 在容器内启动 `/usr/bin/trunplay` 并请求 `/api/v1/system/status` 验证；
6. 输出安装与验证结果。

**说明**：安装方式与实际 OpenWrt 设备上 `opkg install trunplay_*.ipk` 一致，非解包模拟。

## 4. 手动在容器内测试（真实 opkg 安装）

```bash
cd /path/to/TrunPlayOp

# 为 linux/amd64 构建 IPK（Docker 容器架构）
GOOS=linux GOARCH=amd64 ./build-ipk.sh

# 构建带 opkg 的镜像（仅首次或需重建时）
docker build -f tools/Dockerfile.openwrt-opkg -t openwrt-opkg .
# Apple Silicon: docker build --platform linux/amd64 -f tools/Dockerfile.openwrt-opkg -t openwrt-opkg .

# 启动容器并挂载 dist 目录（Apple Silicon 加 --platform linux/amd64）
docker run --rm -it -v "$(pwd)/dist:/packages:ro" openwrt-opkg
```

在容器内执行：

```sh
opkg install /packages/trunplay_*.ipk
ls -la /usr/bin/trunplay /etc/init.d/trunplay
/usr/bin/trunplay &
sleep 2
wget -qO- http://127.0.0.1:8088/api/v1/system/status
```

退出容器：`exit`。

## 5. 镜像与标签说明

- **openwrt-opkg**：本仓库通过 `Dockerfile.openwrt-opkg` 构建，基于 `openwrt/rootfs`，内含 opkg，用于真实 `opkg install` 测试。
- **架构**：默认构建为 x86_64；在 Apple Silicon (arm64) 上需使用 `--platform linux/amd64` 拉取/构建并运行，脚本会自动处理。

## 6. 常见问题

- **Docker 未安装**：终端执行 `docker` 报 “command not found” 时，请先按上文安装 Docker Desktop 或 Docker Engine。
- **Docker 未运行**：脚本会尝试启动 Docker Desktop（macOS）；若失败请手动打开 Docker Desktop 后再运行。
- **Apple Silicon (arm64)**：需使用 `--platform linux/amd64` 构建/运行镜像；脚本会使用 **GOOS=linux GOARCH=amd64** 构建 IPK，使容器内二进制可执行。
- **首次较慢**：首次运行会构建 openwrt-opkg 镜像（下载 openwrt/rootfs 及 opkg 相关 ipk），后续运行直接使用该镜像。
