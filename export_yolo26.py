#!/usr/bin/env python3
"""
NCNN export helpers for YOLO26 (Ultralytics).

Used by finetune_yolo26.py and requires:
    pip install "ultralytics[export]"
"""

from __future__ import annotations

import sys
from pathlib import Path


def die(message: str, exit_code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def dataset_paths(data_root: Path) -> dict[str, Path]:
    root = data_root.resolve()
    return {
        "root": root,
        "train_images": root / "images" / "train",
        "train_labels": root / "labels" / "train",
        "val_images": root / "images" / "val",
        "val_labels": root / "labels" / "val",
        "yaml": root / "crowdhuman_ultralytics.yaml",
    }


def ensure_dir(path: Path, *, label: str) -> None:
    if not path.is_dir():
        die(f"error: missing {label}: {path}")


def ensure_nonempty_dir(path: Path, *, label: str, hint: str | None = None) -> None:
    if path.is_dir() and any(path.iterdir()):
        return
    message = f"error: missing or empty {label}: {path}"
    if hint:
        message += f"\n  {hint}"
    die(message)


def validate_dataset(data_root: Path) -> None:
    paths = dataset_paths(data_root)
    ensure_nonempty_dir(
        paths["train_images"],
        label="training images",
        hint="Run download_dataset.py first.",
    )
    ensure_dir(paths["train_labels"], label="training labels")
    ensure_nonempty_dir(
        paths["val_images"],
        label="validation images",
        hint="The CrowdHuman export must include a validation split.",
    )
    ensure_dir(paths["val_labels"], label="validation labels")


def write_dataset_yaml(data_root: Path, class_name: str = "person") -> Path:
    paths = dataset_paths(data_root)
    content = "\n".join(
        [
            f"path: {paths['root'].as_posix()}",
            "train: images/train",
            "val: images/val",
            "nc: 1",
            "names:",
            f"  0: {class_name}",
            "",
        ]
    )
    paths["yaml"].write_text(content, encoding="utf-8")
    return paths["yaml"]


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
