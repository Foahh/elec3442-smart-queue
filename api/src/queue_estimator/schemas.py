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


class SnapshotRecord(BaseModel):
    """Historical queue snapshot payload."""

    timestamp: datetime
    queue_length: int
    estimated_wait_seconds: float
    busyness_level: str


class HourlyStats(BaseModel):
    """Per-hour aggregate statistics."""

    hour: str
    avg_queue_length: float
    avg_wait_seconds: float
    total_persons_served: int
    peak_queue_length: int


class AnalyticsSummary(BaseModel):
    """Summary analytics response."""

    period_start: datetime
    period_end: datetime
    total_persons_served: int
    avg_service_time_seconds: float
    peak_hour: str | None
    hourly_breakdown: list[HourlyStats]


class PeerSiteSnapshot(BaseModel):
    """Peer site snapshot exposed by the API."""

    site_id: str
    display_name: str
    queue_length: int
    estimated_wait_seconds: float
    busyness_level: str
    comfort_score: float | None
    updated_at: int
    stale: bool
    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_hpa: float | None = None
    latitude: float | None = None
    longitude: float | None = None


class PeerSitesResponse(BaseModel):
    """Peer site collection response."""

    sites: list[PeerSiteSnapshot]
