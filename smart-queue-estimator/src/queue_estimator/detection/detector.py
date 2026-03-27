from __future__ import annotations

"""YOLO person detection and tracking."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from loguru import logger
from ultralytics import YOLO

from queue_estimator.config import Settings
from queue_estimator.detection.model_path import resolve_model_path


@dataclass(slots=True)
class DetectedPerson:
    """Detected person output with tracking metadata."""

    track_id: int
    bbox_xyxy: tuple[float, float, float, float]
    confidence: float
    center: tuple[float, float]


class PersonDetector:
    """Detector wrapper for YOLO tracking."""

    def __init__(self, settings: Settings) -> None:
        """Load YOLO model and prepare detector."""

        self._settings = settings
        settings.model_dir.mkdir(parents=True, exist_ok=True)
        model_path = resolve_model_path(settings)
        try:
            if model_path.exists():
                logger.info("Loading NCNN model from {}", model_path)
                self._model = YOLO(str(model_path))
            else:
                raise FileNotFoundError(
                    f"NCNN model directory not found: {model_path}. "
                    "Export first with: yolo export model=yolo26n.pt format=ncnn"
                )
        except (RuntimeError, ValueError, OSError, FileNotFoundError) as exc:
            logger.exception("Failed to load model from {}", model_path)
            raise RuntimeError(f"Failed to load model: {model_path}") from exc

    def detect(self, frame: np.ndarray) -> list[DetectedPerson]:
        """Run tracking and return detected tracked persons."""

        height, width = frame.shape[:2]
        results = self._model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            conf=self._settings.yolo_confidence,
            iou=self._settings.yolo_iou,
            imgsz=self._settings.yolo_imgsz,
            verbose=False,
        )
        if not results:
            return []

        result = results[0]
        boxes = result.boxes
        if boxes is None or boxes.xyxy is None:
            return []

        persons: list[DetectedPerson] = []
        ids = boxes.id
        for idx in range(len(boxes.xyxy)):
            if boxes.conf is None or boxes.cls is None:
                continue
            confidence = float(boxes.conf[idx].item())
            if confidence < self._settings.yolo_confidence:
                continue
            class_id = int(boxes.cls[idx].item())
            if class_id != 0:
                continue

            track_id: int | None = None
            if ids is not None:
                maybe_id = ids[idx].item()
                if maybe_id is not None:
                    track_id = int(maybe_id)
            if track_id is None:
                logger.warning("Track ID missing for a person detection; skipping frame entry")
                continue

            x1, y1, x2, y2 = boxes.xyxy[idx].tolist()
            center_x = ((x1 + x2) / 2.0) / float(width)
            center_y = ((y1 + y2) / 2.0) / float(height)
            persons.append(
                DetectedPerson(
                    track_id=track_id,
                    bbox_xyxy=(float(x1), float(y1), float(x2), float(y2)),
                    confidence=confidence,
                    center=(center_x, center_y),
                )
            )
        return persons

