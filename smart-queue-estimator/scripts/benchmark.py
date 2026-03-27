#!/usr/bin/env python3
from __future__ import annotations

"""Run Ultralytics benchmarks for the configured model on the current device.

Usage:
    python scripts/benchmark.py                         # benchmark all export formats
    python scripts/benchmark.py --format ncnn           # benchmark NCNN only
    python scripts/benchmark.py --imgsz 320 --data coco128.yaml
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ultralytics import YOLO

from queue_estimator.config import get_settings


def main() -> None:
    """CLI entry point for model benchmarking."""

    settings = get_settings()
    parser = argparse.ArgumentParser(description="Benchmark YOLO model on this device")
    parser.add_argument("--model", type=str, default=None, help="Model filename (default: from settings)")
    parser.add_argument("--data", type=str, default="coco128.yaml", help="Benchmark dataset")
    parser.add_argument("--imgsz", type=int, default=None, help="Input image size")
    parser.add_argument("--format", type=str, default=None, help="Limit to one export format (e.g. ncnn)")
    args = parser.parse_args()

    model_name = args.model or settings.yolo_model
    model_dir = settings.model_dir
    imgsz = args.imgsz or settings.yolo_imgsz
    pt_path = model_dir / model_name

    if pt_path.exists():
        model = YOLO(str(pt_path))
    else:
        model = YOLO(model_name)

    bench_kwargs: dict[str, object] = {"data": args.data, "imgsz": imgsz}
    if args.format:
        bench_kwargs["format"] = args.format

    model.benchmark(**bench_kwargs)


if __name__ == "__main__":
    main()
