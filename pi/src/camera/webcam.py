from __future__ import annotations

"""OpenCV webcam implementation."""

import cv2
import numpy as np
from loguru import logger

from camera.base import CameraSource
from config import Settings


class WebcamSource(CameraSource):
    """Webcam camera source using OpenCV VideoCapture."""

    def __init__(self, settings: Settings) -> None:
        """Initialize webcam source."""

        self._settings = settings
        self._capture: cv2.VideoCapture | None = None

    def start(self) -> None:
        """Open camera device and apply resolution."""

        self._capture = cv2.VideoCapture(self._settings.camera_index)
        if not self._capture.isOpened():
            raise RuntimeError(
                f"Unable to open webcam index {self._settings.camera_index}"
            )
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(self._settings.camera_width))
        self._capture.set(
            cv2.CAP_PROP_FRAME_HEIGHT, float(self._settings.camera_height)
        )

    def read_frame(self) -> np.ndarray | None:
        """Read one frame from webcam."""

        if self._capture is None:
            return None
        ok, frame = self._capture.read()
        if not ok:
            logger.warning("Failed to read frame from webcam")
            return None
        return frame

    def stop(self) -> None:
        """Release webcam resource."""

        if self._capture is not None:
            self._capture.release()
            self._capture = None
