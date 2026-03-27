from __future__ import annotations

"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="QE_")

    # Model
    yolo_model: str = "yolo26n.pt"
    yolo_confidence: float = 0.4
    yolo_iou: float = 0.5
    yolo_imgsz: int = 640
    model_dir: Path = Path("models")

    # Camera
    camera_source: Literal["picamera", "webcam"] = "webcam"
    camera_index: int = 0
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

    # Display backend
    display_backend: Literal["sensehat", "terminal", "none"] = "terminal"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database
    database_url: str = "sqlite:///data/queue.db"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings singleton."""

    return Settings()

