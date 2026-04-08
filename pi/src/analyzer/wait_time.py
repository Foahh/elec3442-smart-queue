from __future__ import annotations

"""Rolling wait time estimation."""

from collections import deque
from datetime import timedelta
from typing import Literal

from config import Settings
from db_models import PersonEvent


class WaitTimeEstimator:
    """Estimate throughput and wait time from completed events."""

    def __init__(self, settings: Settings) -> None:
        """Initialize estimator with rolling event window."""

        self._settings = settings
        self._events: deque[PersonEvent] = deque()

    def add_event(self, event: PersonEvent) -> None:
        """Add completed person event and prune old events."""

        self._events.append(event)
        self._prune()

    def _prune(self) -> None:
        """Prune events outside configured rolling window."""

        if not self._events:
            return
        cutoff = self._events[-1].exit_time - timedelta(
            minutes=self._settings.throughput_window_minutes
        )
        while self._events and self._events[0].exit_time < cutoff:
            self._events.popleft()

    @property
    def throughput_per_minute(self) -> float:
        """Return rolling throughput in persons per minute."""

        if not self._events:
            return 0.0
        window_minutes = float(self._settings.throughput_window_minutes)
        if window_minutes <= 0:
            return 0.0
        return float(len(self._events)) / window_minutes

    def estimate_wait_seconds(self, queue_length: int) -> float:
        """Estimate queue wait time in seconds."""

        throughput = self.throughput_per_minute
        if throughput <= 0.0:
            return self._settings.max_wait_seconds
        return (float(queue_length) / throughput) * 60.0

    def busyness_level(self, queue_length: int) -> Literal["low", "medium", "high"]:
        """Map queue length to busyness level."""

        if queue_length <= self._settings.led_green_max:
            return "low"
        if queue_length <= self._settings.led_yellow_max:
            return "medium"
        return "high"
