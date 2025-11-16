"""
Configuration settings for Torrent to Google Drive bot.
All settings are loaded from environment variables.
"""
import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""

    # Telegram Bot Configuration
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Owner/Admin User IDs (comma-separated)
    OWNER_IDS: list = [int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip()]

    # Download Configuration
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "/tmp/downloads")
    MAX_DOWNLOAD_SIZE: int = int(os.getenv("MAX_DOWNLOAD_SIZE", str(1024 * 1024 * 1024)))  # 1GB default
    CONCURRENT_DOWNLOADS: int = int(os.getenv("CONCURRENT_DOWNLOADS", "3"))

    # Torrent Client Configuration
    TORRENT_TIMEOUT: int = int(os.getenv("TORRENT_TIMEOUT", "3600"))  # 1 hour default
    SEED_TIME: int = int(os.getenv("SEED_TIME", "0"))  # No seeding by default

    # Rclone Configuration
    RCLONE_CONFIG_PATH: str = os.getenv("RCLONE_CONFIG_PATH", "/app/rclone.conf")
    RCLONE_REMOTE_NAME: str = os.getenv("RCLONE_REMOTE_NAME", "gdrive")
    RCLONE_BASE_DIR: str = os.getenv("RCLONE_BASE_DIR", "TorrentBot")

    # Google Drive Index Configuration
    INDEX_BASE_URL: str = os.getenv("INDEX_BASE_URL", "")

    # Progress Update Configuration
    PROGRESS_UPDATE_INTERVAL: int = int(os.getenv("PROGRESS_UPDATE_INTERVAL", "10"))  # seconds

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Heroku-specific
    PORT: int = int(os.getenv("PORT", "8080"))

    @classmethod
    def validate(cls) -> tuple[bool, Optional[str]]:
        """Validate required settings."""
        if not cls.BOT_TOKEN:
            return False, "BOT_TOKEN is required"

        if not cls.RCLONE_REMOTE_NAME:
            return False, "RCLONE_REMOTE_NAME is required"

        return True, None

    @classmethod
    def get_gdrive_path(cls, relative_path: str) -> str:
        """Get full Google Drive path."""
        base = cls.RCLONE_BASE_DIR.strip("/")
        rel = relative_path.strip("/")
        return f"{cls.RCLONE_REMOTE_NAME}:/{base}/{rel}" if base else f"{cls.RCLONE_REMOTE_NAME}:/{rel}"

    @classmethod
    def get_index_url(cls, relative_path: str) -> Optional[str]:
        """Get Google Drive index URL for a file."""
        if not cls.INDEX_BASE_URL:
            return None

        base_url = cls.INDEX_BASE_URL.rstrip("/")
        rel = relative_path.strip("/")
        base_dir = cls.RCLONE_BASE_DIR.strip("/")

        full_path = f"{base_dir}/{rel}" if base_dir else rel
        return f"{base_url}/{full_path}"


settings = Settings()
