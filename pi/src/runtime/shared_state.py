from __future__ import annotations

"""Thread-safe runtime state shared across background services."""

import threading

from schemas import QueueStatusResponse, SensorReading


class SharedState:
    """Thread-safe wrapper around latest queue status and preview data."""

    def __init__(self) -> None:
        """Initialize shared runtime state."""

        self._lock = threading.Lock()
        self._status: QueueStatusResponse | None = None
        self._preview_jpeg: bytes | None = None
        self._sensors: SensorReading | None = None
        self._preview_clients: int = 0

    def update(self, status: QueueStatusResponse) -> None:
        """Store latest queue status."""

        with self._lock:
            self._status = status

    def get(self) -> QueueStatusResponse | None:
        """Return latest queue status if available."""

        with self._lock:
            return self._status

    def set_preview_jpeg(self, data: bytes) -> None:
        """Store latest encoded preview frame."""

        with self._lock:
            self._preview_jpeg = data

    def get_preview_jpeg(self) -> bytes | None:
        """Return latest preview JPEG bytes if available."""

        with self._lock:
            return self._preview_jpeg

    def preview_client_connected(self) -> None:
        """Increment connected preview client count."""

        with self._lock:
            self._preview_clients += 1

    def preview_client_disconnected(self) -> None:
        """Decrement connected preview client count."""

        with self._lock:
            self._preview_clients = max(0, self._preview_clients - 1)

    def preview_client_count(self) -> int:
        """Return connected preview client count."""

        with self._lock:
            return self._preview_clients

    def update_sensors(self, sensors: SensorReading) -> None:
        """Store latest sensor reading."""

        with self._lock:
            self._sensors = sensors

    def get_sensors(self) -> SensorReading | None:
        """Return latest sensor reading if available."""

        with self._lock:
            return self._sensors
