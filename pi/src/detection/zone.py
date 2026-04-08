from __future__ import annotations

"""Queue zone polygon filtering."""

from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from detection.detector import DetectedPerson


class QueueZone:
    """Polygon queue zone with normalized coordinates."""

    def __init__(self, normalized_polygon: list[tuple[float, float]]) -> None:
        """Store normalized polygon points."""

        if len(normalized_polygon) < 3:
            raise ValueError("Queue zone polygon must contain at least 3 points")
        self._normalized_polygon = np.array(normalized_polygon, dtype=np.float32)

    def _to_pixel_polygon(self, frame_shape: tuple[int, int]) -> np.ndarray:
        """Convert normalized polygon to pixel coordinates."""

        height, width = frame_shape
        scaled = np.copy(self._normalized_polygon)
        scaled[:, 0] *= width
        scaled[:, 1] *= height
        return scaled.astype(np.float32)

    def contains(
        self, point_normalized: tuple[float, float], frame_shape: tuple[int, int]
    ) -> bool:
        """Return True if point is inside or on polygon boundary."""

        polygon = self._to_pixel_polygon(frame_shape)
        height, width = frame_shape
        px = float(point_normalized[0]) * width
        py = float(point_normalized[1]) * height
        result = cv2.pointPolygonTest(polygon, (px, py), False)
        return result >= 0

    def filter_persons(
        self,
        persons: list[DetectedPerson],
        frame_shape: tuple[int, int],
    ) -> list[DetectedPerson]:
        """Return only persons whose center is inside zone."""

        return [
            person for person in persons if self.contains(person.center, frame_shape)
        ]
