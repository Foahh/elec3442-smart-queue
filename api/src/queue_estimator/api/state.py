from __future__ import annotations

"""Typed access helpers for FastAPI app state."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from fastapi import HTTPException, Request, WebSocket

from queue_estimator.schemas import QueueStatusResponse, SensorReading

if TYPE_CHECKING:
    from queue_estimator.sync.hub_sync import SiteSnapshot


class SharedStateLike(Protocol):
    """Subset of shared runtime state used by the API."""

    def get(self) -> QueueStatusResponse | None:
        """Return the latest queue status when available."""

    def get_preview_jpeg(self) -> bytes | None:
        """Return the latest preview frame when available."""

    def get_sensors(self) -> SensorReading | None:
        """Return the latest sensor reading when available."""


class PeerCacheLike(Protocol):
    """Subset of peer cache behavior used by the API."""

    def get_all(self) -> list["SiteSnapshot"]:
        """Return all cached peer snapshots."""


class WebSocketHubLike(Protocol):
    """Subset of websocket hub behavior used by the API."""

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a websocket connection."""

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a websocket connection."""

    def enqueue(self, payload: dict[str, Any]) -> None:
        """Queue a websocket broadcast payload."""


@dataclass(frozen=True)
class APIState:
    """Typed container for API-level runtime dependencies."""

    ws_hub: WebSocketHubLike
    shared_state: SharedStateLike | None = None
    peer_cache: PeerCacheLike | None = None


def get_api_state(request: Request) -> APIState:
    """Return the typed API state stored on the FastAPI app."""

    return cast(APIState, request.app.state.api_state)


def require_shared_state(request: Request) -> SharedStateLike:
    """Return shared state or raise when the runtime is still initializing."""

    shared_state = get_api_state(request).shared_state
    if shared_state is None:
        raise HTTPException(status_code=503, detail="System initializing")
    return shared_state
