# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TrunPlay (定时投屏) is a scheduled DLNA/UPnP media casting application for OpenWrt routers. It enables automated media playback to DLNA-compatible devices (smart TVs, casters) with support for SMB network shares and local storage.

## Technology Stack

- **Backend**: Python 3 / FastAPI (async)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: LuCI (OpenWrt web interface) with Lua + HTML/JS
- **DLNA**: async-upnp-client for UPnP device discovery and control
- **SMB**: pysmb for network share access
- **Platform**: OpenWrt embedded Linux

## Development Commands

### Running the Backend Locally

```bash
cd trunplay-backend
pip install -r requirements.txt
python src/main.py
```

The API server runs on port 8088 and the media streaming server on port 8089.

### Building OpenWrt Packages

```bash
# After setting up OpenWrt SDK and adding packages to package/ directory
make package/trunplay-backend/compile V=s
make package/luci-app-trunplay/compile V=s
```

### Service Management (on OpenWrt device)

```bash
/etc/init.d/trunplay start|stop|restart|status
```

## Architecture

### Backend Structure (`trunplay-backend/src/`)

**Service Layer** (`services/`):
- `dlna_manager.py` - DLNA device discovery and AVTransport control
- `media_server.py` - HTTP streaming server with Range request support for seeking
- `smb_client.py` - SMB/CIFS file browsing and streaming
- `playback.py` - Orchestrates playback lifecycle, progress tracking
- `scheduler.py` - Cron job management for scheduled playback

**API Layer** (`api/`):
- FastAPI routers with `/api/v1` prefix
- Each router handles a specific domain (plans, devices, playback, etc.)

**Data Layer** (`database/`):
- `models.py` - SQLAlchemy ORM models (Plan, Device, SmbServer, PlaybackHistory, StudyTask)
- `schemas.py` - Pydantic request/response schemas
- `crud.py` - All database operations centralized here

**Key Patterns**:
- Services use singleton pattern via `get_*()` functions
- All I/O operations are async
- Media streaming supports HTTP Range requests for video seeking

### Frontend Structure (`luci-app-trunplay/`)

- `luasrc/controller/trunplay.lua` - LuCI routing and API proxy to backend
- `luasrc/view/trunplay/*.htm` - HTML templates for each page
- Pages: home (status), plans, devices, smb, study, history, settings

### Key Data Flow

1. **Scheduled Playback**: Cron triggers `trunplay-trigger` → Backend API → DLNA device
2. **Media Streaming**: DLNA device requests → Media server → SMB/local file → HTTP stream with Range support
3. **Progress Tracking**: Playback service polls DLNA position → Saves to PlaybackHistory

## Configuration

- Config file: `/etc/trunplay/config.json`
- Environment variables override config: `TRUNPLAY_API_PORT`, `TRUNPLAY_MEDIA_PORT`, `TRUNPLAY_DB_PATH`, `TRUNPLAY_LOG_LEVEL`

## API Endpoints

All endpoints are prefixed with `/api/v1`. Key endpoints:
- `POST /plans/{id}/play` - Manual playback trigger
- `POST /devices/discover` - DLNA device discovery
- `GET /media/local`, `GET /media/smb/{server_id}` - Browse media files
- `POST /playback/play`, `POST /playback/stop` - Playback control
- `GET /system/status` - System and service status
