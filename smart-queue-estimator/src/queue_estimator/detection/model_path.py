from __future__ import annotations

"""Model path resolution logic (no heavy dependencies)."""

from pathlib import Path

from queue_estimator.config import Settings


def resolve_model_path(settings: Settings) -> Path:
    """Return the NCNN model directory path used at runtime.

    Runtime always expects ``<model_dir>/<stem>_ncnn_model/`` produced by
    ``YOLO.export(format="ncnn")``.
    """

    stem = settings.yolo_model.removesuffix(".pt")
    return settings.model_dir / f"{stem}_ncnn_model"
