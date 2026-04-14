"""CrowdHuman layout checks and Ultralytics dataset YAML for YOLO training/export."""

from __future__ import annotations

import os
import sys
from pathlib import Path


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
