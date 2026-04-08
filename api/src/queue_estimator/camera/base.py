from __future__ import annotations

"""Abstract camera source."""

from abc import ABC, abstractmethod

import numpy as np


class CameraSource(ABC):
    """Abstract camera source contract."""

    @abstractmethod
    def start(self) -> None:
        """Start the camera resource."""

    @abstractmethod
    def read_frame(self) -> np.ndarray | None:
        """Return a BGR frame or None on failure."""

    @abstractmethod
    def stop(self) -> None:
        """Stop and release camera resource."""

    def __enter__(self) -> CameraSource:
        """Context manager enter."""

        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        """Context manager exit."""

        self.stop()
