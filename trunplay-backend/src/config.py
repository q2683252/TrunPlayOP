"""
TrunPlay Configuration.
"""
import os
import json
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

CONFIG_PATH = os.environ.get("TRUNPLAY_CONFIG_PATH", "/etc/trunplay/config.json")


@dataclass
class Config:
    """Application configuration."""
    api_port: int = 8088
    media_port: int = 8089
    db_path: str = "/etc/trunplay/trunplay.db"
    local_media_paths: List[str] = field(default_factory=lambda: ["/mnt", "/tmp"])
    log_level: str = "INFO"
    allowed_origins: List[str] = field(default_factory=lambda: ["http://localhost", "http://127.0.0.1"])
    ssdp_multicast_addr: str = "239.255.255.250"
    ssdp_port: int = 1900
    crontab_file: str = "/etc/crontabs/root"
    trigger_script: str = "/usr/bin/trunplay-trigger"
    media_chunk_size: int = 1048576  # 1MB

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file."""
        config = cls()

        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)
                    config.api_port = data.get("api_port", config.api_port)
                    config.media_port = data.get("media_port", config.media_port)
                    config.db_path = data.get("db_path", config.db_path)
                    config.local_media_paths = data.get("local_media_paths", config.local_media_paths)
                    config.log_level = data.get("log_level", config.log_level)
                    config.allowed_origins = data.get("allowed_origins", config.allowed_origins)
                    config.ssdp_multicast_addr = data.get("ssdp_multicast_addr", config.ssdp_multicast_addr)
                    config.ssdp_port = data.get("ssdp_port", config.ssdp_port)
                    config.crontab_file = data.get("crontab_file", config.crontab_file)
                    config.trigger_script = data.get("trigger_script", config.trigger_script)
                    config.media_chunk_size = data.get("media_chunk_size", config.media_chunk_size)
                logger.info(f"Loaded config from {CONFIG_PATH}")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}, using defaults")

        # Override with environment variables
        config.api_port = int(os.environ.get("TRUNPLAY_API_PORT", config.api_port))
        config.media_port = int(os.environ.get("TRUNPLAY_MEDIA_PORT", config.media_port))
        config.db_path = os.environ.get("TRUNPLAY_DB_PATH", config.db_path)
        config.log_level = os.environ.get("TRUNPLAY_LOG_LEVEL", config.log_level)
        config.crontab_file = os.environ.get("TRUNPLAY_CRONTAB_FILE", config.crontab_file)

        return config

    def save(self):
        """Save configuration to file."""
        config_dir = os.path.dirname(CONFIG_PATH)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        data = {
            "api_port": self.api_port,
            "media_port": self.media_port,
            "db_path": self.db_path,
            "local_media_paths": self.local_media_paths,
            "log_level": self.log_level,
            "allowed_origins": self.allowed_origins,
            "ssdp_multicast_addr": self.ssdp_multicast_addr,
            "ssdp_port": self.ssdp_port,
            "crontab_file": self.crontab_file,
            "trigger_script": self.trigger_script,
            "media_chunk_size": self.media_chunk_size
        }

        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved config to {CONFIG_PATH}")


# Global config instance
_config: Config = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config
