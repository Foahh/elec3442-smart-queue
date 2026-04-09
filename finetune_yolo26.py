#!/usr/bin/env python3
"""
Finetune YOLO26 on the exported CrowdHuman dataset and optionally export NCNN.

Requires:
    pip install "ultralytics[export]"
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrainConfig:
    yolo_pretrained: str = "yolo26n.pt"
    train_epochs: int = 100
    train_imgsz: int = 512
    train_batch: int = 16
    export_source_pt: Path | None = None
    export_imgsz: int | None = 512
    export_half: bool = False
    export_int8: bool = True
    data_root: Path | None = None
    device: str = ""
    workers: int = 8
    project: str = "results"
    name: str = "crowdhuman_yolo26n"
    skip_train: bool = False
    skip_export: bool = False


def die(message: str, exit_code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def default_dataset_root() -> Path:
    datasets_dir = os.environ.get("DATASETS_DIR")
    base = Path(datasets_dir).expanduser() if datasets_dir else Path.cwd() / "datasets"
    return (base / "crowdhuman_person").resolve()


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


def resolve_data_root(config: TrainConfig) -> Path:
    return (
        config.data_root.expanduser().resolve()
        if config.data_root
        else default_dataset_root()
    )


def resolve_export_imgsz(config: TrainConfig) -> int:
    return (
        config.export_imgsz if config.export_imgsz is not None else config.train_imgsz
    )


def resolve_trained_weights(project: str, name: str) -> Path:
    best = Path(project) / name / "weights" / "best.pt"
    if not best.is_file():
        die(f"error: missing {best} - train first or set --export-source-pt")
    return best


def resolve_export_source(config: TrainConfig) -> Path:
    if config.export_source_pt is None:
        return resolve_trained_weights(config.project, config.name)

    weights = Path(config.export_source_pt).expanduser().resolve()
    if not weights.is_file():
        die(f"error: export_source_pt not found: {weights}")
    return weights


def maybe_prepare_dataset_yaml(
    data_root: Path, needs_dataset: bool, class_name: str = "person"
) -> Path | None:
    if not needs_dataset:
        return None
    validate_dataset(data_root)
    dataset_yaml = write_dataset_yaml(data_root, class_name=class_name)
    print(f"Dataset YAML: {dataset_yaml}")
    return dataset_yaml


def train_model(YOLO, config: TrainConfig, dataset_yaml: Path) -> Path:
    model = YOLO(config.yolo_pretrained)
    train_kwargs: dict[str, object] = {
        "data": str(dataset_yaml),
        "epochs": config.train_epochs,
        "imgsz": config.train_imgsz,
        "batch": config.train_batch,
        "project": config.project,
        "name": config.name,
        "exist_ok": True,
        "workers": config.workers,
    }
    if config.device:
        train_kwargs["device"] = config.device

    model.train(**train_kwargs)

    best_pt = Path(config.project) / config.name / "weights" / "best.pt"
    if not best_pt.is_file():
        die(f"error: training finished but missing {best_pt}")

    print(f"Best weights: {best_pt}")
    return best_pt


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
        print(f"  cp -r {expected_dir} models/")


def run_training_and_export(config: TrainConfig, class_name: str = "person") -> None:
    data_root = resolve_data_root(config)
    export_imgsz = resolve_export_imgsz(config)

    YOLO = load_yolo_class()
    needs_dataset = (not config.skip_train) or config.export_int8
    dataset_yaml = maybe_prepare_dataset_yaml(
        data_root, needs_dataset, class_name=class_name
    )

    best_pt = (
        resolve_export_source(config)
        if config.skip_train
        else train_model(YOLO, config, dataset_yaml)
    )

    if config.skip_export:
        print("Skipping NCNN export.")
        return

    export_ncnn(
        YOLO,
        weights=best_pt,
        export_imgsz=export_imgsz,
        export_half=config.export_half,
        export_int8=config.export_int8,
        dataset_yaml=dataset_yaml,
        data_root=data_root,
        class_name=class_name,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Dataset root (default: ./datasets/crowdhuman_person or $DATASETS_DIR/crowdhuman_person)",
    )
    parser.add_argument(
        "--weights",
        default="yolo26n.pt",
        help="Pretrained YOLO checkpoint for finetuning",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Training epochs",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=512,
        help="Training image size",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=16,
        help="Training batch size",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Ultralytics dataloader workers",
    )
    parser.add_argument(
        "--device",
        default="",
        help="Torch device string passed to Ultralytics",
    )
    parser.add_argument(
        "--project",
        default="results",
        help="Training output project directory",
    )
    parser.add_argument(
        "--name",
        default="crowdhuman_yolo26n",
        help="Training run name under the project directory",
    )
    parser.add_argument(
        "--class-name",
        default="person",
        help="Class name written into the generated dataset YAML",
    )
    parser.add_argument(
        "--skip-train",
        action="store_true",
        help="Skip finetuning and export from an existing checkpoint",
    )
    parser.add_argument(
        "--export-source-pt",
        type=Path,
        default=None,
        help="Checkpoint to export when --skip-train is set",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip NCNN export after training",
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
    config = TrainConfig(
        yolo_pretrained=args.weights,
        train_epochs=args.epochs,
        train_imgsz=args.imgsz,
        train_batch=args.batch,
        export_source_pt=args.export_source_pt,
        export_imgsz=args.export_imgsz,
        export_half=args.export_half,
        export_int8=args.export_int8,
        data_root=args.data_root,
        device=args.device,
        workers=args.workers,
        project=args.project,
        name=args.name,
        skip_train=args.skip_train,
        skip_export=args.skip_export,
    )
    run_training_and_export(config, class_name=args.class_name)


if __name__ == "__main__":
    main()
