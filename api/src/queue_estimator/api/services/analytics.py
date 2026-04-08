from __future__ import annotations

"""Analytics query and aggregation helpers."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session, select

from queue_estimator.db_models import PersonEvent, QueueSnapshot
from queue_estimator.schemas import AnalyticsSummary, HourlyStats


@dataclass
class _HourlyAggregate:
    """Mutable aggregation bucket for one hour."""

    queue_sum: float = 0.0
    wait_sum: float = 0.0
    sample_count: int = 0
    peak_queue_length: int = 0

    def add_snapshot(self, snapshot: QueueSnapshot) -> None:
        """Accumulate one queue snapshot into the hour bucket."""

        self.queue_sum += snapshot.queue_length
        self.wait_sum += snapshot.estimated_wait_seconds
        self.sample_count += 1
        self.peak_queue_length = max(self.peak_queue_length, snapshot.queue_length)

    def to_stats(self, hour: str, total_persons_served: int) -> HourlyStats:
        """Build the public response model for this hour."""

        count = max(self.sample_count, 1)
        return HourlyStats(
            hour=hour,
            avg_queue_length=self.queue_sum / count,
            avg_wait_seconds=self.wait_sum / count,
            total_persons_served=total_persons_served,
            peak_queue_length=self.peak_queue_length,
        )


def _hour_key(timestamp: datetime) -> str:
    """Return the canonical API key used for hourly groupings."""

    return timestamp.strftime("%Y-%m-%dT%H")


def read_period_data(
    session: Session,
    *,
    period_start: datetime,
) -> tuple[list[QueueSnapshot], list[PersonEvent]]:
    """Load queue snapshots and completed events for a time window."""

    snapshots_statement = select(QueueSnapshot).where(
        QueueSnapshot.timestamp >= period_start
    )
    events_statement = select(PersonEvent).where(PersonEvent.exit_time >= period_start)
    snapshots = list(session.execute(snapshots_statement).scalars())
    events = list(session.execute(events_statement).scalars())
    return snapshots, events


def build_hourly_breakdown(
    snapshots: list[QueueSnapshot],
    events: list[PersonEvent],
) -> list[HourlyStats]:
    """Aggregate raw records into hourly API statistics."""

    event_counts: dict[str, int] = defaultdict(int)
    for event in events:
        event_counts[event.date_hour] += 1

    buckets: dict[str, _HourlyAggregate] = {}
    for snapshot in snapshots:
        hour = _hour_key(snapshot.timestamp)
        bucket = buckets.setdefault(hour, _HourlyAggregate())
        bucket.add_snapshot(snapshot)

    return [
        bucket.to_stats(hour=hour, total_persons_served=event_counts.get(hour, 0))
        for hour, bucket in sorted(buckets.items())
    ]


def build_summary(
    session: Session,
    *,
    period_start: datetime,
    period_end: datetime,
) -> AnalyticsSummary:
    """Build the summary analytics response for a time window."""

    snapshots, events = read_period_data(session, period_start=period_start)
    breakdown = build_hourly_breakdown(snapshots, events)
    total_persons_served = len(events)
    avg_service_time_seconds = (
        sum(event.dwell_seconds for event in events) / total_persons_served
        if total_persons_served
        else 0.0
    )
    peak_hour = (
        max(breakdown, key=lambda item: item.avg_queue_length).hour
        if breakdown
        else None
    )

    return AnalyticsSummary(
        period_start=period_start,
        period_end=period_end,
        total_persons_served=total_persons_served,
        avg_service_time_seconds=avg_service_time_seconds,
        peak_hour=peak_hour,
        hourly_breakdown=breakdown,
    )


def build_peak_hours(
    session: Session,
    *,
    period_start: datetime,
    limit: int = 3,
) -> list[HourlyStats]:
    """Return the busiest hours in the requested time window."""

    snapshots, events = read_period_data(session, period_start=period_start)
    breakdown = build_hourly_breakdown(snapshots, events)
    return sorted(breakdown, key=lambda row: row.avg_queue_length, reverse=True)[:limit]
