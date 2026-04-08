from __future__ import annotations

"""PiCamera2 source implementation."""

from typing import Any

import cv2
import numpy as np

from queue_estimator.camera.base import CameraSource
from queue_estimator.config import Settings


class PiCameraSource(CameraSource):
    """Camera source backed by Picamera2."""

    def __init__(self, settings: Settings) -> None:
        """Initialize Pi camera source."""

        self._settings = settings
        self._camera: Any | None = None

    def start(self) -> None:
        """Create and start picamera2 capture stream."""

        try:
            from picamera2 import Picamera2
        except ImportError as exc:
            raise RuntimeError(
                "picamera2 not installed — on Raspberry Pi run: pip install picamera2"
            ) from exc

        self._camera = Picamera2()
        config = self._camera.create_preview_configuration(
            main={
                "size": (self._settings.camera_width, self._settings.camera_height),
                "format": "XRGB8888",
            }
        )
        self._camera.configure(config)
        self._camera.start()

    def read_frame(self) -> np.ndarray | None:
        """Capture one frame and return BGR numpy image."""

        if self._camera is None:
            return None
        frame = self._camera.capture_array()
        if frame is None:
            return None
        if frame.ndim == 3 and frame.shape[2] == 4:
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        if frame.ndim == 3 and frame.shape[2] == 3:
            return frame
        return None

    def stop(self) -> None:
        """Stop camera stream."""

        if self._camera is not None:
            self._camera.stop()
            self._camera.close()
            self._camera = None
