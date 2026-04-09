#!/usr/bin/env python3
"""
Download CrowdHuman from Hugging Face and export it in YOLO format.

Requires:
    pip install datasets pillow
    HF_TOKEN (or --hf-token) - Create a token at https://huggingface.co/settings/tokens
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from datasets import load_dataset
from PIL import Image


@dataclass(frozen=True)
class ExportConfig:
    dataset_name: str = "sshao0516/CrowdHuman"
    class_name: str = "person"
    class_id: int = 0
    split_candidates: dict[str, tuple[str, ...]] | None = None
    annotation_list_keys: tuple[str, ...] = (
        "gtboxes",
        "annotations",
        "objects",
        "labels",
        "instances",
        "label",
    )
    nested_annotation_keys: tuple[str, ...] = (
        "gtboxes",
        "annotations",
        "objects",
        "labels",
        "instances",
    )
    box_keys: tuple[str, ...] = ("vbox", "fbox", "bbox", "box")
    stem_keys: tuple[str, ...] = ("ID", "id", "image_id", "filename")
    max_workers: int = 0

    def __post_init__(self) -> None:
        if self.split_candidates is None:
            object.__setattr__(
                self,
                "split_candidates",
                {
                    "train": ("train",),
                    "val": ("validation", "val"),
                },
            )


def die(message: str, exit_code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    die(
        f"error: {name} must be set for authenticated Hugging Face requests\n"
        f"  Linux/macOS (bash): export {name}=...\n"
        f"  Windows (cmd.exe):  set {name}=...\n"
        f'  Windows (PowerShell): $env:{name}="..."\n'
        "  https://huggingface.co/settings/tokens"
    )


def default_dataset_root() -> Path:
    datasets_dir = os.environ.get("DATASETS_DIR")
    base = Path(datasets_dir).expanduser() if datasets_dir else Path.cwd() / "datasets"
    return (base / "crowdhuman_person").resolve()


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def effective_max_workers(requested: int) -> int:
    if requested > 0:
        return requested
    return min(32, (os.cpu_count() or 4) + 4)


def row_stem(
    row: dict[str, Any], fallback_index: int, stem_keys: tuple[str, ...]
) -> str:
    for key in stem_keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return Path(value).stem
        if isinstance(value, int):
            return f"{value:08d}"
    return f"crowdhuman_{fallback_index:08d}"


def xywh_to_yolo(
    x: float,
    y: float,
    w: float,
    h: float,
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float] | None:
    if w <= 0 or h <= 0 or image_width <= 0 or image_height <= 0:
        return None

    x1 = clamp(x, 0.0, float(image_width))
    y1 = clamp(y, 0.0, float(image_height))
    x2 = clamp(x + w, 0.0, float(image_width))
    y2 = clamp(y + h, 0.0, float(image_height))

    if x2 <= x1 or y2 <= y1:
        return None

    return (
        ((x1 + x2) / 2.0) / image_width,
        ((y1 + y2) / 2.0) / image_height,
        (x2 - x1) / image_width,
        (y2 - y1) / image_height,
    )


def iter_annotation_lists(
    row: dict[str, Any],
    annotation_list_keys: tuple[str, ...],
    nested_annotation_keys: tuple[str, ...],
) -> Iterable[list[Any]]:
    for key in annotation_list_keys:
        value = row.get(key)
        if isinstance(value, list):
            yield value

    annotation = row.get("annotation")
    if isinstance(annotation, dict):
        for key in nested_annotation_keys:
            value = annotation.get(key)
            if isinstance(value, list):
                yield value


def is_person_annotation(annotation: dict[str, Any], class_name: str) -> bool:
    tag = str(annotation.get("tag", class_name)).lower()
    if tag != class_name:
        return False

    extra = annotation.get("extra")
    if isinstance(extra, dict) and int(extra.get("ignore", 0) or 0) == 1:
        return False

    return True


def extract_raw_box(
    annotation: dict[str, Any],
    box_keys: tuple[str, ...],
) -> tuple[float, float, float, float] | None:
    for key in box_keys:
        value = annotation.get(key)
        if not isinstance(value, (list, tuple)) or len(value) < 4:
            continue

        x = safe_float(value[0])
        y = safe_float(value[1])
        w = safe_float(value[2])
        h = safe_float(value[3])

        if None not in (x, y, w, h):
            return x, y, w, h

    return None


def extract_yolo_boxes(
    row: dict[str, Any],
    image_width: int,
    image_height: int,
    config: ExportConfig,
) -> list[tuple[float, float, float, float]]:
    boxes: list[tuple[float, float, float, float]] = []

    for annotations in iter_annotation_lists(
        row,
        config.annotation_list_keys,
        config.nested_annotation_keys,
    ):
        for annotation in annotations:
            if not isinstance(annotation, dict):
                continue
            if not is_person_annotation(annotation, config.class_name):
                continue

            raw_box = extract_raw_box(annotation, config.box_keys)
            if raw_box is None:
                continue

            yolo_box = xywh_to_yolo(*raw_box, image_width, image_height)
            if yolo_box is not None:
                boxes.append(yolo_box)

    return boxes


def row_to_rgb_image(row: dict[str, Any]) -> Image.Image | None:
    image = row.get("image")
    if image is None:
        return None

    if isinstance(image, Image.Image):
        return image.convert("RGB")

    if not isinstance(image, dict):
        return None

    image_bytes = image.get("bytes")
    if isinstance(image_bytes, (bytes, bytearray)) and image_bytes:
        return Image.open(BytesIO(image_bytes)).convert("RGB")

    image_path = image.get("path")
    if isinstance(image_path, str) and image_path:
        path = Path(image_path)
        if path.is_file():
            return Image.open(path).convert("RGB")

    return None


def write_label_file(
    path: Path,
    boxes: Iterable[tuple[float, float, float, float]],
    class_id: int,
) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for center_x, center_y, box_width, box_height in boxes:
            handle.write(
                f"{class_id} {center_x:.6f} {center_y:.6f} {box_width:.6f} {box_height:.6f}\n"
            )


def process_row_to_files(
    item: tuple[int, dict[str, Any]],
    *,
    images_dir: Path,
    labels_dir: Path,
    config: ExportConfig,
) -> Path | None:
    index, row = item
    if not isinstance(row, dict):
        return None

    image = row_to_rgb_image(row)
    if image is None:
        return None

    width, height = image.size
    boxes = extract_yolo_boxes(row, width, height, config)
    if not boxes:
        return None

    stem = row_stem(row, index, config.stem_keys)
    image_path = images_dir / f"{stem}.jpg"
    label_path = labels_dir / f"{stem}.txt"

    image.save(image_path, "JPEG", quality=95)
    write_label_file(label_path, boxes, config.class_id)
    return image_path


def load_first_available_split(
    dataset_name: str, split_names: Iterable[str], token: str
):
    for split_name in split_names:
        try:
            return load_dataset(dataset_name, split=split_name, token=token)
        except Exception:
            continue
    return None


def prefetch_split(dataset: Any, split_label: str) -> None:
    total = len(dataset)
    print(f"  Prefetching {split_label} ({total} examples, sequential)...")
    for _ in dataset:
        pass


def prepare_split(
    out_root: Path, out_split: str, dataset: Any, config: ExportConfig
) -> None:
    images_dir = out_root / "images" / out_split
    labels_dir = out_root / "labels" / out_split
    list_path = out_root / f"{out_split}2017.txt"

    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    workers = effective_max_workers(config.max_workers)
    chunksize = max(1, len(dataset) // (workers * 4)) if workers else 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        paths = executor.map(
            lambda item: process_row_to_files(
                item,
                images_dir=images_dir,
                labels_dir=labels_dir,
                config=config,
            ),
            enumerate(dataset),
            chunksize=chunksize,
        )

        written_count = 0
        with list_path.open("w", encoding="utf-8") as list_file:
            for image_path in paths:
                if image_path is None:
                    continue
                list_file.write(f"{image_path}\n")
                written_count += 1

    print(
        f"  CrowdHuman YOLO split {out_split}: {written_count} images (workers={workers})"
    )


def write_classes_file(out_root: Path, class_name: str) -> None:
    (out_root / "classes.txt").write_text(f"{class_name}\n", encoding="utf-8")


def download_and_prepare_crowdhuman(
    out_root: Path, config: ExportConfig, hf_token: str | None = None
) -> None:
    token = (hf_token or "").strip() or require_env("HF_TOKEN")
    out_root.mkdir(parents=True, exist_ok=True)
    write_classes_file(out_root, config.class_name)

    print("Phase 1: load and prefetch Hugging Face splits...")
    loaded: dict[str, Any] = {}
    for out_split, source_splits in config.split_candidates.items():
        dataset = load_first_available_split(config.dataset_name, source_splits, token)
        if dataset is None:
            print(
                f"  CrowdHuman split not available for {tuple(source_splits)}, skipping {out_split}."
            )
            continue
        prefetch_split(dataset, out_split)
        loaded[out_split] = dataset

    print("Phase 2: export YOLO images and labels...")
    for out_split, dataset in loaded.items():
        prepare_split(out_root, out_split, dataset, config)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output root (default: ./datasets/crowdhuman_person or $DATASETS_DIR/crowdhuman_person)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Thread pool size for image and label writes (0 = auto)",
    )
    parser.add_argument(
        "--dataset-name",
        default="sshao0516/CrowdHuman",
        help="Hugging Face dataset name",
    )
    parser.add_argument(
        "--class-name",
        default="person",
        help="Class name to export into classes.txt and filter annotations by",
    )
    parser.add_argument(
        "--class-id",
        type=int,
        default=0,
        help="YOLO class id written into label files",
    )
    parser.add_argument(
        "--hf-token",
        default=None,
        help="Hugging Face access token (overrides HF_TOKEN env var)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_root = (args.out or default_dataset_root()).resolve()
    config = ExportConfig(
        dataset_name=args.dataset_name,
        class_name=args.class_name,
        class_id=args.class_id,
        max_workers=args.workers,
    )
    print(f"Writing CrowdHuman YOLO dataset under {out_root}")
    download_and_prepare_crowdhuman(out_root, config, hf_token=args.hf_token)


if __name__ == "__main__":
    main()
