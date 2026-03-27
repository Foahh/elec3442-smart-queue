from __future__ import annotations

"""Display implementations and factory."""

from queue_estimator.display.base import LEDDisplay
from queue_estimator.display.sensehat import SenseHATDisplay


def make_display() -> LEDDisplay:
    """Return Sense HAT display implementation."""

    return SenseHATDisplay()

