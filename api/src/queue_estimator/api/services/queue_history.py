from __future__ import annotations

"""Queue history query helpers."""

from datetime import datetime

from sqlmodel import Session, desc, select

from queue_estimator.db_models import QueueSnapshot
from queue_estimator.schemas import SnapshotRecord


def list_snapshot_records(
    session: Session,
    *,
    since: datetime,
    limit: int,
) -> list[SnapshotRecord]:
    """Fetch queue snapshot history as API response models."""

    statement = (
        select(QueueSnapshot)
        .where(QueueSnapshot.timestamp >= since)
        .order_by(desc(QueueSnapshot.timestamp))
        .limit(limit)
    )
    snapshots = list(session.execute(statement).scalars())
    return [
        SnapshotRecord(
            timestamp=snapshot.timestamp,
            queue_length=snapshot.queue_length,
            estimated_wait_seconds=snapshot.estimated_wait_seconds,
            busyness_level=snapshot.busyness_level,
        )
        for snapshot in snapshots
    ]
