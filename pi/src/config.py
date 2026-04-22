from __future__ import annotations

"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


PI_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PI_ROOT / ".env"


class Settings(BaseSettings):
    """Runtime settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="QE_")

    yolo_model_path: Path | None = None
    yolo_confidence: float = 0.4
    yolo_iou: float = 0.5
    yolo_imgsz: int = 640
    yolo_device: str = "cpu"

    # Camera
    camera_source: Literal["picamera", "video"] = "picamera"
    camera_index: int = 0
    camera_video_path: str | None = None
    camera_width: int = 640
    camera_height: int = 640
    camera_fps: int = 20

    # Queue Zone
    queue_zone: list[tuple[float, float]] = [
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    ]

    # Wait time estimation
    throughput_window_minutes: int = 15
    min_dwell_seconds: float = 3.0
    track_lost_grace_seconds: float = 1.5
    snapshots_per_minute: int = 2
    max_wait_seconds: float = 900.0

    # LED thresholds
    led_green_max: int = 3
    led_yellow_max: int = 8

    # Hub sync
    hub_url: str = ""
    hub_api_key: str = ""
    site_id: str = ""
    site_display_name: str = ""
    site_latitude: float | None = None
    site_longitude: float | None = None
    hub_push_interval: float = 2.5
    hub_pull_interval: float = 2.5

    # Sense HAT calibration
    temp_offset: float = -8.0
    queue_max_display: int = 16

    # Local preview HTTP server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Preview encoding (MJPEG)
    preview_enabled: bool = True
    preview_fps: int = 20
    preview_width: int = 640
    preview_height: int = 640
    preview_jpeg_quality: int = 70

    # Database
    database_url: str = "sqlite:///data/queue.db"

    # Logging
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings singleton."""

    return Settings()
