#!/usr/bin/env python3
"""
Download CrowdHuman from Hugging Face and export it in YOLO format.

Requires:
    pip install datasets pillow
    HF_TOKEN — Create a token at https://huggingface.co/settings/tokens
"""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from datasets import load_dataset
from PIL import Image

DATASET_NAME = "sshao0516/CrowdHuman"
CLASS_NAME = "person"
CLASS_ID = 0
HF_TOKEN_ENV = "HF_TOKEN"


def require_hf_token() -> None:
    if os.environ.get(HF_TOKEN_ENV, "").strip():
        return
    print(
        "error: "
        f"{HF_TOKEN_ENV} must be set for authenticated HuggingFace requests "
        "  export HF_TOKEN=...\n"
        "  https://huggingface.co/settings/tokens",
        file=sys.stderr,
    )
    raise SystemExit(1)

SPLIT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "train": ("train",),
    "val": ("validation", "val"),
}

ANNOTATION_LIST_KEYS = ("gtboxes", "annotations", "objects", "labels", "instances", "label")
NESTED_ANNOTATION_KEYS = ("gtboxes", "annotations", "objects", "labels", "instances")
BOX_KEYS = ("vbox", "fbox", "bbox", "box")
STEM_KEYS = ("ID", "id", "image_id", "filename")


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


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

    box_width = (x2 - x1) / image_width
    box_height = (y2 - y1) / image_height
    center_x = ((x1 + x2) / 2.0) / image_width
    center_y = ((y1 + y2) / 2.0) / image_height

    return center_x, center_y, box_width, box_height


def iter_annotation_lists(row: dict[str, Any]) -> Iterable[list[Any]]:
    for key in ANNOTATION_LIST_KEYS:
        value = row.get(key)
        if isinstance(value, list):
            yield value

    annotation = row.get("annotation")
    if isinstance(annotation, dict):
        for key in NESTED_ANNOTATION_KEYS:
            value = annotation.get(key)
            if isinstance(value, list):
                yield value


def is_person_annotation(annotation: dict[str, Any]) -> bool:
    tag = str(annotation.get("tag", CLASS_NAME)).lower()
    if tag != CLASS_NAME:
        return False

    extra = annotation.get("extra")
    if isinstance(extra, dict) and int(extra.get("ignore", 0) or 0) == 1:
        return False

    return True


def extract_raw_box(annotation: dict[str, Any]) -> tuple[float, float, float, float] | None:
    for key in BOX_KEYS:
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
) -> list[tuple[float, float, float, float]]:
    boxes: list[tuple[float, float, float, float]] = []

    for annotations in iter_annotation_lists(row):
        for annotation in annotations:
            if not isinstance(annotation, dict):
                continue
            if not is_person_annotation(annotation):
                continue

            raw_box = extract_raw_box(annotation)
            if raw_box is None:
                continue

            yolo_box = xywh_to_yolo(*raw_box, image_width, image_height)
            if yolo_box is not None:
                boxes.append(yolo_box)

    return boxes


def row_to_image(row: dict[str, Any]) -> Image.Image | None:
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


def row_stem(row: dict[str, Any], fallback_index: int) -> str:
    for key in STEM_KEYS:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return Path(value).stem
        if isinstance(value, int):
            return f"{value:08d}"

    return f"crowdhuman_{fallback_index:08d}"


def load_first_available_split(split_names: Iterable[str]):
    token = os.environ[HF_TOKEN_ENV].strip()
    for split_name in split_names:
        try:
            return load_dataset(DATASET_NAME, split=split_name, token=token)
        except Exception:
            continue
    return None


def prefetch_split_sequential(dataset: Any, split_label: str) -> None:
    total = len(dataset)
    print(f"  Prefetching {split_label} ({total} examples, sequential)...")
    for _ in dataset:
        pass


def write_label_file(path: Path, boxes: Iterable[tuple[float, float, float, float]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for center_x, center_y, box_width, box_height in boxes:
            handle.write(
                f"{CLASS_ID} "
                f"{center_x:.6f} {center_y:.6f} "
                f"{box_width:.6f} {box_height:.6f}\n"
            )


def effective_max_workers(requested: int) -> int:
    if requested > 0:
        return requested
    return min(32, (os.cpu_count() or 4) + 4)


def process_row_to_files(
    item: tuple[int, dict[str, Any]],
    images_dir: Path,
    labels_dir: Path,
) -> Path | None:
    index, row = item
    if not isinstance(row, dict):
        return None

    image = row_to_image(row)
    if image is None:
        return None

    image_width, image_height = image.size
    boxes = extract_yolo_boxes(row, image_width, image_height)
    if not boxes:
        return None

    stem = row_stem(row, index)
    image_path = images_dir / f"{stem}.jpg"
    label_path = labels_dir / f"{stem}.txt"

    image.save(image_path, "JPEG", quality=95)
    write_label_file(label_path, boxes)
    return image_path


def prepare_split(
    out_root: Path,
    out_split: str,
    dataset: Any,
    max_workers: int,
) -> None:
    images_dir = out_root / "images" / out_split
    labels_dir = out_root / "labels" / out_split
    list_path = out_root / f"{out_split}2017.txt"

    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    workers = effective_max_workers(max_workers)
    chunksize = max(1, len(dataset) // (workers * 4) if workers else 1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        paths = executor.map(
            lambda item: process_row_to_files(item, images_dir, labels_dir),
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

    print(f"  CrowdHuman YOLO split {out_split}: {written_count} images (workers={workers})")


def download_and_prepare_crowdhuman(out_root: Path, max_workers: int) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "classes.txt").write_text(f"{CLASS_NAME}\n", encoding="utf-8")

    print("Phase 1: load and prefetch Hugging Face splits...")
    loaded: dict[str, Any] = {}
    for out_split, source_splits in SPLIT_CANDIDATES.items():
        dataset = load_first_available_split(source_splits)
        if dataset is None:
            print(
                f"  CrowdHuman split not available for {tuple(source_splits)}, skipping {out_split}."
            )
            continue
        prefetch_split_sequential(dataset, out_split)
        loaded[out_split] = dataset

    print("Phase 2: export YOLO images and labels...")
    for out_split, dataset in loaded.items():
        prepare_split(out_root, out_split, dataset, max_workers)


def default_out_root() -> Path:
    datasets_dir = os.environ.get("DATASETS_DIR")
    if datasets_dir:
        return Path(datasets_dir).expanduser().resolve() / "crowdhuman_person"
    return Path.cwd() / "datasets" / "crowdhuman_person"


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
        help="Thread pool size for image/label writes (0 = auto, based on CPU count)",
    )
    return parser.parse_args()


def main() -> None:
    require_hf_token()
    args = parse_args()
    out_root = (args.out or default_out_root()).resolve()
    print(f"Writing CrowdHuman YOLO dataset under {out_root}")
    download_and_prepare_crowdhuman(out_root, args.workers)


if __name__ == "__main__":
    main()