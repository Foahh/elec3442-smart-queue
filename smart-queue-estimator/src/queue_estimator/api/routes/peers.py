from __future__ import annotations

"""Peer site status route (local cache of hub data)."""

from dataclasses import asdict

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/peers", tags=["peers"])


@router.get("/")
def get_peers(request: Request) -> dict:
    """Return cached peer site snapshots from hub."""

    peer_cache = request.app.state.peer_cache
    if peer_cache is None:
        return {"sites": []}
    return {"sites": [asdict(s) for s in peer_cache.get_all()]}
