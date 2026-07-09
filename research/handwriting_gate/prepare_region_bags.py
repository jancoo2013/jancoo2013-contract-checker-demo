from __future__ import annotations

import argparse
import csv
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from research.handwriting_gate.prepare_paired_bags import Pair, difference_mask, discover_pairs
from research.handwriting_gate.prepare_tiles import iter_tile_boxes

POSITIVE_BAG = "positive_bag"
NEGATIVE_BAG = "negative_bag"


@dataclass(frozen=True)
class Component:
    component_id: int
    area: int
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class RegionTile:
    path: Path
    page_id: str
    bag_id: str
    bag_label: str
    x: int
    y: int
    width: int
    height: int
    component_id: int | None
    component_fraction: float


def dilate_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius < 0:
        raise ValueError("radius must be >= 0")
    if radius == 0:
        return mask.astype(bool, copy=True)
    image = Image.fromarray(mask.astype(np.uint8) * 255)
    size = radius * 2 + 1
    return np.asarray(image.filter(ImageFilter.MaxFilter(size=size))) > 0


def label_components(mask: np.ndarray, min_area: int) -> tuple[np.ndarray, list[Component]]:
    if mask.ndim != 2:
        raise ValueError("mask must be 2D")
    if min_area <= 0:
        raise ValueError("min_area must be positive")

    height, width = mask.shape
    labels = np.zeros((height, width), dtype=np.int32)
    seen = np.zeros((height, width), dtype=bool)
    components: list[Component] = []
    component_id = 0

    for start_y, start_x in zip(*np.nonzero(mask), strict=True):
        if seen[start_y, start_x]:
            continue

        queue: deque[tuple[int, int]] = deque([(int(start_y), int(start_x))])
        seen[start_y, start_x] = True
        pixels: list[tuple[int, int]] = []
        min_x = max_x = int(start_x)
        min_y = max_y = int(start_y)

        while queue:
            y, x = queue.popleft()
            pixels.append((y, x))
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    ny = y + dy
                    nx = x + dx
                    if ny < 0 or ny >= height or nx < 0 or nx >= width:
                        continue
                    if seen[ny, nx] or not mask[ny, nx]:
                        continue
                    seen[ny, nx] = True
                    queue.append((ny, nx))

        if len(pixels) < min_area:
            continue

        component_id += 1
        for y, x in pixels:
            labels[y, x] = component_id
        components.append(
            Component(
                component_id=component_id,
                area=len(pixels),
                x=min_x,
                y=min_y,
                width=max_x - min_x + 1,
                height=max_y - min_y + 1,
            )
        )

    return labels, components


def _component_fraction(labels: np.ndarray, component_id: int, box: tuple[int, int, int, int]) -> float:
    left, top, right, bottom = box
    tile = labels[top:bottom, left:right]
    return float(np.mean(tile == component_id))


