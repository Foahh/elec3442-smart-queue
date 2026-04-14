#!/usr/bin/env python3
"""
Export a trained YOLO26 checkpoint to NCNN for the Pi estimator.

Requires:
    pip install "ultralytics[export]"
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from common import (
    default_dataset_root,
    die,
    validate_dataset,
    write_dataset_yaml,
)


@dataclass(frozen=True)
class ExportConfig:
    weights: Path
    data_root: Path | None = None
    export_imgsz: int = 512
    export_half: bool = False
    export_int8: bool = True
    dataset_yaml: Path | None = None
    class_name: str = "person"


def load_yolo_class():
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        die('error: ultralytics is not installed.\n  pip install "ultralytics[export]"')
        raise AssertionError("unreachable") from exc
    return YOLO


def export_ncnn(
    YOLO,
    *,
    weights: Path,
    export_imgsz: int,
    export_half: bool,
    export_int8: bool,
    dataset_yaml: Path | None,
    data_root: Path,
    class_name: str,
) -> None:
    model = YOLO(str(weights))
    export_kwargs: dict[str, object] = {
        "format": "ncnn",
        "imgsz": export_imgsz,
        "half": export_half,
        "int8": export_int8,
    }

    if export_int8:
        if dataset_yaml is None:
            validate_dataset(data_root)
            dataset_yaml = write_dataset_yaml(data_root, class_name=class_name)
        export_kwargs["data"] = str(dataset_yaml)

    out = model.export(**export_kwargs)
    print(f"NCNN export done: {out}")

    expected_dir = weights.parent / f"{weights.stem}_ncnn_model"
    if expected_dir.is_dir():
        print("Copy for the Pi estimator, e.g.:")
        print(f"  cp -r {expected_dir} pi/models/")


def resolve_data_root(config: ExportConfig) -> Path:
    return (
        config.data_root.expanduser().resolve()
        if config.data_root
        else default_dataset_root()
    )


def run_export(config: ExportConfig) -> None:
    weights = config.weights.expanduser().resolve()
    if not weights.is_file():
        die(f"error: weights not found: {weights}")

    data_root = resolve_data_root(config)
    YOLO = load_yolo_class()
    export_ncnn(
        YOLO,
        weights=weights,
        export_imgsz=config.export_imgsz,
        export_half=config.export_half,
        export_int8=config.export_int8,
        dataset_yaml=config.dataset_yaml,
        data_root=data_root,
        class_name=config.class_name,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--weights",
        type=Path,
        required=True,
        help="Path to .pt checkpoint (e.g. results/crowdhuman_yolo26n/weights/best.pt)",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Dataset root for INT8 calibration (default: ./datasets/crowdhuman_person or $DATASETS_DIR/crowdhuman_person)",
    )
    parser.add_argument(
        "--dataset-yaml",
        type=Path,
        default=None,
        help="Optional Ultralytics data YAML for INT8 calibration (skips auto-generated YAML)",
    )
    parser.add_argument(
        "--class-name",
        default="person",
        help="Class name when generating dataset YAML for calibration",
    )
    parser.add_argument(
        "--export-imgsz",
        type=int,
        default=512,
        help="NCNN export image size",
    )
    parser.add_argument(
        "--export-half",
        action="store_true",
        help="Enable FP16 NCNN export",
    )
    parser.add_argument(
        "--no-export-int8",
        action="store_false",
        dest="export_int8",
        help="Disable INT8 NCNN export calibration",
    )
    parser.set_defaults(export_int8=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ExportConfig(
        weights=args.weights,
        data_root=args.data_root,
        export_imgsz=args.export_imgsz,
        export_half=args.export_half,
        export_int8=args.export_int8,
        dataset_yaml=args.dataset_yaml,
        class_name=args.class_name,
    )
    run_export(config)


if __name__ == "__main__":
    main()
