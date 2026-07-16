from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, features


FONT_SUFFIXES = {".otf", ".ttc", ".ttf"}
HEBREW_ALPHABET = "אבגדהוזחטיכלמנסעפצקרשתךםןףץ"


@dataclass(frozen=True)
class TextSample:
    text: str
    template_id: str
    text_source: str = "synthetic_template"


@dataclass(frozen=True)
class RenderParameters:
    font: str
    font_size: int
    foreground: int
    background: int
    rotation_degrees: float
    blur_radius: float
    noise_sigma: float
    contrast: float
    resolution_scale: float
    jpeg_quality: int


def _clause_number(rng: random.Random) -> str:
    major = rng.randint(1, 18)
    depth = rng.choices((1, 2, 3), weights=(3, 5, 1), k=1)[0]
    return ".".join(str(rng.randint(1, 9)) if part else str(major) for part in range(depth))


def _date(rng: random.Random) -> str:
    return f"{rng.randint(1, 28):02d}.{rng.randint(1, 12):02d}.{rng.randint(2024, 2032)}"


def _amount(rng: random.Random) -> str:
    return f"{rng.randrange(2500, 12501, 100):,}"


Template = tuple[str, Callable[[random.Random], str]]


TEMPLATES: tuple[Template, ...] = (
    ("lease_period", lambda r: f"תקופת השכירות תהיה {r.choice((12, 18, 24, 36))} חודשים"),
    ("monthly_rent", lambda r: f"דמי השכירות החודשיים יהיו בסך {_amount(r)} ש\"ח"),
    ("payment_day", lambda r: f"השוכר ישלם את דמי השכירות עד ליום {r.randint(1, 10)} בכל חודש"),
    ("reasonable_condition", lambda r: "השוכר מתחייב לשמור על הדירה במצב תקין וסביר"),
    ("repairs", lambda r: "המשכיר מתחייב לתקן כל תקלה שאינה נובעת משימוש בלתי סביר"),
    ("as_is", lambda r: "הצדדים מסכימים כי הדירה תימסר במצב AS-IS"),
    ("advance_notice", lambda r: f"הודעה מראש על סיום ההסכם תימסר {r.choice((30, 45, 60, 90))} ימים מראש"),
    ("utilities", lambda r: "הארנונה, המים והחשמל יחולו על השוכר בתקופת השכירות"),
    ("assignment", lambda r: "אין להעביר את זכויות השוכר לצד שלישי ללא הסכמה מראש ובכתב"),
    ("deposit_return", lambda r: f"הערבות תוחזר לשוכר בתוך {r.choice((7, 14, 30, 60))} ימים מתום השכירות"),
    ("signed_on", lambda r: f"הסכם זה נערך ונחתם ביום {_date(r)}"),
    ("definitions_landlord", lambda r: "להלן - \"המשכיר\" (מצד אחד)"),
    ("definitions_tenant", lambda r: "להלן - \"השוכר\" (מצד שני)"),
    ("id_fields", lambda r: "שם מלא: __________ ת.ז.: __________ מרחוב __________"),
    ("security", lambda r: f"השוכר ימסור למשכיר שיק ביטחון בסך {_amount(r)} ש\"ח"),
    ("ordinary_wear", lambda r: "השוכר לא יישא באחריות לבלאי סביר הנובע משימוש רגיל בדירה"),
    ("appendix", lambda r: f"נספח {r.choice(('א', 'ב', 'ג'))} להסכם השכירות מהווה חלק בלתי נפרד ממנו"),
    ("heading", lambda r: r.choice(("תקופת השכירות", "דמי השכירות", "מיסים ותשלומים", "בטחונות", "אחריות השוכר"))),
)


def normalize_single_line(value: str) -> str:
    return " ".join(value.replace("\ufeff", "").split())


def build_synthetic_text(rng: random.Random) -> TextSample:
    template_id, renderer = rng.choice(TEMPLATES)
    text = renderer(rng)
    if rng.random() < 0.72:
        text = f"{_clause_number(rng)} {text}"
    return TextSample(text=normalize_single_line(text), template_id=template_id)


