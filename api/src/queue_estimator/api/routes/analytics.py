from __future__ import annotations

"""Analytics routes."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query

from queue_estimator.api.dependencies import DBSessionDep
from queue_estimator.api.services.analytics import build_peak_hours, build_summary
from queue_estimator.schemas import AnalyticsSummary, HourlyStats

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(
    session: DBSessionDep, hours: int = Query(default=24, ge=1, le=24 * 30)
) -> AnalyticsSummary:
    """Return aggregate analytics over the requested period."""

    period_end = datetime.now(UTC)
    period_start = period_end - timedelta(hours=hours)
    return build_summary(
        session,
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/peak-hours", response_model=list[HourlyStats])
def get_peak_hours(session: DBSessionDep) -> list[HourlyStats]:
    """Return top 3 busiest hours by average queue length over last 7 days."""

    period_start = datetime.now(UTC) - timedelta(days=7)
    return build_peak_hours(session, period_start=period_start)
