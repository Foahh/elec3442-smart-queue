from __future__ import annotations

"""Pydantic API schemas."""

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel


@dataclass
class SensorReading:
    """Raw sensor values from Sense HAT (calibrated)."""

    temperature_c: float
    humidity_pct: float
    pressure_hpa: float


class QueueStatusResponse(BaseModel):
    """Current queue status payload."""

    timestamp: datetime
    queue_length: int
    estimated_wait_seconds: float
    estimated_wait_human: str
    throughput_per_minute: float
    busyness_level: str
    comfort_score: float
    comfort_label: str
    inference_ms: float
    tracking_ms: float
    persistence_ms: float
    end_to_end_latency_ms: float
    effective_fps: float
