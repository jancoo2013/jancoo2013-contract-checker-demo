from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image

from research.handwriting_gate.prepare_tiles import iter_tile_boxes

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
POSITIVE_BAG = "positive_bag"
NEGATIVE_BAG = "negative_bag"


@dataclass(frozen=True)
class Pair:
    page_id: str
    original_path: Path
    redacted_path: Path


@dataclass(frozen=True)
class PreparedTile:
    path: Path
    page_id: str
    bag_id: str
    bag_label: str
    mask_fraction: float
    x: int
    y: int
    width: int
    height: int


def discover_pairs(original_dir: Path, redacted_dir: Path) -> list[Pair]:
    original_files = {
        path.relative_to(original_dir).as_posix(): path
        for path in original_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    }
    redacted_files = {
        path.relative_to(redacted_dir).as_posix(): path
        for path in redacted_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    }

    if not original_files:
        raise ValueError(f"no supported images found in {original_dir}")
    if set(original_files) != set(redacted_files):
        only_original = sorted(set(original_files) - set(redacted_files))
        only_redacted = sorted(set(redacted_files) - set(original_files))
        raise ValueError(
            "pair names do not match; "
            f"only_original={only_original[:10]}, only_redacted={only_redacted[:10]}"
        )

    pairs = []
    for relative_name in sorted(original_files):
        page_id = Path(relative_name).with_suffix("").as_posix().replace("/", "__")
        pairs.append(
            Pair(
                page_id=page_id,
                original_path=original_files[relative_name],
                redacted_path=redacted_files[relative_name],
            )
        )
    return pairs


def difference_mask(original: Image.Image, redacted: Image.Image, diff_threshold: int = 30) -> np.ndarray:
    if original.size != redacted.size:
        raise ValueError(f"paired images must have equal dimensions: {original.size} != {redacted.size}")
    if not 0 <= diff_threshold <= 255:
        raise ValueError("diff_threshold must be in [0, 255]")

    original_array = np.asarray(original.convert("RGB"), dtype=np.int16)
    redacted_array = np.asarray(redacted.convert("RGB"), dtype=np.int16)
    max_channel_difference = np.abs(original_array - redacted_array).max(axis=2)
    return max_channel_difference >= diff_threshold


def _classify_fraction(
    fraction: float,
    positive_min_fraction: float,
    negative_max_fraction: float,
) -> str | None:
    if fraction >= positive_min_fraction:
        return POSITIVE_BAG
    if fraction <= negative_max_fraction:
        return NEGATIVE_BAG
    return None


def prepare_pair(
    pair: Pair,
    output_dir: Path,
    tile_size: int,
    stride: int,
    diff_threshold: int,
    positive_min_fraction: float,
    negative_max_fraction: float,
) -> tuple[list[PreparedTile], dict[str, object]]:
    if not 0.0 <= negative_max_fraction < positive_min_fraction <= 1.0:
        raise ValueError("require 0 <= negative_max_fraction < positive_min_fraction <= 1")

    with Image.open(pair.original_path) as original_image, Image.open(pair.redacted_path) as redacted_image:
        original = original_image.convert("RGB")
        redacted = redacted_image.convert("RGB")
        mask = difference_mask(original, redacted, diff_threshold=diff_threshold)

        page_dir = output_dir / "tiles" / pair.page_id
        page_dir.mkdir(parents=True, exist_ok=True)
        prepared: list[PreparedTile] = []
        ignored = 0

        for index, box in enumerate(iter_tile_boxes(original.width, original.height, tile_size, stride)):
            left, top, right, bottom = box
            fraction = float(mask[top:bottom, left:right].mean())
            bag_label = _classify_fraction(
                fraction,
                positive_min_fraction=positive_min_fraction,
                negative_max_fraction=negative_max_fraction,
            )
            if bag_label is None:
                ignored += 1
                continue

            bag_id = f"{pair.page_id}__positive" if bag_label == POSITIVE_BAG else f"{pair.page_id}__negative"
            filename = f"tile_{index:04d}.jpg"
            tile_path = page_dir / filename
            original.crop(box).save(tile_path, format="JPEG", quality=95)
            prepared.append(
                PreparedTile(
                    path=tile_path,
                    page_id=pair.page_id,
                    bag_id=bag_id,
                    bag_label=bag_label,
                    mask_fraction=fraction,
                    x=left,
                    y=top,
                    width=right - left,
                    height=bottom - top,
                )
            )

    positive_count = sum(tile.bag_label == POSITIVE_BAG for tile in prepared)
    negative_count = sum(tile.bag_label == NEGATIVE_BAG for tile in prepared)
    report = {
        "page_id": pair.page_id,
        "width": original.width,
        "height": original.height,
        "changed_pixel_fraction": float(mask.mean()),
        "positive_candidate_tiles": positive_count,
        "negative_tiles": negative_count,
        "ignored_tiles": ignored,
    }
    return prepared, report


def write_manifest(rows: Iterable[PreparedTile], output_dir: Path) -> Path:
    manifest_path = output_dir / "paired_bags_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "path",
                "page_id",
                "bag_id",
                "bag_label",
                "mask_fraction",
                "x",
                "y",
                "width",
                "height",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "path": row.path.relative_to(output_dir).as_posix(),
                    "page_id": row.page_id,
                    "bag_id": row.bag_id,
                    "bag_label": row.bag_label,
                    "mask_fraction": f"{row.mask_fraction:.8f}",
                    "x": row.x,
                    "y": row.y,
                    "width": row.width,
                    "height": row.height,
                }
            )
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare weakly supervised handwriting bags from aligned original/redacted image pairs."
    )
    parser.add_argument("--original-dir", type=Path, required=True)
    parser.add_argument("--redacted-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tile-size", type=int, default=256)
    parser.add_argument("--stride", type=int, default=128)
    parser.add_argument("--diff-threshold", type=int, default=30)
    parser.add_argument("--positive-min-fraction", type=float, default=0.008)
    parser.add_argument("--negative-max-fraction", type=float, default=0.0)
    args = parser.parse_args()

    pairs = discover_pairs(args.original_dir, args.redacted_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    all_tiles: list[PreparedTile] = []
    page_reports: list[dict[str, object]] = []
    for pair in pairs:
        tiles, page_report = prepare_pair(
            pair=pair,
            output_dir=args.output_dir,
            tile_size=args.tile_size,
            stride=args.stride,
            diff_threshold=args.diff_threshold,
            positive_min_fraction=args.positive_min_fraction,
            negative_max_fraction=args.negative_max_fraction,
        )
        all_tiles.extend(tiles)
        page_reports.append(page_report)

    manifest_path = write_manifest(all_tiles, args.output_dir)
    report = {
        "pairs": len(pairs),
        "tiles": len(all_tiles),
        "positive_candidate_tiles": sum(tile.bag_label == POSITIVE_BAG for tile in all_tiles),
        "negative_tiles": sum(tile.bag_label == NEGATIVE_BAG for tile in all_tiles),
        "parameters": {
            "tile_size": args.tile_size,
            "stride": args.stride,
            "diff_threshold": args.diff_threshold,
            "positive_min_fraction": args.positive_min_fraction,
            "negative_max_fraction": args.negative_max_fraction,
        },
        "pages": page_reports,
    }
    report_path = args.output_dir / "paired_dataset_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(manifest_path)
    print(report_path)


if __name__ == "__main__":
    main()
