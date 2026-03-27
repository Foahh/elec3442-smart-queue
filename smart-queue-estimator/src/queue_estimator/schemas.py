from __future__ import annotations

"""Pydantic API schemas."""

from datetime import datetime

from pydantic import BaseModel


class QueueStatusResponse(BaseModel):
    """Current queue status payload."""

    timestamp: datetime
    queue_length: int
    estimated_wait_seconds: float
    estimated_wait_human: str
    throughput_per_minute: float
    busyness_level: str


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

