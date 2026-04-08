from __future__ import annotations

"""Application configuration."""

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Runtime settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_prefix="QE_")

    # Model
    yolo_model: str = "yolo26n.pt"
    yolo_confidence: float = 0.4
    yolo_iou: float = 0.5
    yolo_imgsz: int = 640
    model_dir: Path = PROJECT_ROOT / "models"

    # Camera
    camera_source: Literal["picamera", "webcam", "video"] = "webcam"
    camera_index: int = 0
    camera_video_path: str | None = None
    camera_width: int = 1280
    camera_height: int = 720
    camera_fps: int = 10

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
    hub_push_interval: float = 5.0
    hub_pull_interval: float = 5.0

    # Sense HAT calibration
    temp_offset: float = -8.0
    queue_max_display: int = 16

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Preview: OpenCV's Qt GUI often breaks on Linux+Wayland (xcb / XWayland). Use HTTP stream instead.
    # auto = OpenCV window except on Linux+Wayland, where only the browser stream is enabled.
    preview_mode: Literal["auto", "opencv", "http", "off", "both"] = "auto"

    # Database
    database_url: str = "sqlite:///data/queue.db"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings singleton."""

    return Settings()


def preview_targets(settings: Settings) -> tuple[bool, bool]:
    """Return (use_opencv_window, use_http_stream) for the given preview_mode."""

    mode = settings.preview_mode
    if mode == "auto":
        if sys.platform == "linux" and os.environ.get("WAYLAND_DISPLAY"):
            return False, True
        return True, False
    if mode == "opencv":
        return True, False
    if mode == "http":
        return False, True
    if mode == "both":
        return True, True
    if mode == "off":
        return False, False
    raise RuntimeError(f"Unknown preview_mode: {mode}")
