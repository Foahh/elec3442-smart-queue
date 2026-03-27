from __future__ import annotations

"""FastAPI application factory and app-level state."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from queue import Empty, Queue
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from queue_estimator.database import create_db_and_tables


class WebSocketHub:
    """In-memory WebSocket connection manager."""

    def __init__(self) -> None:
        """Initialize connection hub."""

        self._connections: set[WebSocket] = set()
        self._queue: Queue[dict[str, Any]] = Queue()
        self._running = True

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store websocket connection."""

        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove websocket connection if present."""

        self._connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Broadcast payload to all connected clients."""

        stale_connections: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            except RuntimeError:
                stale_connections.append(connection)
        for connection in stale_connections:
            self.disconnect(connection)

    def enqueue(self, payload: dict[str, Any]) -> None:
        """Queue payload for async websocket broadcast."""

        self._queue.put(payload)

    async def run_dispatcher(self) -> None:
        """Dispatch queued messages to websocket clients."""

        while self._running:
            try:
                payload = self._queue.get(timeout=0.2)
            except Empty:
                await asyncio.sleep(0.05)
                continue
            await self.broadcast(payload)

    def stop(self) -> None:
        """Stop dispatcher loop."""

        self._running = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create resources at startup and cleanup at shutdown."""

    create_db_and_tables()
    logger.info("API startup complete")
    dispatcher_task = asyncio.create_task(app.state.ws_hub.run_dispatcher())
    yield
    app.state.ws_hub.stop()
    await dispatcher_task


def create_app(shared_state: Any | None = None) -> FastAPI:
    """Create and configure FastAPI app."""

    app = FastAPI(title="Smart Queue Estimator API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.ws_hub = WebSocketHub()
    app.state.shared_state = shared_state

    from queue_estimator.api.routes.analytics import router as analytics_router
    from queue_estimator.api.routes.queue import router as queue_router

    app.include_router(queue_router)
    app.include_router(analytics_router)
    return app

