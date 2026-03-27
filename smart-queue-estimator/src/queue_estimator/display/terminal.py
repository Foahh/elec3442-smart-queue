from __future__ import annotations

"""Terminal display fallback implementation."""

import sys
from typing import Literal

from queue_estimator.display.base import LEDDisplay


class TerminalDisplay(LEDDisplay):
    """ANSI terminal display for busyness level."""

    def show_level(self, level: Literal["green", "yellow", "red"]) -> None:
        """Print level with ANSI color on one terminal line."""

        color_map: dict[str, str] = {
            "green": "\033[32m",
            "yellow": "\033[33m",
            "red": "\033[31m",
        }
        block = f"{color_map[level]}█ {level.upper()}\033[0m"
        sys.stdout.write(f"\r\033[K{block}\n")
        sys.stdout.flush()

    def clear(self) -> None:
        """Clear terminal line."""

        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


class NoOpDisplay(LEDDisplay):
    """No-op display backend."""

    def show_level(self, level: Literal["green", "yellow", "red"]) -> None:
        """Ignore level updates."""

        _ = level

    def clear(self) -> None:
        """Ignore clear operations."""