def prepare_pair_regions(
    pair: Pair,
    output_dir: Path,
    tile_size: int,
    stride: int,
    diff_threshold: int,
    component_min_area: int,
    component_tile_min_fraction: float,
    negative_exclusion_radius: int,
) -> tuple[list[RegionTile], dict[str, object]]:
    if not 0.0 < component_tile_min_fraction <= 1.0:
        raise ValueError("component_tile_min_fraction must be in (0, 1]")

    with Image.open(pair.original_path) as original_image, Image.open(pair.redacted_path) as redacted_image:
        original = original_image.convert("RGB")
        redacted = redacted_image.convert("RGB")
        raw_mask = difference_mask(original, redacted, diff_threshold=diff_threshold)
        labels, components = label_components(raw_mask, min_area=component_min_area)
        exclusion_mask = dilate_mask(raw_mask, radius=negative_exclusion_radius)
        boxes = list(iter_tile_boxes(original.width, original.height, tile_size, stride))

        page_dir = output_dir / "region_tiles" / pair.page_id
        page_dir.mkdir(parents=True, exist_ok=True)
        rows: list[RegionTile] = []

        for component in components:
            bag_id = f"{pair.page_id}__region_{component.component_id:03d}"
            for tile_index, box in enumerate(boxes):
                fraction = _component_fraction(labels, component.component_id, box)
                if fraction < component_tile_min_fraction:
                    continue
                left, top, right, bottom = box
                filename = f"region_{component.component_id:03d}__tile_{tile_index:04d}.jpg"
                tile_path = page_dir / filename
                original.crop(box).save(tile_path, format="JPEG", quality=95)
                rows.append(
                    RegionTile(
                        path=tile_path,
                        page_id=pair.page_id,
                        bag_id=bag_id,
                        bag_label=POSITIVE_BAG,
                        x=left,
                        y=top,
                        width=right - left,
                        height=bottom - top,
                        component_id=component.component_id,
                        component_fraction=fraction,
                    )
                )

        negative_count = 0
        for tile_index, box in enumerate(boxes):
            left, top, right, bottom = box
            if np.any(exclusion_mask[top:bottom, left:right]):
                continue
            bag_id = f"{pair.page_id}__negative_{tile_index:04d}"
            filename = f"negative__tile_{tile_index:04d}.jpg"
            tile_path = page_dir / filename
            original.crop(box).save(tile_path, format="JPEG", quality=95)
            rows.append(
                RegionTile(
                    path=tile_path,
                    page_id=pair.page_id,
                    bag_id=bag_id,
                    bag_label=NEGATIVE_BAG,
                    x=left,
                    y=top,
                    width=right - left,
                    height=bottom - top,
                    component_id=None,
                    component_fraction=0.0,
                )
            )
            negative_count += 1

    component_tile_counts = {
        str(component.component_id): sum(
            row.component_id == component.component_id and row.bag_label == POSITIVE_BAG for row in rows
        )
        for component in components
    }
    report = {
        "page_id": pair.page_id,
        "width": original.width,
        "height": original.height,
        "changed_pixel_fraction": float(raw_mask.mean()),
        "components": len(components),
        "positive_tiles": sum(row.bag_label == POSITIVE_BAG for row in rows),
        "negative_tiles": negative_count,
        "component_tile_counts": component_tile_counts,
        "component_boxes": [component.__dict__ for component in components],
    }
    return rows, report


def write_manifest(rows: list[RegionTile], output_dir: Path) -> Path:
    manifest_path = output_dir / "region_bags_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "path",
                "page_id",
                "bag_id",
                "bag_label",
                "x",
                "y",
                "width",
                "height",
                "component_id",
                "component_fraction",
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
                    "x": row.x,
                    "y": row.y,
                    "width": row.width,
                    "height": row.height,
                    "component_id": "" if row.component_id is None else row.component_id,
                    "component_fraction": f"{row.component_fraction:.8f}",
                }
            )
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build region-level weakly supervised handwriting bags from original/redacted pairs."
    )
    parser.add_argument("--original-dir", type=Path, required=True)
    parser.add_argument("--redacted-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tile-size", type=int, default=256)
    parser.add_argument("--stride", type=int, default=128)
    parser.add_argument("--diff-threshold", type=int, default=30)
    parser.add_argument("--component-min-area", type=int, default=200)
    parser.add_argument("--component-tile-min-fraction", type=float, default=0.001)
    parser.add_argument("--negative-exclusion-radius", type=int, default=8)
    args = parser.parse_args()

    pairs = discover_pairs(args.original_dir, args.redacted_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[RegionTile] = []
    page_reports: list[dict[str, object]] = []
    for pair in pairs:
        rows, page_report = prepare_pair_regions(
            pair=pair,
            output_dir=args.output_dir,
            tile_size=args.tile_size,
            stride=args.stride,
            diff_threshold=args.diff_threshold,
            component_min_area=args.component_min_area,
            component_tile_min_fraction=args.component_tile_min_fraction,
            negative_exclusion_radius=args.negative_exclusion_radius,
        )
        all_rows.extend(rows)
        page_reports.append(page_report)

    manifest_path = write_manifest(all_rows, args.output_dir)
    report = {
        "pairs": len(pairs),
        "positive_region_bags": sum(int(page["components"]) for page in page_reports),
        "positive_tiles": sum(row.bag_label == POSITIVE_BAG for row in all_rows),
        "negative_tiles": sum(row.bag_label == NEGATIVE_BAG for row in all_rows),
        "parameters": {
            "tile_size": args.tile_size,
            "stride": args.stride,
            "diff_threshold": args.diff_threshold,
            "component_min_area": args.component_min_area,
            "component_tile_min_fraction": args.component_tile_min_fraction,
            "negative_exclusion_radius": args.negative_exclusion_radius,
        },
        "pages": page_reports,
    }
    report_path = args.output_dir / "region_dataset_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(manifest_path)
    print(report_path)


if __name__ == "__main__":
    main()
