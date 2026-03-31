from __future__ import annotations

"""Sense HAT display implementation."""

from importlib import import_module
from typing import Literal

from queue_estimator.display.base import LEDDisplay


class SenseHATDisplay(LEDDisplay):
    """Sense HAT LED matrix display."""

    def __init__(self) -> None:
        """Initialize Sense HAT instance."""

        try:
            sense_hat_module = import_module("sense_hat")
            sense_hat_cls = getattr(sense_hat_module, "SenseHat")
        except ImportError as exc:
            raise RuntimeError(
                "Sense HAT library not installed — on Raspberry Pi: pip install sense-hat"
            ) from exc
        self._sense = sense_hat_cls()

    def show_level(self, level: Literal["green", "yellow", "red"]) -> None:
        """Fill 8x8 matrix with level color."""

        color_map: dict[str, tuple[int, int, int]] = {
            "green": (0, 180, 0),
            "yellow": (200, 180, 0),
            "red": (200, 0, 0),
        }
        self._sense.clear(color_map[level])

    def clear(self) -> None:
        """Clear Sense HAT matrix."""

        self._sense.clear()

