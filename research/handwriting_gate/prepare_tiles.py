from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from research.handwriting_gate.gate_baseline import HAND_MARK_PRESENT, PRINTED_ONLY, stable_split


@dataclass(frozen=True)
class MarkBox:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)


@dataclass(frozen=True)
class PageAnnotation:
    path: Path
    group_id: str
    page_id: str
    marks: tuple[MarkBox, ...]


def iter_tile_boxes(width: int, height: int, tile_size: int, stride: int):
    if min(width, height, tile_size, stride) <= 0:
        raise ValueError("image dimensions, tile_size, and stride must be positive")

    def starts(length: int) -> list[int]:
        if length <= tile_size:
            return [0]
        values = list(range(0, length - tile_size + 1, stride))
        last = length - tile_size
        if values[-1] != last:
            values.append(last)
        return values

    for top in starts(height):
        for left in starts(width):
            yield (left, top, min(left + tile_size, width), min(top + tile_size, height))


def tile_has_mark(tile: tuple[int, int, int, int], marks: tuple[MarkBox, ...]) -> bool:
    left, top, right, bottom = tile
    for mark in marks:
        cx, cy = mark.center
        if left <= cx < right and top <= cy < bottom:
            return True
    return False


def load_annotations(path: Path, image_root: Path) -> list[PageAnnotation]:
    grouped: dict[tuple[str, str, str], list[MarkBox]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"path", "group_id", "page_id", "mark_x", "mark_y", "mark_w", "mark_h"}
        if not required.issubset(reader.fieldnames or []):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"annotations are missing columns: {', '.join(missing)}")
        for line_no, row in enumerate(reader, start=2):
            rel_path = (row["path"] or "").strip()
            group_id = (row["group_id"] or "").strip()
            page_id = (row["page_id"] or "").strip()
            if not rel_path or not group_id or not page_id:
                raise ValueError(f"line {line_no}: path, group_id, and page_id are required")
            key = (rel_path, group_id, page_id)
            marks = grouped.setdefault(key, [])
            raw_coords = [row[name] for name in ("mark_x", "mark_y", "mark_w", "mark_h")]
            if all((value or "").strip() == "" for value in raw_coords):
                continue
            if any((value or "").strip() == "" for value in raw_coords):
                raise ValueError(f"line {line_no}: mark coordinates must be all blank or all integers")
            x, y, width, height = (int(value) for value in raw_coords)
            if x < 0 or y < 0 or width <= 0 or height <= 0:
                raise ValueError(f"line {line_no}: invalid mark rectangle")
            marks.append(MarkBox(x=x, y=y, width=width, height=height))

    return [
        PageAnnotation(
            path=(image_root / rel_path).resolve(),
            group_id=group_id,
            page_id=page_id,
            marks=tuple(marks),
        )
        for (rel_path, group_id, page_id), marks in grouped.items()
    ]


def prepare_tiles(
    annotations: list[PageAnnotation],
    output_dir: Path,
    tile_size: int = 384,
    stride: int = 256,
) -> Path:
    tiles_dir = output_dir / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "tiles_manifest.csv"

    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "label", "group_id", "page_id", "split"])
        writer.writeheader()
        for page in annotations:
            with Image.open(page.path) as image:
                rgb = image.convert("RGB")
                for index, box in enumerate(iter_tile_boxes(rgb.width, rgb.height, tile_size, stride)):
                    label = HAND_MARK_PRESENT if tile_has_mark(box, page.marks) else PRINTED_ONLY
                    filename = f"{page.page_id}__{index:04d}.jpg"
                    tile_path = tiles_dir / filename
                    rgb.crop(box).save(tile_path, format="JPEG", quality=92)
                    writer.writerow(
                        {
                            "path": tile_path.relative_to(output_dir).as_posix(),
                            "label": label,
                            "group_id": page.group_id,
                            "page_id": page.page_id,
                            "split": stable_split(page.group_id),
                        }
                    )
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare handwriting-gate tiles from annotated pages.")
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tile-size", type=int, default=384)
    parser.add_argument("--stride", type=int, default=256)
    args = parser.parse_args()

    annotations = load_annotations(args.annotations, args.image_root)
    if not annotations:
        raise SystemExit("No annotated pages found")
    manifest = prepare_tiles(annotations, args.output_dir, args.tile_size, args.stride)
    print(manifest)


if __name__ == "__main__":
    main()
