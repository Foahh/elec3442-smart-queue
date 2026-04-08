from __future__ import annotations

"""Camera implementations and factory."""

from camera.base import CameraSource
from camera.picamera import PiCameraSource
from camera.video import VideoFileSource
from camera.webcam import WebcamSource
from config import Settings


def make_camera(settings: Settings) -> CameraSource:
    """Return camera implementation for current settings."""

    if settings.camera_source == "picamera":
        return PiCameraSource(settings)
    if settings.camera_source == "video":
        return VideoFileSource(settings)
    return WebcamSource(settings)
