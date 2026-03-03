#!/bin/bash
#
# TrunPlay Mock Services Launcher
# Starts mock DLNA device and SMB/HTTP media server for testing
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MOCK_MEDIA_DIR="${SCRIPT_DIR}/mock_media"

# Default settings
DLNA_NAME="Mock TV (TrunPlay Test)"
DLNA_PORT=8089
SMB_PORT=4455

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}          ${GREEN}TrunPlay Mock Services${NC}                            ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}          模拟 DLNA 电视和媒体服务器                        ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dlna-only       Only start DLNA device simulator"
    echo "  --smb-only        Only start SMB/HTTP media server"
    echo "  --dlna-name NAME  Set DLNA device name (default: '$DLNA_NAME')"
    echo "  --dlna-port PORT  Set DLNA HTTP port (default: $DLNA_PORT)"
    echo "  --smb-port PORT   Set SMB/HTTP port (default: $SMB_PORT)"
    echo "  --media-dir DIR   Set media directory (default: $MOCK_MEDIA_DIR)"
    echo "  --create-samples  Create sample media files"
    echo "  -h, --help        Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                        # Start both services"
    echo "  $0 --dlna-only            # Only DLNA device"
    echo "  $0 --smb-only --create-samples  # Only media server with samples"
    echo ""
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: python3 is required${NC}"
        exit 1
    fi
}

get_local_ip() {
    python3 -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "127.0.0.1"
}

# Parse arguments
DLNA_ONLY=false
SMB_ONLY=false
CREATE_SAMPLES=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dlna-only)
            DLNA_ONLY=true
            shift
            ;;
        --smb-only)
            SMB_ONLY=true
            shift
            ;;
        --dlna-name)
            DLNA_NAME="$2"
            shift 2
            ;;
        --dlna-port)
            DLNA_PORT="$2"
            shift 2
            ;;
        --smb-port)
            SMB_PORT="$2"
            shift 2
            ;;
        --media-dir)
            MOCK_MEDIA_DIR="$2"
            shift 2
            ;;
        --create-samples)
            CREATE_SAMPLES="--create-samples"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Main
print_banner
check_python

LOCAL_IP=$(get_local_ip)

echo -e "${YELLOW}Local IP:${NC} $LOCAL_IP"
echo ""

# Track PIDs for cleanup
PIDS=()

cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null || true
    echo -e "${GREEN}Services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start DLNA device
if [ "$SMB_ONLY" = false ]; then
    echo -e "${GREEN}Starting DLNA Device Simulator...${NC}"
    echo -e "  Name: ${DLNA_NAME}"
    echo -e "  Port: ${DLNA_PORT}"
    echo ""

    python3 "${SCRIPT_DIR}/mock_dlna_device.py" \
        --name "$DLNA_NAME" \
        --port "$DLNA_PORT" &
    PIDS+=($!)

    sleep 1
fi

# Start SMB/HTTP server
if [ "$DLNA_ONLY" = false ]; then
    echo -e "${GREEN}Starting Media Server...${NC}"
    echo -e "  Port: ${SMB_PORT}"
    echo -e "  Media: ${MOCK_MEDIA_DIR}"
    echo ""

    python3 "${SCRIPT_DIR}/mock_smb_server.py" \
        --share-path "$MOCK_MEDIA_DIR" \
        --port "$SMB_PORT" \
        --http \
        $CREATE_SAMPLES &
    PIDS+=($!)

    sleep 1
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Mock services running!${NC}"
echo ""

if [ "$SMB_ONLY" = false ]; then
    echo -e "🖥️  ${YELLOW}DLNA Device:${NC}"
    echo -e "   Name: $DLNA_NAME"
    echo -e "   Location: http://${LOCAL_IP}:${DLNA_PORT}/description.xml"
    echo ""
fi

if [ "$DLNA_ONLY" = false ]; then
    echo -e "📁 ${YELLOW}Media Server:${NC}"
    echo -e "   Browse: http://${LOCAL_IP}:${SMB_PORT}/"
    echo -e "   API: http://${LOCAL_IP}:${SMB_PORT}/api/files"
    echo ""
fi

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Press ${RED}Ctrl+C${NC} to stop all services"
echo ""

# Wait for all background processes
wait
