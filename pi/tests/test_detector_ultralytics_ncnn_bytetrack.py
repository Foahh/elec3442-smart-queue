from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from config import Settings
from detection.detector import PersonDetector


@dataclass
class _FakeBoxes:
    """Mimic ultralytics Results.boxes API surface we need."""

    xyxy: np.ndarray  # shape (N, 4)
    conf: np.ndarray  # shape (N,)
    cls: np.ndarray  # shape (N,)


class _FakeResult:
    def __init__(self, boxes: _FakeBoxes) -> None:
        self.boxes = boxes


class _FakeYOLO:
    def __init__(self, model_path: str | Path) -> None:
        self.model_path = str(model_path)

    def __call__(self, rgb_frame: np.ndarray, **kwargs: Any) -> list[_FakeResult]:
        boxes = _FakeBoxes(
            xyxy=np.array([[10.0, 20.0, 110.0, 220.0]], dtype=np.float32),
            conf=np.array([0.9], dtype=np.float32),
            cls=np.array([0.0], dtype=np.float32),  # person class
        )
        return [_FakeResult(boxes)]


class _FakeSTrack:
    def __init__(self, track_id: int, xyxy: np.ndarray, score: float) -> None:
        self.track_id = track_id
        self.xyxy = xyxy
        self.score = score


class _FakeBYTETracker:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._next_id = 1

    def update(
        self, dets: np.ndarray, img_size: tuple[int, int], **kwargs: Any
    ) -> list[_FakeSTrack]:
        if dets.size == 0:
            return []
        xyxy = dets[0, :4].astype(np.float32)
        score = float(dets[0, 4])
        tid = self._next_id
        self._next_id += 1
        return [_FakeSTrack(tid, xyxy, score)]


def test_person_detector_converts_bgr_to_rgb(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import detection.detector as detmod

    monkeypatch.setattr(detmod, "YOLO", _FakeYOLO, raising=True)
    monkeypatch.setattr(detmod, "BYTETracker", _FakeBYTETracker, raising=True)

    settings = Settings(model_dir=tmp_path, yolo_model="yolo26n.pt")
    detector = PersonDetector(settings)

    frame_bgr = np.zeros((240, 320, 3), dtype=np.uint8)
    frame_bgr[0, 0] = np.array([255, 0, 0], dtype=np.uint8)  # blue in BGR

    persons = detector.detect(frame_bgr, input_color_space="bgr")

    assert len(persons) == 1
    assert persons[0].track_id == 1
    assert persons[0].bbox_xyxy == (10.0, 20.0, 110.0, 220.0)
    assert persons[0].confidence == pytest.approx(0.9)
    assert persons[0].center[0] == pytest.approx(0.1875)
    assert persons[0].center[1] == pytest.approx(0.5)


def test_person_detector_returns_empty_on_invalid_frame(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import detection.detector as detmod

    monkeypatch.setattr(detmod, "YOLO", _FakeYOLO, raising=True)
    monkeypatch.setattr(detmod, "BYTETracker", _FakeBYTETracker, raising=True)

    settings = Settings(model_dir=tmp_path, yolo_model="yolo26n.pt")
    detector = PersonDetector(settings)

    bad = np.zeros((10, 10), dtype=np.uint8)
    assert detector.detect(bad, input_color_space="rgb") == []
