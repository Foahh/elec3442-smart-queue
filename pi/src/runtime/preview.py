from __future__ import annotations

"""Preview rendering helpers."""

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import cv2
import numpy as np

from config import Settings

if TYPE_CHECKING:
    from detection.detector import DetectedPerson
    from runtime.shared_state import SharedState
    from schemas import QueueStatusResponse


@dataclass(slots=True)
class _PreviewJob:
    """Metadata for one preview frame; pixel data lives in `PreviewRenderer` ping-pong buffers."""

    buffer_idx: int
    input_color_space: str
    persons: list["DetectedPerson"]
    in_zone_persons: list["DetectedPerson"]
    frame_time: datetime
    status: "QueueStatusResponse"
    state: "SharedState"


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
        """Store preview-related settings and start background encoder."""

        self._settings = settings
        self._last_preview_encoded_at = 0.0
        self._pending_lock = threading.Lock()
        self._pending: _PreviewJob | None = None
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._buf_shape: tuple[int, int] | None = None
        self._bufs: tuple[np.ndarray, np.ndarray] | None = None
        self._bgr_scratch: np.ndarray | None = None
        ph = max(int(settings.preview_height), 1)
        pw = max(int(settings.preview_width), 1)
        self._resize_shape: tuple[int, int] = (ph, pw)
        self._resize_buf = np.empty((ph, pw, 3), dtype=np.uint8)
        self._consumer_busy_idx: int | None = None
        self._prod_flip: int = 0
        self._worker = threading.Thread(
            target=self._encode_worker,
            name="preview-encoder",
            daemon=True,
        )
        self._worker.start()

    def _ensure_buffers(self, h: int, w: int) -> None:
        """Allocate ping-pong frame storage and BGR scratch when capture size changes."""

        if h <= 0 or w <= 0:
            return
        if self._buf_shape == (h, w) and self._bufs is not None:
            return
        with self._pending_lock:
            if self._consumer_busy_idx is not None:
                return
            self._buf_shape = (h, w)
            self._bufs = (
                np.empty((h, w, 3), dtype=np.uint8, order="C"),
                np.empty((h, w, 3), dtype=np.uint8, order="C"),
            )
            self._bgr_scratch = np.empty((h, w, 3), dtype=np.uint8, order="C")
            self._prod_flip = 0

    def shutdown(self, *, timeout_s: float = 3.0) -> None:
        """Stop the encoder thread (blocks up to timeout_s)."""

        self._stop.set()
        self._wake.set()
        self._worker.join(timeout=timeout_s)

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
        """Queue a preview frame when clients are connected (non-blocking)."""

        if not self._should_encode(state):
            return

        fh, fw = int(frame.shape[0]), int(frame.shape[1])
        self._ensure_buffers(fh, fw)
        if self._bufs is None or self._buf_shape != (fh, fw):
            return

        with self._pending_lock:
            busy = self._consumer_busy_idx
            if busy is None:
                slot = int(self._prod_flip)
                self._prod_flip ^= 1
            else:
                slot = 1 - busy

        np.copyto(self._bufs[slot], frame)
        job = _PreviewJob(
            buffer_idx=slot,
            input_color_space=input_color_space,
            persons=persons,
            in_zone_persons=in_zone_persons,
            frame_time=frame_time,
            status=status,
            state=state,
        )
        with self._pending_lock:
            self._pending = job
        self._wake.set()

    def _encode_worker(self) -> None:
        while not self._stop.is_set():
            if not self._wake.wait(timeout=0.25):
                continue
            self._wake.clear()
            if self._stop.is_set():
                break
            with self._pending_lock:
                job = self._pending
                self._pending = None
            if job is None:
                continue
            with self._pending_lock:
                self._consumer_busy_idx = job.buffer_idx
            try:
                ok = self._encode_and_publish(job)
            finally:
                with self._pending_lock:
                    if self._consumer_busy_idx == job.buffer_idx:
                        self._consumer_busy_idx = None
            if ok:
                self._last_preview_encoded_at = time.monotonic()

    def _encode_and_publish(self, job: _PreviewJob) -> bool:
        if self._bufs is None or self._bgr_scratch is None:
            return False
        raw = self._bufs[job.buffer_idx]
        if job.input_color_space == "rgb":
            cv2.cvtColor(raw, cv2.COLOR_RGB2BGR, dst=self._bgr_scratch)
            vis_frame = self._bgr_scratch
        else:
            vis_frame = raw

        self._draw_roi_border(vis_frame)
        self._draw_zone(vis_frame)
        self._draw_persons(vis_frame, job.persons, job.in_zone_persons)
        self._draw_status_overlay(
            vis_frame,
            job.status,
            job.frame_time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        pw, ph = int(self._settings.preview_width), int(self._settings.preview_height)
        if self._resize_shape != (ph, pw):
            self._resize_shape = (ph, pw)
            self._resize_buf = np.empty((ph, pw, 3), dtype=np.uint8, order="C")

        cv2.resize(vis_frame, (pw, ph), dst=self._resize_buf)
        ok, buf = cv2.imencode(
            ".jpg",
            self._resize_buf,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                int(self._settings.preview_jpeg_quality),
            ],
        )
        if ok:
            job.state.set_preview_jpeg(buf.tobytes())
            return True
        return False

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
