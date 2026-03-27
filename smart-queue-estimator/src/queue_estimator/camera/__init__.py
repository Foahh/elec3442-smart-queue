from __future__ import annotations

"""Camera implementations and factory."""

from queue_estimator.camera.base import CameraSource
from queue_estimator.camera.picamera import PiCameraSource
from queue_estimator.camera.video import VideoFileSource
from queue_estimator.camera.webcam import WebcamSource
from queue_estimator.config import Settings


def make_camera(settings: Settings) -> CameraSource:
    """Return camera implementation for current settings."""

    if settings.camera_source == "picamera":
        return PiCameraSource(settings)
    if settings.camera_source == "video":
        return VideoFileSource(settings)
    return WebcamSource(settings)

