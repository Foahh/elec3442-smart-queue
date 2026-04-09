from __future__ import annotations

from config import Settings
from detection.model_path import resolve_model_path


def test_resolve_model_path_appends_ncnn_model(tmp_path) -> None:
    settings = Settings(model_dir=tmp_path, yolo_model="yolo26n.pt")
    assert resolve_model_path(settings) == tmp_path / "yolo26n_ncnn_model"


def test_resolve_model_path_strips_pt_suffix_only(tmp_path) -> None:
    settings = Settings(model_dir=tmp_path, yolo_model="yolo26n.pt.pt")
    assert resolve_model_path(settings) == tmp_path / "yolo26n.pt_ncnn_model"

