from __future__ import annotations

"""Display implementations and factory."""

from typing import Literal

from loguru import logger

from queue_estimator.display.base import LEDDisplay
from queue_estimator.display.sensehat import SenseHATDisplay


class NullDisplay(LEDDisplay):
    """No-op display used when Sense HAT is unavailable."""

    def show_level(self, level: Literal["green", "yellow", "red"]) -> None:
        """Ignore display updates on unsupported environments."""
        pass

    def clear(self) -> None:
        """Ignore display clear on unsupported environments."""
        pass


def make_display() -> LEDDisplay:
    """Return Sense HAT display, or no-op fallback on dev machines."""

    try:
        return SenseHATDisplay()
    except RuntimeError as exc:
        logger.warning("Sense HAT disabled for this environment: {}", exc)
        return NullDisplay()

