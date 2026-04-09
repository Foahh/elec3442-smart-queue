from __future__ import annotations

"""OpenCV video file source implementation."""

from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from camera.base import CameraSource
from config import Settings


class VideoFileSource(CameraSource):
    """Video file source using OpenCV VideoCapture.

    The stream rewinds to frame 0 when it reaches EOF so the estimator can
    continue running for demos.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize video source."""

        self._settings = settings
        self._capture: cv2.VideoCapture | None = None

    @property
    def color_space(self):  # type: ignore[override]
        return "bgr"

    def start(self) -> None:
        """Open configured video file."""

        if not self._settings.camera_video_path:
            raise RuntimeError(
                "QE_CAMERA_VIDEO_PATH must be set when QE_CAMERA_SOURCE=video"
            )

        video_path = Path(self._settings.camera_video_path)
        if not video_path.exists():
            raise RuntimeError(f"Video file not found: {video_path}")

        self._capture = cv2.VideoCapture(str(video_path))
        if not self._capture.isOpened():
            raise RuntimeError(f"Unable to open video file: {video_path}")

    def read_frame(self) -> np.ndarray | None:
        """Read one frame and loop back to start at EOF."""

        if self._capture is None:
            return None

        ok, frame = self._capture.read()
        if ok:
            return frame

        # For file inputs, restart from the beginning to keep service alive.
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = self._capture.read()
        if ok:
            return frame

        logger.warning("Failed to read frame from video file")
        return None

    def stop(self) -> None:
        """Release video resource."""

        if self._capture is not None:
            self._capture.release()
            self._capture = None
