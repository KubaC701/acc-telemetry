"""Configuration settings for the FastAPI application."""

from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings."""

    # API Settings
    api_title: str = "ACC Telemetry Extractor API"
    api_version: str = "1.0.0"
    api_description: str = "API for processing ACC gameplay videos and extracting telemetry data"

    # CORS Settings
    cors_origins: list = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"]

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    data_output_dir: Path = base_dir / "data" / "output"
    videos_dir: Path = base_dir / "data" / "videos"
    config_dir: Path = base_dir / "config"
    roi_config_path: Path = config_dir / "roi_config.yaml"

    # Processing Settings
    max_concurrent_jobs: int = 2
    job_timeout_seconds: int = 3600  # 1 hour

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

# Ensure output directory exists
settings.data_output_dir.mkdir(parents=True, exist_ok=True)
settings.videos_dir.mkdir(parents=True, exist_ok=True)
