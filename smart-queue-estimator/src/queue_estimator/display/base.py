from __future__ import annotations

"""Display abstraction."""

from abc import ABC, abstractmethod
from typing import Literal


class LEDDisplay(ABC):
    """Abstract display device API."""

    @abstractmethod
    def show_level(self, level: Literal["green", "yellow", "red"]) -> None:
        """Render busyness level."""

    @abstractmethod
    def clear(self) -> None:
        """Clear display output."""

