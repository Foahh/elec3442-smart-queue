from __future__ import annotations

"""Preview rendering helpers."""

import time
from datetime import datetime
from typing import TYPE_CHECKING

import cv2
import numpy as np

from config import Settings

if TYPE_CHECKING:
    from detection.detector import DetectedPerson
    from runtime.shared_state import SharedState
    from schemas import QueueStatusResponse


def humanize_wait(seconds: float) -> str:
    """Convert seconds to approximate human-readable text."""

    total = max(int(seconds), 0)
    minutes, rem_seconds = divmod(total, 60)
    return f"~{minutes} min {rem_seconds} sec"


def center_square_crop(frame: np.ndarray) -> np.ndarray:
    """Return a center-cropped 1:1 square image."""

    h, w = frame.shape[:2]
    size = int(min(h, w))
    if size <= 0:
        return frame
    x0 = (w - size) // 2
    y0 = (h - size) // 2
    return frame[y0 : y0 + size, x0 : x0 + size]


def zone_polygon_pixels(
    zone_points_normalized: list[tuple[float, float]],
    frame_shape: tuple[int, int],
) -> np.ndarray | None:
    """Convert normalized zone polygon points to pixel coordinates."""

    if not zone_points_normalized or len(zone_points_normalized) < 3:
        return None
    h, w = frame_shape
    pts = np.array(zone_points_normalized, dtype=np.float32)
    pts[:, 0] *= float(w)
    pts[:, 1] *= float(h)
    return pts.reshape((-1, 1, 2)).astype(np.int32)


class PreviewRenderer:
    """Render annotated preview frames and cache JPEG output."""

    def __init__(self, settings: Settings) -> None:
        """Store preview-related settings."""

        self._settings = settings
        self._last_preview_encoded_at = 0.0

    def maybe_encode(
        self,
        *,
        state: "SharedState",
        frame: np.ndarray,
        input_color_space: str,
        persons: list["DetectedPerson"],
        in_zone_persons: list["DetectedPerson"],
        frame_time: datetime,
        status: "QueueStatusResponse",
    ) -> None:
        """Encode and publish a preview frame when clients are connected."""

        if not self._should_encode(state):
            return

        vis_frame = (
            cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            if input_color_space == "rgb"
            else frame.copy()
        )
        self._draw_roi_border(vis_frame)
        self._draw_zone(vis_frame)
        self._draw_persons(vis_frame, persons, in_zone_persons)
        self._draw_status_overlay(
            vis_frame,
            status,
            frame_time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        resized_frame = cv2.resize(
            vis_frame,
            (int(self._settings.preview_width), int(self._settings.preview_height)),
        )
        ok, buf = cv2.imencode(
            ".jpg",
            resized_frame,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                int(self._settings.preview_jpeg_quality),
            ],
        )
        if ok:
            state.set_preview_jpeg(buf.tobytes())
            self._last_preview_encoded_at = time.monotonic()

    def _should_encode(self, state: "SharedState") -> bool:
        if not self._settings.preview_enabled:
            return False
        if state.preview_client_count() <= 0:
            return False
        interval = 1.0 / max(int(self._settings.preview_fps), 1)
        return (time.monotonic() - self._last_preview_encoded_at) >= interval

    @staticmethod
    def _draw_roi_border(vis_frame: np.ndarray) -> None:
        h_vis, w_vis = vis_frame.shape[:2]
        cv2.rectangle(
            vis_frame,
            (0, 0),
            (max(w_vis - 1, 0), max(h_vis - 1, 0)),
            color=(255, 0, 255),
            thickness=2,
        )

    def _draw_zone(self, vis_frame: np.ndarray) -> None:
        zone_pts = zone_polygon_pixels(self._settings.queue_zone, vis_frame.shape[:2])
        if zone_pts is not None:
            cv2.polylines(
                vis_frame,
                [zone_pts],
                True,
                color=(0, 255, 255),
                thickness=2,
            )

    @staticmethod
    def _draw_persons(
        vis_frame: np.ndarray,
        persons: list["DetectedPerson"],
        in_zone_persons: list["DetectedPerson"],
    ) -> None:
        in_zone_track_ids = {person.track_id for person in in_zone_persons}
        for person in persons:
            x1, y1, x2, y2 = [int(coord) for coord in person.bbox_xyxy]
            color = (0, 255, 0) if person.track_id in in_zone_track_ids else (0, 0, 255)
            cv2.rectangle(
                vis_frame,
                (x1, y1),
                (x2, y2),
                color=color,
                thickness=2,
            )
            cv2.putText(
                vis_frame,
                f"ID {person.track_id}",
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

    @staticmethod
    def _draw_status_overlay(
        vis_frame: np.ndarray,
        status: "QueueStatusResponse",
        frame_timestamp: str,
    ) -> None:
        status_text = (
            f"Queue: {status.queue_length} | Wait: {status.estimated_wait_seconds:.0f}s | "
            f"Level: {status.busyness_level.upper()} | FPS: {status.effective_fps:.1f}"
        )
        cv2.putText(
            vis_frame,
            status_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            vis_frame,
            frame_timestamp,
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
