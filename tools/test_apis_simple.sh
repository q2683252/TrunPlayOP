#!/bin/bash
#
# Simplified TrunPlay Backend API Tests
#

API_BASE="http://127.0.0.1:8088/api/v1"
MOCK_IP="9.134.66.94"

echo "========================================"
echo "TrunPlay Backend API Tests"
echo "========================================"
echo ""

# Test 1: Device Discovery
echo "✓ Test 1: DLNA Device Discovery"
DISCOVERY_RESULT=$(curl -s -X POST "${API_BASE}/devices/discover")
echo "$DISCOVERY_RESULT" | python3 -m json.tool
DEVICE_COUNT=$(echo "$DISCOVERY_RESULT" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['devices']))")
echo "Found $DEVICE_COUNT device(s)"
echo ""

# Test 2: List Devices
echo "✓ Test 2: List Devices"
DEVICES=$(curl -s "${API_BASE}/devices")
echo "$DEVICES" | python3 -m json.tool | head -20
DEVICE_ID=$(echo "$DEVICES" | python3 -c "import sys, json; print(json.load(sys.stdin)[0]['id'])")
echo "Device ID: $DEVICE_ID"
echo ""

# Test 3: Add Media Server
echo "✓ Test 3: Add Media Server"
SERVER_RESULT=$(curl -s -X POST "${API_BASE}/smb/servers" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test Media Server\",
    \"host\": \"${MOCK_IP}\",
    \"port\": 4455,
    \"protocol\": \"SMB\",
    \"username\": \"guest\",
    \"password\": \"\",
    \"share_path\": \"/\"
  }")
echo "$SERVER_RESULT" | python3 -m json.tool
SERVER_ID=$(echo "$SERVER_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Server ID: $SERVER_ID"
echo ""

# Test 4: Create a Plan
echo "✓ Test 4: Create Playback Plan"
PLAN_RESULT=$(curl -s -X POST "${API_BASE}/plans" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Test Video Playback\",
    \"media_url\": \"http://${MOCK_IP}:4455/Videos/sample_video_1.mp4\",
    \"media_name\": \"Sample Video 1\",
    \"device_id\": \"$DEVICE_ID\",
    \"is_active\": true,
    \"volume\": 50
  }")
echo "$PLAN_RESULT" | python3 -m json.tool
PLAN_ID=$(echo "$PLAN_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
echo "Plan ID: $PLAN_ID"
echo ""

# Test 5: List Plans
echo "✓ Test 5: List Plans"
curl -s "${API_BASE}/plans" | python3 -m json.tool
echo ""

# Test 6: Get Playback Status (Before)
echo "✓ Test 6: Playback Status (Before)"
curl -s "${API_BASE}/playback/status" | python3 -m json.tool
echo ""

# Test 7: Start Playback
echo "✓ Test 7: Start Playback"
PLAY_RESULT=$(curl -s -X POST "${API_BASE}/playback/play" \
  -H "Content-Type: application/json" \
  -d "{\"plan_id\": \"$PLAN_ID\"}")
echo "$PLAY_RESULT" | python3 -m json.tool
echo ""

sleep 2

# Test 8: Get Playback Status (Playing)
echo "✓ Test 8: Playback Status (Playing)"
curl -s "${API_BASE}/playback/status" | python3 -m json.tool
echo ""

# Test 9: Pause Playback
echo "✓ Test 9: Pause Playback"
curl -s -X POST "${API_BASE}/playback/pause" | python3 -m json.tool
echo ""

sleep 1

# Test 10: Get Playback Status (Paused)
echo "✓ Test 10: Playback Status (Paused)"
curl -s "${API_BASE}/playback/status" | python3 -m json.tool
echo ""

# Test 11: Resume Playback
echo "✓ Test 11: Resume Playback"
curl -s -X POST "${API_BASE}/playback/play" \
  -H "Content-Type: application/json" \
  -d "{\"plan_id\": \"$PLAN_ID\"}" | python3 -m json.tool
echo ""

sleep 1

# Test 12: Set Volume
echo "✓ Test 12: Set Volume to 80"
curl -s -X POST "${API_BASE}/playback/volume" \
  -H "Content-Type: application/json" \
  -d '{"level": 80}' | python3 -m json.tool
echo ""

# Test 13: Get Volume
echo "✓ Test 13: Get Volume"
curl -s "${API_BASE}/playback/volume" | python3 -m json.tool
echo ""

# Test 14: Stop Playback
echo "✓ Test 14: Stop Playback"
curl -s -X POST "${API_BASE}/playback/stop" | python3 -m json.tool
echo ""

# Test 15: Playback History
echo "✓ Test 15: Playback History"
curl -s "${API_BASE}/history?limit=5" | python3 -m json.tool
echo ""

# Test 16: System Info
echo "✓ Test 16: System Info"
curl -s "${API_BASE}/system/info" | python3 -m json.tool
echo ""

echo "========================================"
echo "✓ All Tests Complete!"
echo "========================================"
