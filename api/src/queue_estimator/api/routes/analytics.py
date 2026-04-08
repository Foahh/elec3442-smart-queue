from __future__ import annotations

"""Analytics routes."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query
from sqlmodel import Session, select

from queue_estimator.api.dependencies import DBSessionDep
from queue_estimator.db_models import PersonEvent, QueueSnapshot
from queue_estimator.schemas import AnalyticsSummary, HourlyStats

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _read_summary_data(
    session: Session,
    period_start: datetime,
) -> tuple[list[QueueSnapshot], list[PersonEvent]]:
    """Load snapshots and events in period."""

    snapshots_statement = select(QueueSnapshot).where(QueueSnapshot.timestamp >= period_start)
    events_statement = select(PersonEvent).where(PersonEvent.exit_time >= period_start)
    snapshots = list(session.execute(snapshots_statement).scalars())
    events = list(session.execute(events_statement).scalars())
    return snapshots, events


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(session: DBSessionDep, hours: int = Query(default=24, ge=1, le=24 * 30)) -> AnalyticsSummary:
    """Return aggregate analytics over the requested period."""

    period_end = datetime.now(UTC)
    period_start = period_end - timedelta(hours=hours)
    snapshots, events = _read_summary_data(session, period_start=period_start)

    hourly_events: dict[str, int] = defaultdict(int)
    for event in events:
        hourly_events[event.date_hour] += 1

    hourly_stats: dict[str, dict[str, float | int | str]] = {}
    for snapshot in snapshots:
        hour_key = snapshot.timestamp.strftime("%Y-%m-%dT%H")
        bucket = hourly_stats.setdefault(
            hour_key,
            {
                "hour": hour_key,
                "queue_sum": 0.0,
                "wait_sum": 0.0,
                "count": 0,
                "peak_queue_length": 0,
            },
        )
        bucket["queue_sum"] = float(bucket["queue_sum"]) + snapshot.queue_length
        bucket["wait_sum"] = float(bucket["wait_sum"]) + snapshot.estimated_wait_seconds
        bucket["count"] = int(bucket["count"]) + 1
        bucket["peak_queue_length"] = max(int(bucket["peak_queue_length"]), snapshot.queue_length)

    breakdown: list[HourlyStats] = []
    for hour, values in sorted(hourly_stats.items()):
        count = int(values["count"])
        avg_queue_length = float(values["queue_sum"]) / max(count, 1)
        avg_wait_seconds = float(values["wait_sum"]) / max(count, 1)
        breakdown.append(
            HourlyStats(
                hour=hour,
                avg_queue_length=avg_queue_length,
                avg_wait_seconds=avg_wait_seconds,
                total_persons_served=hourly_events.get(hour, 0),
                peak_queue_length=int(values["peak_queue_length"]),
            )
        )

    peak_hour: str | None = None
    if breakdown:
        peak_hour = max(breakdown, key=lambda item: item.avg_queue_length).hour

    total_persons_served = len(events)
    avg_service_time_seconds = (
        sum(event.dwell_seconds for event in events) / total_persons_served if total_persons_served else 0.0
    )

    return AnalyticsSummary(
        period_start=period_start,
        period_end=period_end,
        total_persons_served=total_persons_served,
        avg_service_time_seconds=avg_service_time_seconds,
        peak_hour=peak_hour,
        hourly_breakdown=breakdown,
    )


@router.get("/peak-hours", response_model=list[HourlyStats])
def get_peak_hours(session: DBSessionDep) -> list[HourlyStats]:
    """Return top 3 busiest hours by average queue length over last 7 days."""

    period_start = datetime.now(UTC) - timedelta(days=7)
    snapshots_statement = select(QueueSnapshot).where(QueueSnapshot.timestamp >= period_start)
    events_statement = select(PersonEvent).where(PersonEvent.exit_time >= period_start)

    snapshots = list(session.execute(snapshots_statement).scalars())
    events = list(session.execute(events_statement).scalars())
    event_counts: dict[str, int] = defaultdict(int)
    for event in events:
        event_counts[event.date_hour] += 1

    hour_buckets: dict[str, dict[str, float | int]] = {}
    for snapshot in snapshots:
        hour_key = snapshot.timestamp.strftime("%Y-%m-%dT%H")
        bucket = hour_buckets.setdefault(
            hour_key,
            {"queue_sum": 0.0, "wait_sum": 0.0, "count": 0, "peak_queue_length": 0},
        )
        bucket["queue_sum"] = float(bucket["queue_sum"]) + snapshot.queue_length
        bucket["wait_sum"] = float(bucket["wait_sum"]) + snapshot.estimated_wait_seconds
        bucket["count"] = int(bucket["count"]) + 1
        bucket["peak_queue_length"] = max(int(bucket["peak_queue_length"]), snapshot.queue_length)

    result: list[HourlyStats] = []
    for hour, values in hour_buckets.items():
        count = int(values["count"])
        result.append(
            HourlyStats(
                hour=hour,
                avg_queue_length=float(values["queue_sum"]) / max(count, 1),
                avg_wait_seconds=float(values["wait_sum"]) / max(count, 1),
                total_persons_served=event_counts.get(hour, 0),
                peak_queue_length=int(values["peak_queue_length"]),
            )
        )

    return sorted(result, key=lambda row: row.avg_queue_length, reverse=True)[:3]

