from __future__ import annotations

"""Rolling wait time estimation."""

from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Literal

from config import Settings
from db_models import PersonEvent


class WaitTimeEstimator:
    """Estimate throughput and wait time from completed events."""

    def __init__(self, settings: Settings) -> None:
        """Initialize estimator with rolling event window."""

        self._settings = settings
        self._events: deque[PersonEvent] = deque()
        self._bootstrap_throughput_per_minute: float = 0.0

    def add_event(self, event: PersonEvent) -> None:
        """Add completed person event and prune old events."""

        self._events.append(event)
        self._prune()

    def reset(self, *, preserve_throughput: bool = False) -> None:
        """Clear rolling statistics and optionally keep a bootstrap throughput."""

        if preserve_throughput:
            self._bootstrap_throughput_per_minute = self._compute_throughput_from_events()
        else:
            self._bootstrap_throughput_per_minute = 0.0
        self._events.clear()

    def _prune(self) -> None:
        """Prune events outside configured rolling window."""

        if not self._events:
            return
        cutoff = datetime.now(UTC) - timedelta(
            minutes=self._settings.throughput_window_minutes
        )
        while self._events and self._events[0].exit_time < cutoff:
            self._events.popleft()

    def _compute_throughput_from_events(self) -> float:
        """Compute throughput using current event deque only."""

        if not self._events or len(self._events) < 2:
            return 0.0

        window_minutes = float(self._settings.throughput_window_minutes)
        if window_minutes <= 0:
            return 0.0

        span_seconds = (
            self._events[-1].exit_time - self._events[0].exit_time
        ).total_seconds()
        if span_seconds <= 0:
            return 0.0

        effective_minutes = min(window_minutes, span_seconds / 60.0)
        if effective_minutes <= 0.0:
            return 0.0

        return float(len(self._events)) / effective_minutes

    @property
    def throughput_per_minute(self) -> float:
        """Return rolling throughput in persons per minute."""

        self._prune()
        throughput = self._compute_throughput_from_events()
        if throughput > 0.0:
            self._bootstrap_throughput_per_minute = throughput
            return throughput
        return self._bootstrap_throughput_per_minute

    def estimate_wait_seconds(self, queue_length: int) -> float:
        """Estimate queue wait time in seconds."""

        if queue_length <= 0:
            return 0.0

        throughput = self.throughput_per_minute
        if throughput <= 0.0:
            # Let caller-side floor logic (observed dwell) drive early estimates.
            return 0.0

        wait_seconds = (float(queue_length) / throughput) * 60.0
        return min(wait_seconds, self._settings.max_wait_seconds)

    def busyness_level(self, queue_length: int) -> Literal["low", "medium", "high"]:
        """Map queue length to busyness level."""

        if queue_length <= self._settings.led_green_max:
            return "low"
        if queue_length <= self._settings.led_yellow_max:
            return "medium"
        return "high"
