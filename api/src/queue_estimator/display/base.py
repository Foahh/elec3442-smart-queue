from __future__ import annotations

"""Display abstraction."""

from abc import ABC, abstractmethod
from typing import NamedTuple


class SiteDisplay(NamedTuple):
    """Display data for one site on the LED matrix."""

    busyness_level: str   # "low" | "medium" | "high"
    queue_length: int
    stale: bool


class LEDDisplay(ABC):
    """Abstract display device API."""

    @abstractmethod
    def show_sites(self, sites: list[SiteDisplay]) -> None:
        """Render all sites as horizontal bands."""

    def show_level(self, level: str) -> None:
        """Convenience wrapper: render a single local site."""

        self.show_sites([SiteDisplay(busyness_level=level, queue_length=0, stale=False)])

    @abstractmethod
    def clear(self) -> None:
        """Clear display output."""
