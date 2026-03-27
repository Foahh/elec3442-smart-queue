from __future__ import annotations

"""Queue status and live data routes."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from sqlmodel import Session, desc, select

from queue_estimator.api.dependencies import DBSessionDep
from queue_estimator.db_models import QueueSnapshot
from queue_estimator.schemas import QueueStatusResponse, SnapshotRecord

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])


@router.get("/status", response_model=QueueStatusResponse)
def get_status(request: Request) -> QueueStatusResponse:
    """Return latest in-memory queue status."""

    shared_state = request.app.state.shared_state
    if shared_state is None:
        raise HTTPException(status_code=503, detail="System initializing")
    status = shared_state.get()
    if status is None:
        raise HTTPException(status_code=503, detail="System initializing")
    return status


def _read_snapshots(session: Session, since: datetime, limit: int) -> list[QueueSnapshot]:
    """Fetch snapshots from database."""

    statement = (
        select(QueueSnapshot)
        .where(QueueSnapshot.timestamp >= since)
        .order_by(desc(QueueSnapshot.timestamp))
        .limit(limit)
    )
    return list(session.execute(statement).scalars())


@router.get("/history", response_model=list[SnapshotRecord])
def get_history(
    session: DBSessionDep,
    minutes: int = Query(default=60, ge=1),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[SnapshotRecord]:
    """Return queue snapshots over a lookback window."""

    since = datetime.now(UTC) - timedelta(minutes=minutes)
    rows = _read_snapshots(session, since=since, limit=limit)
    return [
        SnapshotRecord(
            timestamp=row.timestamp,
            queue_length=row.queue_length,
            estimated_wait_seconds=row.estimated_wait_seconds,
            busyness_level=row.busyness_level,
        )
        for row in rows
    ]


@router.websocket("/live")
async def live_status(websocket: WebSocket) -> None:
    """Stream live queue status updates to websocket clients."""

    hub = websocket.app.state.ws_hub
    await hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(websocket)

