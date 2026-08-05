from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version

from research.ocr_benchmark.viability import load_expected_manifest

RENDERER_VERSION = "synthetic-hebrew-a4-v1"
PAGE_WIDTH = 1654
PAGE_HEIGHT = 2339
MARGIN_X = 150
MARGIN_TOP = 150
MARGIN_BOTTOM = 150
BODY_FONT_SIZE = 46
TITLE_FONT_SIZE = 62
LINE_GAP = 22
PARAGRAPH_GAP = 34


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> float:
    return float(draw.textlength(text, font=font, direction="rtl", language="he"))


def wrap_rtl(
    draw: ImageDraw.ImageDraw,
    paragraph: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    words = paragraph.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _text_width(draw, candidate, font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_page(
    text: str,
    body_font: ImageFont.FreeTypeFont,
    title_font: ImageFont.FreeTypeFont,
    seed: int,
) -> Image.Image:
    image = Image.new("L", (PAGE_WIDTH, PAGE_HEIGHT), 248)
    draw = ImageDraw.Draw(image)
    rng = random.Random(seed)

    for _ in range(850):
        x = rng.randrange(PAGE_WIDTH)
        y = rng.randrange(PAGE_HEIGHT)
        shade = rng.choice((235, 239, 242, 245))
        draw.point((x, y), fill=shade)

    paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    max_width = PAGE_WIDTH - 2 * MARGIN_X
    y = MARGIN_TOP
    for paragraph_index, paragraph in enumerate(paragraphs):
        font = title_font if paragraph_index == 0 else body_font
        line_height = font.getbbox("אבג")[3] - font.getbbox("אבג")[1]
        for line in wrap_rtl(draw, paragraph, font, max_width):
            if y + line_height > PAGE_HEIGHT - MARGIN_BOTTOM:
                raise ValueError("fixture text does not fit on one page")
            draw.text(
                (PAGE_WIDTH - MARGIN_X, y),
                line,
                fill=18,
                font=font,
                anchor="ra",
                direction="rtl",
                language="he",
            )
            y += line_height + LINE_GAP
        y += PARAGRAPH_GAP

    return image.convert("RGB")


def render_fixture(
    manifest_path: Path,
    output_dir: Path,
    font_path: Path,
    expected_font_sha256: str | None = None,
) -> dict[str, Any]:
    manifest = load_expected_manifest(manifest_path)
    if not font_path.is_file():
        raise ValueError(f"font file does not exist: {font_path}")
    font_sha256 = sha256_file(font_path)
    if expected_font_sha256 and font_sha256 != expected_font_sha256.lower():
        raise ValueError("font SHA-256 does not match --expected-font-sha256")

    output_dir.mkdir(parents=True, exist_ok=True)
    body_font = ImageFont.truetype(str(font_path), BODY_FONT_SIZE, layout_engine=ImageFont.Layout.RAQM)
    title_font = ImageFont.truetype(
        str(font_path),
        TITLE_FONT_SIZE,
        layout_engine=ImageFont.Layout.RAQM,
    )

    pages: list[dict[str, Any]] = []
    for index, page in enumerate(manifest["pages"], start=1):
        output_path = output_dir / page["source_name"]
        image = render_page(
            text=page["expected_text"],
            body_font=body_font,
            title_font=title_font,
            seed=20260805 + index,
        )
        image.save(output_path, format="PNG", optimize=False, compress_level=9)
        pages.append(
            {
                "source_name": page["source_name"],
                "sha256": sha256_file(output_path),
                "width": image.width,
                "height": image.height,
            }
        )

    render_manifest = {
        "schema_version": 1,
        "renderer_version": RENDERER_VERSION,
        "source_manifest": manifest_path.name,
        "font": {
            "filename": font_path.name,
            "sha256": font_sha256,
            "size": BODY_FONT_SIZE,
            "title_size": TITLE_FONT_SIZE,
        },
        "pillow_version": pillow_version,
        "page": {
            "width": PAGE_WIDTH,
            "height": PAGE_HEIGHT,
            "mode": "RGB",
        },
        "pages": pages,
        "human_readability_review": "required_before_gpu_run",
    }
    metadata_path = output_dir / "render_manifest.json"
    metadata_path.write_text(
        json.dumps(render_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return render_manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render the deterministic synthetic ten-page Hebrew viability fixture."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--font-path", type=Path, required=True)
    parser.add_argument("--expected-font-sha256")
    args = parser.parse_args()

    render_fixture(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        font_path=args.font_path,
        expected_font_sha256=args.expected_font_sha256,
    )
    print(args.output_dir / "render_manifest.json")


if __name__ == "__main__":
    main()
