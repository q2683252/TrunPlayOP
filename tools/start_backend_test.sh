#!/bin/bash
#
# Start TrunPlay backend for testing with mock services
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_DATA_DIR="${SCRIPT_DIR}/test_data"

# Clean up old test data
rm -rf "${TEST_DATA_DIR}"
mkdir -p "${TEST_DATA_DIR}"

# Set test environment variables
export TRUNPLAY_CONFIG_PATH="${TEST_DATA_DIR}/config.json"
export TRUNPLAY_DB_PATH="${TEST_DATA_DIR}/trunplay.db"
export TRUNPLAY_CRONTAB_FILE="${TEST_DATA_DIR}/crontab"
export TRUNPLAY_API_PORT="8088"
export TRUNPLAY_MEDIA_PORT="8090"  # Avoid conflict with mock DLNA on 8089

echo "=========================================="
echo "TrunPlay Backend Test Environment"
echo "=========================================="
echo "Config: ${TRUNPLAY_CONFIG_PATH}"
echo "Database: ${TRUNPLAY_DB_PATH}"
echo "API Port: ${TRUNPLAY_API_PORT}"
echo "Media Port: ${TRUNPLAY_MEDIA_PORT}"
echo "=========================================="
echo ""

cd "${SCRIPT_DIR}/../trunplay-backend"

# Start backend
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8088
