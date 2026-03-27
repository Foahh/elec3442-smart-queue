from __future__ import annotations

"""Model path resolution logic (no heavy dependencies)."""

from pathlib import Path

from queue_estimator.config import Settings


def resolve_model_path(settings: Settings) -> Path:
    """Return the effective model path for the configured format.

    For ``"pt"`` this is ``<model_dir>/<yolo_model>`` (a single file).
    For ``"ncnn"`` this is ``<model_dir>/<stem>_ncnn_model/`` (a directory
    produced by ``YOLO.export(format="ncnn")``).
    """

    model_dir = settings.model_dir
    if settings.yolo_model_format == "ncnn":
        stem = settings.yolo_model.removesuffix(".pt")
        return model_dir / f"{stem}_ncnn_model"
    return model_dir / settings.yolo_model
