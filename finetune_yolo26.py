#!/usr/bin/env python3
"""
Finetune YOLO26 on the exported CrowdHuman dataset.

Export trained weights to NCNN with export_yolo26.py.

Requires:
    pip install ultralytics
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
class TrainConfig:
    yolo_pretrained: str = "yolo26n.pt"
    train_epochs: int = 100
    train_imgsz: int = 512
    train_batch: int = 16
    data_root: Path | None = None
    device: str = ""
    workers: int = 8
    project: str = "results"
    name: str = "crowdhuman_yolo26n"


def resolve_data_root(config: TrainConfig) -> Path:
    return (
        config.data_root.expanduser().resolve()
        if config.data_root
        else default_dataset_root()
    )


def prepare_dataset_yaml(data_root: Path, class_name: str = "person") -> Path:
    validate_dataset(data_root)
    dataset_yaml = write_dataset_yaml(data_root, class_name=class_name)
    print(f"Dataset YAML: {dataset_yaml}")
    return dataset_yaml


def load_yolo_class():
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        die('error: ultralytics is not installed.\n  pip install ultralytics')
        raise AssertionError("unreachable") from exc
    return YOLO


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
    print(f"Export NCNN: python export_yolo26.py --weights {best_pt}")
    return best_pt


def run_training(config: TrainConfig, class_name: str = "person") -> None:
    data_root = resolve_data_root(config)
    dataset_yaml = prepare_dataset_yaml(data_root, class_name=class_name)
    YOLO = load_yolo_class()
    train_model(YOLO, config, dataset_yaml)


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = TrainConfig(
        yolo_pretrained=args.weights,
        train_epochs=args.epochs,
        train_imgsz=args.imgsz,
        train_batch=args.batch,
        data_root=args.data_root,
        device=args.device,
        workers=args.workers,
        project=args.project,
        name=args.name,
    )
    run_training(config, class_name=args.class_name)


if __name__ == "__main__":
    main()