def load_corpus(path: Path, max_characters: int = 220) -> list[TextSample]:
    samples: list[TextSample] = []
    with path.open(encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            if not raw_line.strip():
                continue
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"expected an object on {path}:{line_number}")
            text = normalize_single_line(str(row.get("text") or ""))
            if not text or len(text) > max_characters:
                continue
            status = normalize_single_line(str(row.get("label_status") or "unversioned"))
            samples.append(
                TextSample(
                    text=text,
                    template_id=f"corpus_line_{line_number}",
                    text_source=f"local_corpus:{status}",
                )
            )
    if not samples:
        raise ValueError(f"no usable text rows found in {path}")
    return samples


def _glyph_signature(font: ImageFont.FreeTypeFont, character: str) -> tuple[tuple[int, int], bytes]:
    mask = font.getmask(character)
    return mask.size, bytes(mask)


def font_supports_hebrew(path: Path) -> bool:
    try:
        font = ImageFont.truetype(str(path), 32)
    except OSError:
        return False
    missing_glyph = _glyph_signature(font, "\u0378")
    return all(_glyph_signature(font, character) != missing_glyph for character in HEBREW_ALPHABET)


def discover_fonts(font_dir: Path) -> list[Path]:
    if not font_dir.is_dir():
        raise ValueError(f"font directory does not exist: {font_dir}")
    candidates = sorted(
        path
        for path in font_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in FONT_SUFFIXES
    )
    if not candidates:
        raise ValueError(f"no .ttf, .ttc or .otf fonts found under {font_dir}")
    fonts = [path for path in candidates if font_supports_hebrew(path)]
    if not fonts:
        raise ValueError(f"no fonts with complete Hebrew alphabet coverage found under {font_dir}")
    return fonts


def choose_render_parameters(rng: random.Random, font: Path, line_height: int) -> RenderParameters:
    return RenderParameters(
        font=str(font),
        font_size=rng.randint(max(16, int(line_height * 0.43)), max(17, int(line_height * 0.62))),
        foreground=rng.randint(15, 75),
        background=rng.randint(220, 252),
        rotation_degrees=round(rng.uniform(-1.2, 1.2), 3),
        blur_radius=round(rng.uniform(0.0, 0.75), 3),
        noise_sigma=round(rng.uniform(0.0, 5.0), 3),
        contrast=round(rng.uniform(0.82, 1.18), 3),
        resolution_scale=round(rng.uniform(0.68, 1.0), 3),
        jpeg_quality=rng.randint(58, 96),
    )


def choose_split(text: str, seed: int, validation_fraction: float) -> str:
    digest = hashlib.sha256(f"{seed}\0{text}".encode("utf-8")).digest()
    fraction = int.from_bytes(digest[:8], byteorder="big") / 2**64
    return "validation" if fraction < validation_fraction else "train"


def render_line(
    text: str,
    parameters: RenderParameters,
    line_height: int,
    rng: random.Random,
) -> Image.Image:
    if not features.check("raqm"):
        raise RuntimeError(
            "Pillow was built without libraqm. Hebrew RTL and mixed Hebrew/Latin text cannot be rendered safely."
        )

    font = ImageFont.truetype(parameters.font, parameters.font_size)
    probe = Image.new("L", (16, 16), parameters.background)
    probe_draw = ImageDraw.Draw(probe)
    bbox = probe_draw.textbbox(
        (0, 0),
        text,
        font=font,
        direction="rtl",
        language="he",
        stroke_width=0,
    )
    text_width = max(1, bbox[2] - bbox[0])
    horizontal_padding = rng.randint(14, 34)
    width = max(96, text_width + 2 * horizontal_padding)
    image = Image.new("L", (width, line_height), parameters.background)
    draw = ImageDraw.Draw(image)
    draw.text(
        (width - horizontal_padding, line_height / 2),
        text,
        fill=parameters.foreground,
        font=font,
        anchor="rm",
        direction="rtl",
        language="he",
    )

    image = image.rotate(
        parameters.rotation_degrees,
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor=parameters.background,
    )
    if parameters.resolution_scale < 0.999:
        reduced = image.resize(
            (max(1, round(width * parameters.resolution_scale)), max(1, round(line_height * parameters.resolution_scale))),
            Image.Resampling.LANCZOS,
        )
        image = reduced.resize((width, line_height), Image.Resampling.BICUBIC)
    if parameters.blur_radius > 0.02:
        image = image.filter(ImageFilter.GaussianBlur(parameters.blur_radius))
    image = ImageEnhance.Contrast(image).enhance(parameters.contrast)

    if parameters.noise_sigma > 0.02:
        pixels = np.asarray(image, dtype=np.float32)
        np_rng = np.random.default_rng(rng.randrange(2**63))
        pixels += np_rng.normal(0.0, parameters.noise_sigma, size=pixels.shape)
        image = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8), mode="L")

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=parameters.jpeg_quality, optimize=False)
    buffer.seek(0)
    with Image.open(buffer) as compressed:
        return compressed.convert("L")


