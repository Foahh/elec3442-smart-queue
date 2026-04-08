from __future__ import annotations

"""Display implementations and factory."""

from loguru import logger

from queue_estimator.display.base import LEDDisplay, SiteDisplay
from queue_estimator.display.sensehat import SenseHATDisplay


class NullDisplay(LEDDisplay):
    """No-op display used when Sense HAT is unavailable."""

    def show_sites(self, sites: list[SiteDisplay]) -> None:  # noqa: ARG002
        pass

    def clear(self) -> None:
        pass


def make_display(queue_max_display: int = 16) -> LEDDisplay:
    """Return Sense HAT display, or no-op fallback on dev machines."""

    try:
        return SenseHATDisplay(queue_max_display=queue_max_display)
    except RuntimeError as exc:
        logger.warning("Sense HAT disabled for this environment: {}", exc)
        return NullDisplay()
