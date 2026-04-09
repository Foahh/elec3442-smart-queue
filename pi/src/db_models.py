from __future__ import annotations

"""Database ORM models."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class QueueSnapshot(SQLModel, table=True):
    """Written every N seconds as core queue time-series data."""

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    queue_length: int
    estimated_wait_seconds: float
    throughput_per_minute: float
    busyness_level: str


class PersonEvent(SQLModel, table=True):
    """Represents one tracked person exiting the queue zone."""

    id: int | None = Field(default=None, primary_key=True)
    track_id: int
    entry_time: datetime
    exit_time: datetime
    dwell_seconds: float
    date_hour: str


class PeerSiteSnapshot(SQLModel, table=True):
    """Latest snapshot for a peer site pulled from the hub."""

    site_id: str = Field(primary_key=True)
    display_name: str
    queue_length: int
    estimated_wait_seconds: float
    busyness_level: str
    comfort_score: float | None = None
    updated_at: int
    stale: bool
    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_hpa: float | None = None
    latitude: float | None = None
    longitude: float | None = None
