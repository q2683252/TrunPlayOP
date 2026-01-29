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
                logger.info(f"Loaded config from {CONFIG_PATH}")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}, using defaults")

        # Override with environment variables
        config.api_port = int(os.environ.get("TRUNPLAY_API_PORT", config.api_port))
        config.media_port = int(os.environ.get("TRUNPLAY_MEDIA_PORT", config.media_port))
        config.db_path = os.environ.get("TRUNPLAY_DB_PATH", config.db_path)
        config.log_level = os.environ.get("TRUNPLAY_LOG_LEVEL", config.log_level)

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
            "log_level": self.log_level
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
