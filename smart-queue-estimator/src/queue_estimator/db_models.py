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

