from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch
from ultralytics.engine.results import Boxes

from config import Settings
from detection.detector import PersonDetector


class _FakeYOLO:
    """Returns one person box as a real ultralytics Boxes tensor."""

    def __init__(self, model_path: str | Path) -> None:
        self.model_path = str(model_path)
        self.last_rgb_frame: np.ndarray | None = None

    def predict(self, source: Any, **kwargs: Any) -> list[Any]:
        assert isinstance(source, np.ndarray)
        self.last_rgb_frame = source
        data = torch.tensor([[10.0, 20.0, 110.0, 220.0, 0.9, 0.0]])
        boxes = Boxes(data, orig_shape=(source.shape[0], source.shape[1]))

        class _R:
            def __init__(self) -> None:
                self.boxes = boxes

        return [_R()]


class _FakeBYTETracker:
    """Mimics ultralytics BYTETracker.update(results, img=...) -> ndarray."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._next_id = 1

    def update(
        self,
        results: Boxes,
        img: np.ndarray | None = None,
        feats: np.ndarray | None = None,
    ) -> np.ndarray:
        if len(results) == 0:
            return np.empty((0, 8), dtype=np.float32)
        xyxy = results.xyxy[0]
        x1, y1, x2, y2 = (float(xyxy[i]) for i in range(4))
        tid = self._next_id
        self._next_id += 1
        conf = float(results.conf[0])
        cls_ = float(results.cls[0])
        idx = 0.0
        return np.array(
            [[x1, y1, x2, y2, tid, conf, cls_, idx]], dtype=np.float32
        )


def _make_model_dir(tmp_path: Path) -> None:
    (tmp_path / "yolo26n_ncnn_model").mkdir(parents=True)


def test_person_detector_converts_bgr_to_rgb(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import detection.detector as detmod

    monkeypatch.setattr(detmod, "YOLO", _FakeYOLO, raising=True)
    monkeypatch.setattr(detmod, "BYTETracker", _FakeBYTETracker, raising=True)

    _make_model_dir(tmp_path)
    settings = Settings(model_dir=tmp_path, yolo_model="yolo26n.pt")
    detector = PersonDetector(settings)

    frame_bgr = np.zeros((240, 320, 3), dtype=np.uint8)
    frame_bgr[0, 0] = np.array([255, 0, 0], dtype=np.uint8)  # blue in BGR

    persons = detector.detect(frame_bgr, input_color_space="bgr")

    fake_yolo = detector._model._model  # type: ignore[attr-defined]
    assert fake_yolo.last_rgb_frame is not None
    # BGR blue [255,0,0] → RGB [0,0,255]
    assert tuple(int(x) for x in fake_yolo.last_rgb_frame[0, 0]) == (0, 0, 255)

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

    _make_model_dir(tmp_path)
    settings = Settings(model_dir=tmp_path, yolo_model="yolo26n.pt")
    detector = PersonDetector(settings)

    bad = np.zeros((10, 10), dtype=np.uint8)
    assert detector.detect(bad, input_color_space="rgb") == []
