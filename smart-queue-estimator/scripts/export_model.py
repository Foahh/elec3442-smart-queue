#!/usr/bin/env python3
from __future__ import annotations

"""Export a YOLO PyTorch model to NCNN format for Raspberry Pi deployment.

Usage:
    python scripts/export_model.py                       # uses defaults from .env / settings
    python scripts/export_model.py --model yolo26n.pt    # explicit model name
    python scripts/export_model.py --imgsz 320           # smaller input for faster inference

The exported NCNN directory is placed alongside the source .pt file inside
the configured model_dir (default: models/).
"""

import argparse
import sys
from pathlib import Path

# Allow running from project root without installation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from loguru import logger
from ultralytics import YOLO

from queue_estimator.config import get_settings


def _ncnn_dir_name(pt_name: str) -> str:
    """Derive NCNN output directory name from a .pt filename."""

    stem = pt_name.removesuffix(".pt")
    return f"{stem}_ncnn_model"


def export_to_ncnn(
    model_name: str | None = None,
    model_dir: Path | None = None,
    imgsz: int | None = None,
) -> Path:
    """Export a .pt model to NCNN and return the output directory path.

    If the .pt file is not yet present in model_dir it will be downloaded
    automatically by the Ultralytics hub.
    """

    settings = get_settings()
    model_name = model_name or settings.yolo_model
    model_dir = model_dir or settings.model_dir
    imgsz = imgsz or settings.yolo_imgsz

    model_dir.mkdir(parents=True, exist_ok=True)
    pt_path = model_dir / model_name

    if pt_path.exists():
        logger.info("Loading local model: {}", pt_path)
        model = YOLO(str(pt_path))
    else:
        logger.info("Model not found locally; downloading {}...", model_name)
        model = YOLO(model_name)

    logger.info("Exporting to NCNN (imgsz={})...", imgsz)
    export_path_str: str = model.export(format="ncnn", imgsz=imgsz)
    exported = Path(export_path_str)

    target = model_dir / _ncnn_dir_name(model_name)
    if exported.resolve() != target.resolve():
        if target.exists():
            import shutil

            shutil.rmtree(target)
        exported.rename(target)
        logger.info("Moved exported model to {}", target)
    else:
        logger.info("Exported model already at {}", target)

    logger.info("Export complete. Use QE_YOLO_MODEL_FORMAT=ncnn to switch runtime.")
    return target


def main() -> None:
    """CLI entry point for model export."""

    parser = argparse.ArgumentParser(description="Export YOLO model to NCNN")
    parser.add_argument("--model", type=str, default=None, help="Model filename (e.g. yolo26n.pt)")
    parser.add_argument("--model-dir", type=Path, default=None, help="Model directory")
    parser.add_argument("--imgsz", type=int, default=None, help="Input image size for export")
    args = parser.parse_args()

    export_to_ncnn(model_name=args.model, model_dir=args.model_dir, imgsz=args.imgsz)


if __name__ == "__main__":
    main()
