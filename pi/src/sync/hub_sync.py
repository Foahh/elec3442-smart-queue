from __future__ import annotations

"""Hub sync agent — push local status and pull peer status."""

import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

from config import Settings

if TYPE_CHECKING:
    from main import SharedState


@dataclass
class SiteSnapshot:
    """Peer site status received from hub."""

    site_id: str
    display_name: str
    queue_length: int
    estimated_wait_seconds: float
    busyness_level: str
    comfort_score: float | None
    updated_at: int
    stale: bool
    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_hpa: float | None = None
    latitude: float | None = None
    longitude: float | None = None


class PeerCache:
    """Thread-safe cache of all sites received from the hub."""

    _STALE_AFTER_SECONDS = 30.0

    def __init__(self) -> None:
        """Initialize empty cache."""

        self._lock = threading.Lock()
        self._sites: dict[str, SiteSnapshot] = {}
        self._cached_at: dict[str, float] = {}

    def update(self, snapshots: list[SiteSnapshot]) -> None:
        """Replace cache with fresh snapshot list."""

        now = time.monotonic()
        with self._lock:
            self._sites = {s.site_id: s for s in snapshots}
            self._cached_at = {s.site_id: now for s in snapshots}

    def get_all(self) -> list[SiteSnapshot]:
        """Return all cached snapshots with stale flag recomputed."""

        now = time.monotonic()
        with self._lock:
            result = []
            for site_id, snap in self._sites.items():
                age = now - self._cached_at.get(site_id, 0.0)
                stale = age > self._STALE_AFTER_SECONDS
                result.append(SiteSnapshot(**{**snap.__dict__, "stale": stale}))
        return result

    def is_empty(self) -> bool:
        """Return True if no peers have been fetched yet."""

        with self._lock:
            return len(self._sites) == 0


class HubSyncAgent:
    """Background daemon that pushes local status and pulls peer status."""

    def __init__(
        self,
        settings: Settings,
        shared_state: "SharedState",
        peer_cache: PeerCache,
    ) -> None:
        """Initialise agent with dependencies."""

        self._settings = settings
        self._shared_state = shared_state
        self._peer_cache = peer_cache
        self._push_backoff = settings.hub_push_interval
        self._pull_backoff = settings.hub_pull_interval

    def run(self) -> None:
        """Run push and pull loops indefinitely (call in daemon thread)."""

        last_push = 0.0
        last_pull = 0.0
        while True:
            now = time.monotonic()
            if now - last_push >= self._push_backoff:
                self._do_push()
                last_push = time.monotonic()
            if now - last_pull >= self._pull_backoff:
                self._do_pull()
                last_pull = time.monotonic()
            time.sleep(0.5)

    # ------------------------------------------------------------------ push

    def _build_body(self) -> dict[str, Any] | None:
        status = self._shared_state.get()
        if status is None:
            return None
        s = self._settings
        body: dict[str, Any] = {
            "site_id": s.site_id,
            "display_name": s.site_display_name,
            "queue_length": status.queue_length,
            "estimated_wait_seconds": status.estimated_wait_seconds,
            "busyness_level": status.busyness_level,
            "comfort_score": status.comfort_score,
            "snapshot": {
                "timestamp": int(status.timestamp.timestamp() * 1000),
                "queue_length": status.queue_length,
                "estimated_wait_seconds": status.estimated_wait_seconds,
                "busyness_level": status.busyness_level,
                "comfort_score": status.comfort_score,
            },
        }
        if s.site_latitude is not None:
            body["latitude"] = s.site_latitude
        if s.site_longitude is not None:
            body["longitude"] = s.site_longitude
        sensors = self._shared_state.get_sensors()
        if sensors is not None:
            body["sensors"] = {
                "temperature_c": sensors.temperature_c,
                "humidity_pct": sensors.humidity_pct,
                "pressure_hpa": sensors.pressure_hpa,
            }
        return body

    def _do_push(self) -> None:
        body = self._build_body()
        if body is None:
            return
        url = self._settings.hub_url.rstrip("/") + "/api/ingest"
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": self._settings.hub_api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status == 200:
                    self._push_backoff = self._settings.hub_push_interval
                    return
                raise urllib.error.HTTPError(url, resp.status, "non-200", {}, None)  # type: ignore[arg-type]
        except Exception as exc:
            logger.warning(
                "Hub push failed: {}; backoff={:.0f}s", exc, self._push_backoff
            )
            self._push_backoff = min(self._push_backoff * 2, 60.0)

    # ------------------------------------------------------------------ pull

    def _do_pull(self) -> None:
        url = self._settings.hub_url.rstrip("/") + "/api/sites"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                payload = json.loads(resp.read())
            snapshots = [
                SiteSnapshot(
                    site_id=s["site_id"],
                    display_name=s["display_name"],
                    queue_length=s["queue_length"],
                    estimated_wait_seconds=s["estimated_wait_seconds"],
                    busyness_level=s["busyness_level"],
                    comfort_score=s.get("comfort_score"),
                    updated_at=s["updated_at"],
                    stale=s.get("stale", False),
                    temperature_c=s.get("temperature_c"),
                    humidity_pct=s.get("humidity_pct"),
                    pressure_hpa=s.get("pressure_hpa"),
                    latitude=s.get("latitude"),
                    longitude=s.get("longitude"),
                )
                for s in payload.get("sites", [])
            ]
            self._peer_cache.update(snapshots)
            self._pull_backoff = self._settings.hub_pull_interval
        except Exception as exc:
            logger.warning(
                "Hub pull failed: {}; backoff={:.0f}s", exc, self._pull_backoff
            )
            self._pull_backoff = min(self._pull_backoff * 2, 60.0)
