from __future__ import annotations

"""Peer site status route (local cache of hub data)."""

from dataclasses import asdict

from fastapi import APIRouter, Request

from api.state import get_api_state
from schemas import PeerSiteSnapshot, PeerSitesResponse

router = APIRouter(prefix="/api/v1/peers", tags=["peers"])


@router.get("/", response_model=PeerSitesResponse)
def get_peers(request: Request) -> PeerSitesResponse:
    """Return cached peer site snapshots from hub."""

    peer_cache = get_api_state(request).peer_cache
    if peer_cache is None:
        return PeerSitesResponse(sites=[])
    return PeerSitesResponse(
        sites=[PeerSiteSnapshot(**asdict(site)) for site in peer_cache.get_all()]
    )
