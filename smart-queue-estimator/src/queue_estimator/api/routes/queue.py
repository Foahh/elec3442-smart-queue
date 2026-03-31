from __future__ import annotations

"""Queue status and live data routes."""

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
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


_PREVIEW_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Queue Estimator preview</title></head>
<body style="margin:0;background:#111;color:#ccc;font-family:system-ui,sans-serif;">
<p style="padding:8px 12px;margin:0;">
  Live frame stream (MJPEG). If this stays blank, ensure the camera loop is running and HTTP preview is enabled (<code>QE_PREVIEW_MODE</code>=auto on Wayland, or <code>http</code> / <code>both</code>).
</p>
<img src="/api/v1/queue/preview/stream" alt="preview" style="display:block;max-width:100%;height:auto;"/>
</body>
</html>
"""


@router.get("/preview", response_class=HTMLResponse)
def preview_page() -> str:
    """Simple page that shows the MJPEG stream (works on Linux Wayland without OpenCV/Qt GUI)."""

    return _PREVIEW_HTML


@router.get("/preview/stream")
async def preview_stream(request: Request) -> StreamingResponse:
    """Multipart MJPEG of the latest annotated frame from the camera thread."""

    async def frames() -> asyncio.AsyncIterator[bytes]:
        while True:
            if await request.is_disconnected():
                break
            shared = request.app.state.shared_state
            if shared is None:
                await asyncio.sleep(0.1)
                continue
            jpg = shared.get_preview_jpeg()
            if jpg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            await asyncio.sleep(0.03)

    return StreamingResponse(
        frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