def _prepare_output(output_dir: Path) -> Path:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


def generate_dataset(
    output_dir: Path,
    fonts: Sequence[Path],
    count: int,
    seed: int,
    line_height: int = 64,
    validation_fraction: float = 0.1,
    corpus: Sequence[TextSample] = (),
    corpus_ratio: float = 0.0,
) -> dict[str, object]:
    if count < 1:
        raise ValueError("count must be at least 1")
    if line_height < 32:
        raise ValueError("line height must be at least 32 pixels")
    if not 0.0 <= validation_fraction < 1.0:
        raise ValueError("validation fraction must be in [0, 1)")
    if not 0.0 <= corpus_ratio <= 1.0:
        raise ValueError("corpus ratio must be in [0, 1]")
    if corpus_ratio and not corpus:
        raise ValueError("corpus ratio is non-zero but no corpus rows were supplied")
    if not fonts:
        raise ValueError("at least one font is required")

    images_dir = _prepare_output(output_dir)
    manifest_path = output_dir / "manifest.jsonl"
    master_rng = random.Random(seed)
    split_counts = {"train": 0, "validation": 0}
    source_counts: dict[str, int] = {}

    with manifest_path.open("w", encoding="utf-8") as manifest:
        for index in range(count):
            sample_seed = master_rng.randrange(2**63)
            rng = random.Random(sample_seed)
            if corpus and rng.random() < corpus_ratio:
                sample = rng.choice(corpus)
            else:
                sample = build_synthetic_text(rng)
            font = rng.choice(fonts)
            parameters = choose_render_parameters(rng, font, line_height)
            image = render_line(sample.text, parameters, line_height, rng)
            image_name = f"line_{index:06d}.png"
            image.save(images_dir / image_name, format="PNG")
            split = choose_split(sample.text, seed, validation_fraction)
            split_counts[split] += 1
            source_counts[sample.text_source] = source_counts.get(sample.text_source, 0) + 1
            row = {
                "image": f"images/{image_name}",
                "text": sample.text,
                "split": split,
                "sample_seed": sample_seed,
                "template_id": sample.template_id,
                "text_source": sample.text_source,
                "render": asdict(parameters),
            }
            manifest.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    summary: dict[str, object] = {
        "schema_version": 1,
        "count": count,
        "seed": seed,
        "line_height": line_height,
        "validation_fraction": validation_fraction,
        "corpus_ratio": corpus_ratio,
        "fonts": [str(path) for path in fonts],
        "splits": split_counts,
        "text_sources": source_counts,
        "manifest": manifest_path.name,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic Hebrew rental-contract line images for custom OCR research."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--font-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260716)
    parser.add_argument("--line-height", type=int, default=64)
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--corpus-jsonl", type=Path)
    parser.add_argument(
        "--corpus-ratio",
        type=float,
        default=0.0,
        help="Fraction of samples whose text comes from --corpus-jsonl; rendering remains synthetic.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fonts = discover_fonts(args.font_dir)
    corpus = load_corpus(args.corpus_jsonl) if args.corpus_jsonl else []
    summary = generate_dataset(
        output_dir=args.output_dir,
        fonts=fonts,
        count=args.count,
        seed=args.seed,
        line_height=args.line_height,
        validation_fraction=args.validation_fraction,
        corpus=corpus,
        corpus_ratio=args.corpus_ratio,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
