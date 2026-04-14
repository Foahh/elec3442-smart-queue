#!/usr/bin/env python3
"""
Finetune YOLO26 on the exported CrowdHuman dataset and optionally export NCNN.

NCNN export is implemented in export_yolo26.py.

Requires:
    pip install "ultralytics[export]"
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from export_yolo26 import die, export_ncnn, load_yolo_class, validate_dataset, write_dataset_yaml


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


def default_dataset_root() -> Path:
    datasets_dir = os.environ.get("DATASETS_DIR")
    base = Path(datasets_dir).expanduser() if datasets_dir else Path.cwd() / "datasets"
    return (base / "crowdhuman_person").resolve()


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
