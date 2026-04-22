from __future__ import annotations

"""Abstract camera source."""

from abc import ABC, abstractmethod
from typing import Literal

import numpy as np


class CameraSource(ABC):
    """Abstract camera source contract."""

    @property
    @abstractmethod
    def color_space(self) -> Literal["rgb", "bgr"]:
        """Color channel order of frames returned by read_frame()."""

    @abstractmethod
    def start(self) -> None:
        """Start the camera resource."""

    @abstractmethod
    def read_frame(self) -> np.ndarray | None:
        """Return a frame or None on failure."""

    @abstractmethod
    def stop(self) -> None:
        """Stop and release camera resource."""

    def poll_rewound(self) -> bool:
        """Return True once when input stream rewinds to the beginning."""

        return False

    def __enter__(self) -> CameraSource:
        """Context manager enter."""

        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        """Context manager exit."""

        self.stop()
