"""
TrunPlay OpenWrt Backend - Main Entry Point.

This is the main FastAPI application that serves the REST API
and media streaming for DLNA playback.
"""
import os
import sys
import asyncio
import logging
import signal
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_config
from src.database.models import init_db, SessionLocal, DB_PATH
from src.services.dlna_manager import get_dlna_manager
from src.services.media_server import get_media_server
from src.services.smb_client import get_smb_client
from src.services.scheduler import get_scheduler
from src.services.playback import get_playback_service

# Import API routers
from src.api import plans, devices, smb, media, playback, study, history, system

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("trunplay")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("=" * 50)
    logger.info("TrunPlay Backend Starting...")
    logger.info("=" * 50)

    # Load config
    config = get_config()
    logger.info(f"Config: API port={config.api_port}, Media port={config.media_port}")
    logger.info(f"Database: {config.db_path}")

    # Set database path
    os.environ["TRUNPLAY_DB_PATH"] = config.db_path

    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info(f"Database initialized at {DB_PATH}")

    # Initialize services
    logger.info("Initializing services...")

    # DLNA Manager
    dlna_manager = get_dlna_manager()
    logger.info("DLNA Manager initialized")

    # Media Server
    media_server = get_media_server(port=config.media_port)
    logger.info(f"Media Server initialized on port {config.media_port}")

    # SMB Client
    smb_client = get_smb_client()
    logger.info("SMB Client initialized")

    # Scheduler
    scheduler = get_scheduler()
    logger.info("Scheduler initialized")

    # Playback Service
    playback_service = get_playback_service()
    playback_service.set_db_session_factory(SessionLocal)
    logger.info("Playback Service initialized")

    # Start media server in background
    media_app = media_server.create_app()
    media_config = uvicorn.Config(
        media_app,
        host="0.0.0.0",
        port=config.media_port,
        log_level="warning"
    )
    media_server_task = uvicorn.Server(media_config)

    async def run_media_server():
        await media_server_task.serve()

    media_task = asyncio.create_task(run_media_server())
    logger.info(f"Media HTTP Server started on port {config.media_port}")

    logger.info("=" * 50)
    logger.info("TrunPlay Backend Ready!")
    logger.info(f"API: http://0.0.0.0:{config.api_port}/api/v1")
    logger.info(f"Media: http://0.0.0.0:{config.media_port}/stream/...")
    logger.info("=" * 50)

    yield

    # Shutdown
    logger.info("Shutting down TrunPlay Backend...")

    # Stop media server
    media_server_task.should_exit = True
    media_task.cancel()
    try:
        await media_task
    except asyncio.CancelledError:
        pass

    # Close services
    await dlna_manager.close()
    smb_client.close_all()

    logger.info("TrunPlay Backend stopped")


# Create FastAPI app
app = FastAPI(
    title="TrunPlay API",
    description="TrunPlay OpenWrt Backend - Scheduled DLNA Media Casting",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(plans.router, prefix="/api/v1")
app.include_router(devices.router, prefix="/api/v1")
app.include_router(smb.router, prefix="/api/v1")
app.include_router(media.router, prefix="/api/v1")
app.include_router(playback.router, prefix="/api/v1")
app.include_router(study.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "TrunPlay API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


def main():
    """Main entry point."""
    config = get_config()

    # Set log level
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level)

    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the server
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=config.api_port,
        reload=False,
        log_level=config.log_level.lower()
    )


if __name__ == "__main__":
    main()
