from __future__ import annotations

"""YOLO person detection and tracking."""

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Literal

import numpy as np
from loguru import logger
from ultralytics import YOLO
from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import BYTETracker

from config import Settings
from detection.model_path import resolve_model_path


@dataclass(slots=True)
class DetectedPerson:
    """Detected person output with tracking metadata."""

    track_id: int
    bbox_xyxy: tuple[float, float, float, float]
    confidence: float
    center: tuple[float, float]


def _tracker_args(settings: Settings) -> SimpleNamespace:
    """Build ByteTrack args compatible with ultralytics BYTETracker."""

    return SimpleNamespace(
        track_high_thresh=float(settings.yolo_confidence),
        track_low_thresh=0.1,
        new_track_thresh=float(settings.yolo_confidence),
        match_thresh=0.8,
        track_buffer=max(int(settings.camera_fps) * 2, 25),
        fuse_score=True,
    )


def _empty_boxes(h: int, w: int) -> Boxes:
    return Boxes(np.zeros((0, 6), dtype=np.float32), orig_shape=(h, w))


def _boxes_to_persons(boxes: np.ndarray, w0: int, h0: int) -> list[DetectedPerson]:
    """Convert BYTETracker.update() output rows to DetectedPerson list.

    Each row is xyxy (4), track_id, score, cls, idx (see STrack.result).
    """

    if boxes.size == 0:
        return []
    if boxes.ndim == 1:
        boxes = boxes.reshape(1, -1)
    persons: list[DetectedPerson] = []
    for row in boxes:
        x1, y1, x2, y2 = float(row[0]), float(row[1]), float(row[2]), float(row[3])
        tid = int(row[4])
        score = float(row[5])
        center_x = ((x1 + x2) / 2.0) / float(w0)
        center_y = ((y1 + y2) / 2.0) / float(h0)
        persons.append(
            DetectedPerson(
                track_id=tid,
                bbox_xyxy=(x1, y1, x2, y2),
                confidence=score,
                center=(center_x, center_y),
            )
        )
    return persons


class _UltralyticsNcnnPersonDetector:
    """Ultralytics YOLO (NCNN export) + Ultralytics ByteTrack."""

    def __init__(self, settings: Settings, model_dir: Path) -> None:
        self._settings = settings
        self._model = YOLO(str(model_dir))
        self._tracker = BYTETracker(
            _tracker_args(settings), frame_rate=max(int(settings.camera_fps), 1)
        )

    def detect(
        self, frame: np.ndarray, *, input_color_space: Literal["rgb", "bgr"]
    ) -> list[DetectedPerson]:
        if frame.ndim != 3 or frame.shape[2] != 3:
            return []
        h0, w0 = frame.shape[:2]
        rgb = frame if input_color_space == "rgb" else frame[:, :, ::-1]

        pred = self._model.predict(
            source=rgb,
            imgsz=int(self._settings.yolo_imgsz),
            conf=float(self._settings.yolo_confidence),
            iou=float(self._settings.yolo_iou),
            classes=[0],
            verbose=False,
        )[0]

        det_boxes = pred.boxes
        if det_boxes is None or len(det_boxes) == 0:
            det_boxes = _empty_boxes(h0, w0)

        tracked = self._tracker.update(det_boxes, img=rgb)
        return _boxes_to_persons(
            np.asarray(tracked, dtype=np.float32), w0=w0, h0=h0
        )


class PersonDetector:
    """Detector wrapper for YOLO tracking."""

    def __init__(self, settings: Settings) -> None:
        """Load NCNN export (Ultralytics) and prepare detector + tracker."""

        self._settings = settings
        settings.model_dir.mkdir(parents=True, exist_ok=True)
        model_path = resolve_model_path(settings)
        try:
            if model_path.exists():
                logger.info(
                    "Loading Ultralytics YOLO (NCNN) from {}", model_path
                )
                self._model = _UltralyticsNcnnPersonDetector(
                    settings=settings, model_dir=model_path
                )
            else:
                raise FileNotFoundError(
                    f"NCNN model directory not found: {model_path}. "
                    "Export with Ultralytics (yolo export format=ncnn), then copy "
                    "the `<stem>_ncnn_model/` folder into `models/`."
                )
        except (RuntimeError, ValueError, OSError, FileNotFoundError) as exc:
            logger.exception("Failed to load model from {}", model_path)
            raise RuntimeError(f"Failed to load model: {model_path}") from exc

    def detect(
        self, frame: np.ndarray, *, input_color_space: Literal["rgb", "bgr"]
    ) -> list[DetectedPerson]:
        """Run detection + ByteTrack and return tracked persons."""

        return self._model.detect(frame, input_color_space=input_color_space)
