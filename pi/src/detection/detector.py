from __future__ import annotations

"""YOLO person detection and tracking."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from loguru import logger

from config import Settings
from detection.model_path import resolve_model_path


@dataclass(slots=True)
class DetectedPerson:
    """Detected person output with tracking metadata."""

    track_id: int
    bbox_xyxy: tuple[float, float, float, float]
    confidence: float
    center: tuple[float, float]


def _iou_xyxy(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter = inter_w * inter_h
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    denom = area_a + area_b - inter
    if denom <= 0.0:
        return 0.0
    return inter / denom


def _nms_xyxy(
    boxes: list[tuple[float, float, float, float]],
    scores: list[float],
    iou_threshold: float,
) -> list[int]:
    """Return indices kept after greedy NMS."""

    if not boxes:
        return []
    order = sorted(range(len(boxes)), key=lambda i: scores[i], reverse=True)
    keep: list[int] = []
    while order:
        i = order.pop(0)
        keep.append(i)
        if not order:
            break
        remaining: list[int] = []
        for j in order:
            if _iou_xyxy(boxes[i], boxes[j]) <= iou_threshold:
                remaining.append(j)
        order = remaining
    return keep


class _NcnnYoloPersonDetector:
    """NCNN-only person detector for ultralytics-free deployments."""

    def __init__(self, settings: Settings, model_dir: Path) -> None:
        try:
            import ncnn  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "NCNN backend selected but `ncnn` Python package is missing. "
                "Install it (e.g. `pip install ncnn`)."
            ) from exc

        try:
            from pyxtrackers import BYTETracker  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "ByteTrack tracker is enabled but `pyxtrackers` is missing. "
                "Install it (e.g. `pip install pyxtrackers`)."
            ) from exc

        self._ncnn = ncnn
        self._settings = settings
        self._tracker = BYTETracker(
            track_thresh=float(settings.yolo_confidence),
            match_thresh=0.8,
            track_buffer=max(int(settings.camera_fps) * 2, 25),
        )

        param = model_dir / "model.ncnn.param"
        bin_ = model_dir / "model.ncnn.bin"
        if not param.exists() or not bin_.exists():
            raise FileNotFoundError(f"Missing NCNN files: {param} / {bin_}")

        self._net = ncnn.Net()
        self._net.load_param(str(param))
        self._net.load_model(str(bin_))

    def detect(self, frame: np.ndarray) -> list[DetectedPerson]:
        # Model expects RGB.
        img = frame
        if img.ndim != 3 or img.shape[2] != 3:
            return []
        h0, w0 = img.shape[:2]
        imgsz = int(self._settings.yolo_imgsz)

        rgb = img[:, :, ::-1]  # BGR -> RGB
        resized = _resize_letterbox(rgb, imgsz, imgsz)
        inp = resized.astype(np.float32) / 255.0

        # NCNN expects CHW.
        chw = np.transpose(inp, (2, 0, 1))
        with self._net.create_extractor() as ex:
            ex.input("in0", self._ncnn.Mat(chw).clone())
            _, out0 = ex.extract("out0")

        raw = np.array(out0, dtype=np.float32)
        # Typical shape: (8400, 84) = [cx,cy,w,h] + 80 class probs
        if raw.ndim == 1:
            # Some NCNN builds flatten; try to recover.
            raw = raw.reshape((-1, raw.shape[0]))
        if raw.shape[-1] < 5:
            return []

        boxes_xyxy: list[tuple[float, float, float, float]] = []
        scores: list[float] = []

        # Use class 0 (person). If the export includes an objectness score, it is usually at index 4.
        # This model appears to output class probabilities directly (sigmoid applied in graph).
        cls0_idx = 4  # first class prob starts at 4
        if raw.shape[1] >= 85:
            cls0_idx = 5  # [cx,cy,w,h,obj] + classes

        for row in raw:
            cx, cy, w, h = float(row[0]), float(row[1]), float(row[2]), float(row[3])
            score = float(row[cls0_idx])
            if score < self._settings.yolo_confidence:
                continue
            x1 = cx - w / 2.0
            y1 = cy - h / 2.0
            x2 = cx + w / 2.0
            y2 = cy + h / 2.0

            # Undo letterbox back to original frame coordinates.
            x1, y1, x2, y2 = _unletterbox_xyxy(x1, y1, x2, y2, w0, h0, imgsz, imgsz)
            boxes_xyxy.append((x1, y1, x2, y2))
            scores.append(score)

        keep = _nms_xyxy(
            boxes_xyxy, scores, iou_threshold=float(self._settings.yolo_iou)
        )
        kept_boxes = [boxes_xyxy[i] for i in keep]
        kept_scores = [scores[i] for i in keep]
        if not kept_boxes:
            tracked = self._tracker.update(np.empty((0, 5), dtype=np.float64))
        else:
            dets = np.array(
                [
                    [x1, y1, x2, y2, s]
                    for (x1, y1, x2, y2), s in zip(
                        kept_boxes, kept_scores, strict=False
                    )
                ],
                dtype=np.float64,
            )
            tracked = self._tracker.update(dets)

        persons: list[DetectedPerson] = []
        if tracked is None or len(tracked) == 0:
            return persons

        # pyxtrackers returns: [[x1, y1, x2, y2, track_id], ...]
        for row in np.asarray(tracked):
            x1, y1, x2, y2, tid = row[:5]
            if np.isnan(x1) or np.isnan(y1) or np.isnan(x2) or np.isnan(y2):
                continue
            center_x = ((float(x1) + float(x2)) / 2.0) / float(w0)
            center_y = ((float(y1) + float(y2)) / 2.0) / float(h0)
            persons.append(
                DetectedPerson(
                    track_id=int(tid),
                    bbox_xyxy=(float(x1), float(y1), float(x2), float(y2)),
                    confidence=1.0,
                    center=(float(center_x), float(center_y)),
                )
            )
        return persons


def _resize_letterbox(rgb: np.ndarray, new_w: int, new_h: int) -> np.ndarray:
    """Resize with letterbox padding to preserve aspect ratio."""
    import cv2

    h, w = rgb.shape[:2]
    scale = min(new_w / float(w), new_h / float(h))
    rw, rh = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(rgb, (rw, rh), interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((new_h, new_w, 3), dtype=resized.dtype)
    pad_x = (new_w - rw) // 2
    pad_y = (new_h - rh) // 2
    canvas[pad_y : pad_y + rh, pad_x : pad_x + rw] = resized
    return canvas


def _unletterbox_xyxy(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    orig_w: int,
    orig_h: int,
    net_w: int,
    net_h: int,
) -> tuple[float, float, float, float]:
    scale = min(net_w / float(orig_w), net_h / float(orig_h))
    rw, rh = orig_w * scale, orig_h * scale
    pad_x = (net_w - rw) / 2.0
    pad_y = (net_h - rh) / 2.0
    x1 = (x1 - pad_x) / scale
    x2 = (x2 - pad_x) / scale
    y1 = (y1 - pad_y) / scale
    y2 = (y2 - pad_y) / scale
    # clamp
    x1 = max(0.0, min(float(orig_w - 1), x1))
    x2 = max(0.0, min(float(orig_w - 1), x2))
    y1 = max(0.0, min(float(orig_h - 1), y1))
    y2 = max(0.0, min(float(orig_h - 1), y2))
    return x1, y1, x2, y2


class PersonDetector:
    """Detector wrapper for YOLO tracking."""

    def __init__(self, settings: Settings) -> None:
        """Load NCNN model and prepare detector."""

        self._settings = settings
        settings.model_dir.mkdir(parents=True, exist_ok=True)
        model_path = resolve_model_path(settings)
        try:
            if model_path.exists():
                logger.info("Loading NCNN model via ncnn runtime from {}", model_path)
                self._model = _NcnnYoloPersonDetector(
                    settings=settings, model_dir=model_path
                )
            else:
                raise FileNotFoundError(
                    f"NCNN model directory not found: {model_path}. "
                    "Export/convert the model to NCNN first, then copy the generated "
                    "`<model_stem>_ncnn_model/` folder into `models/`."
                )
        except (RuntimeError, ValueError, OSError, FileNotFoundError) as exc:
            logger.exception("Failed to load model from {}", model_path)
            raise RuntimeError(f"Failed to load model: {model_path}") from exc

    def detect(self, frame: np.ndarray) -> list[DetectedPerson]:
        """Run detection + lightweight tracking and return tracked persons."""

        return self._model.detect(frame)
