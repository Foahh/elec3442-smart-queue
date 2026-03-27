from __future__ import annotations

"""Display implementations and factory."""

from queue_estimator.config import Settings
from queue_estimator.display.base import LEDDisplay
from queue_estimator.display.sensehat import SenseHATDisplay
from queue_estimator.display.terminal import NoOpDisplay, TerminalDisplay


def make_display(settings: Settings) -> LEDDisplay:
    """Return configured display implementation."""

    match settings.display_backend:
        case "sensehat":
            return SenseHATDisplay()
        case "terminal":
            return TerminalDisplay()
        case "none":
            return NoOpDisplay()
    return NoOpDisplay()

