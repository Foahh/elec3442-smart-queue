from __future__ import annotations

"""Application bootstrap for the queue estimator runtime."""

import threading

from loguru import logger

from config import Settings
from database import create_db_and_tables
from hub_sync import HubSyncAgent, PeerCache
from preview_server import create_preview_http_server
from runtime.camera_loop import camera_loop
from runtime.shared_state import SharedState


class QueueEstimatorApplication:
    """Bootstrap background services and run the camera loop."""

    def __init__(self, settings: Settings) -> None:
        """Store application settings."""

        self._settings = settings

    def run(self) -> None:
        """Run the queue estimator runtime."""

        logger.info(
            "Open http://127.0.0.1:{}/preview for local video preview",
            self._settings.api_port,
        )
        create_db_and_tables()

        shared_state = SharedState()
        peer_cache = PeerCache()
        self._start_hub_sync(shared_state, peer_cache)

        preview_http_server = create_preview_http_server(
            self._settings.api_host,
            self._settings.api_port,
            shared_state,
        )
        preview_http_thread = threading.Thread(
            target=preview_http_server.serve_forever,
            daemon=True,
            name="preview-http-thread",
        )
        preview_http_thread.start()
        logger.info(
            "Preview server listening on http://{}:{}",
            self._settings.api_host,
            self._settings.api_port,
        )
        try:
            camera_loop(self._settings, shared_state, peer_cache)
        finally:
            preview_http_server.shutdown()
            preview_http_server.server_close()

    def _start_hub_sync(self, shared_state: SharedState, peer_cache: PeerCache) -> None:
        if not self._settings.hub_url:
            logger.info("QE_HUB_URL not set — hub sync disabled")
            return

        sync_agent = HubSyncAgent(self._settings, shared_state, peer_cache)
        sync_thread = threading.Thread(
            target=sync_agent.run,
            daemon=True,
            name="hub-sync-thread",
        )
        sync_thread.start()
        logger.info("Hub sync started → {}", self._settings.hub_url)
