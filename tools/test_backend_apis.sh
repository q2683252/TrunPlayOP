#!/bin/bash
#
# Test TrunPlay Backend APIs with Mock Services
#

API_BASE="http://127.0.0.1:8088/api/v1"
MOCK_IP="9.134.66.94"

echo "========================================"
echo "TrunPlay Backend API Tests"
echo "========================================"
echo ""

# Test 1: Device Discovery
echo "=== Test 1: DLNA Device Discovery ==="
curl -s -X POST "${API_BASE}/devices/discover" | python3 -m json.tool
echo ""
sleep 2

# Test 2: List Devices
echo "=== Test 2: List Devices ==="
curl -s "${API_BASE}/devices" | python3 -m json.tool
echo ""

# Test 3: Add SMB Server (manual, since our HTTP server isn't real SMB)
echo "=== Test 3: Add HTTP Media Server as 'SMB' ==="
SERVER_ID=$(curl -s -X POST "${API_BASE}/smb/servers" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test Media Server\",
    \"host\": \"${MOCK_IP}\",
    \"port\": 4455,
    \"protocol\": \"SMB\",
    \"username\": \"guest\",
    \"password\": \"\",
    \"share_path\": \"/\"
  }" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "Created server with ID: $SERVER_ID"
echo ""

# Test 4: List SMB Servers
echo "=== Test 4: List SMB Servers ==="
curl -s "${API_BASE}/smb/servers" | python3 -m json.tool
echo ""

# Test 5: Browse Media Files
echo "=== Test 5: Browse Media Files ==="
curl -s "${API_BASE}/media/browse?path=/" | python3 -m json.tool
echo ""

# Test 6: Browse Videos Folder
echo "=== Test 6: Browse Videos Folder ==="
curl -s "${API_BASE}/media/browse?path=/Videos" | python3 -m json.tool
echo ""

# Test 7: Get Playback Status
echo "=== Test 7: Get Playback Status ==="
curl -s "${API_BASE}/playback/status" | python3 -m json.tool
echo ""

# Test 8: Create a Test Plan
echo "=== Test 8: Create Test Plan ==="
PLAN_ID=$(curl -s -X POST "${API_BASE}/plans" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Test Playback Plan\",
    \"media_url\": \"http://${MOCK_IP}:4455/Videos/sample_video_1.mp4\",
    \"media_name\": \"Sample Video 1\",
    \"device_id\": \"uuid:8fb01552-142f-40be-8b56-f41dfe4f8763\",
    \"is_active\": true,
    \"volume\": 50
  }" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "Created plan with ID: $PLAN_ID"
echo ""

# Test 9: List Plans
echo "=== Test 9: List Plans ==="
curl -s "${API_BASE}/plans" | python3 -m json.tool
echo ""

# Test 10: Manual Playback
echo "=== Test 10: Start Manual Playback ==="
curl -s -X POST "${API_BASE}/playback/play" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": \"uuid:8fb01552-142f-40be-8b56-f41dfe4f8763\",
    \"media_url\": \"http://${MOCK_IP}:4455/Videos/nature_documentary.mp4\",
    \"media_name\": \"Nature Documentary\"
  }" | python3 -m json.tool
echo ""

sleep 2

# Test 11: Get Playback Status After Play
echo "=== Test 11: Playback Status (Playing) ==="
curl -s "${API_BASE}/playback/status" | python3 -m json.tool
echo ""

# Test 12: Pause Playback
echo "=== Test 12: Pause Playback ==="
curl -s -X POST "${API_BASE}/playback/pause" | python3 -m json.tool
echo ""

# Test 13: Resume Playback
echo "=== Test 13: Resume Playback ==="
curl -s -X POST "${API_BASE}/playback/play" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": \"uuid:8fb01552-142f-40be-8b56-f41dfe4f8763\"
  }" | python3 -m json.tool
echo ""

# Test 14: Set Volume
echo "=== Test 14: Set Volume to 75 ==="
curl -s -X POST "${API_BASE}/playback/volume" \
  -H "Content-Type: application/json" \
  -d '{"volume": 75}' | python3 -m json.tool
echo ""

# Test 15: Stop Playback
echo "=== Test 15: Stop Playback ==="
curl -s -X POST "${API_BASE}/playback/stop" | python3 -m json.tool
echo ""

# Test 16: Playback History
echo "=== Test 16: Playback History ==="
curl -s "${API_BASE}/history?limit=10" | python3 -m json.tool
echo ""

# Test 17: System Info
echo "=== Test 17: System Info ==="
curl -s "${API_BASE}/system/info" | python3 -m json.tool
echo ""

echo "========================================"
echo "All Tests Complete!"
echo "========================================"
