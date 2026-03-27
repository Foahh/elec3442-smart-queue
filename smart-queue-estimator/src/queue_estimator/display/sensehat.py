from __future__ import annotations

"""Sense HAT display implementation."""

from typing import Literal

from queue_estimator.display.base import LEDDisplay


class SenseHATDisplay(LEDDisplay):
    """Sense HAT LED matrix display."""

    def __init__(self) -> None:
        """Initialize Sense HAT instance."""

        try:
            from sense_hat import SenseHat
        except ImportError as exc:
            raise RuntimeError("sense-hat not installed — run: uv sync --extra pi") from exc
        self._sense = SenseHat()

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

