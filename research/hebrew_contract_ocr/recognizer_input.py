from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence

import numpy as np
from PIL import Image, UnidentifiedImageError

from .dataset_contract import (
    CharsetContract,
    DatasetContractError,
    load_charset,
    normalize_text,
    read_jsonl,
    unknown_characters,
)
from .text_order import TextOrderError, logical_to_visual_rtl


RECOGNIZER_HEIGHT = 64
MAX_LINE_PIXELS = 4_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class RecognizerInputError(ValueError):
    pass


@dataclass(frozen=True)
class LineExample:
    sample_id: str
    image_path: Path
    text: str
    image_sha256: str | None = None
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class RecognizerBatch:
    sample_ids: tuple[str, ...]
    texts: tuple[str, ...]
    pixels: np.ndarray
    input_widths: np.ndarray
    targets: np.ndarray
    target_lengths: np.ndarray


def _safe_image_path(dataset_root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RecognizerInputError("image must be a safe relative POSIX path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise RecognizerInputError("image must be a safe relative POSIX path")
    try:
        root = dataset_root.resolve(strict=True)
        path = dataset_root.joinpath(*relative.parts).resolve(strict=True)
        path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise RecognizerInputError(f"image is missing or escapes dataset root: {value}") from exc
    if not path.is_file():
        raise RecognizerInputError(f"image is not a file: {value}")
    return path


def _validated_text(value: object, charset: CharsetContract, sample_id: str) -> str:
    try:
        text = normalize_text(value)  # type: ignore[arg-type]
    except DatasetContractError as exc:
        raise RecognizerInputError(f"invalid text for {sample_id}: {exc}") from exc
    if not text:
        raise RecognizerInputError(f"empty text for {sample_id}")
    unknown = unknown_characters(text, charset)
    if unknown:
        rendered = " ".join(f"U+{ord(character):04X}" for character in unknown)
        raise RecognizerInputError(f"unknown characters for {sample_id}: {rendered}")
    return text


def load_manifest_lines(
    manifest_path: Path,
    dataset_root: Path,
    *,
    charset: CharsetContract | None = None,
    split: str | None = None,
) -> tuple[LineExample, ...]:
    if split is not None and split not in {"train", "validation", "test"}:
        raise RecognizerInputError(f"unknown split: {split}")
    charset = charset or load_charset()
    examples: list[LineExample] = []
    seen_ids: set[str] = set()
    for row_number, row in enumerate(read_jsonl(manifest_path), start=1):
        if split is not None and row.get("split") != split:
            continue
        image_value = row.get("image")
        image_path = _safe_image_path(dataset_root, image_value)
        sample_id_value = row.get("sample_id") or image_value
        if not isinstance(sample_id_value, str):
            raise RecognizerInputError(f"sample_id must be a string on row {row_number}")
        sample_id = sample_id_value.strip()
        if not sample_id or sample_id in seen_ids:
            raise RecognizerInputError(f"missing or duplicate sample_id on row {row_number}")
        seen_ids.add(sample_id)
        text = _validated_text(row.get("text"), charset, sample_id)
        image_sha256 = row.get("image_sha256")
        if image_sha256 is not None and (
            not isinstance(image_sha256, str) or SHA256_RE.fullmatch(image_sha256) is None
        ):
            raise RecognizerInputError(f"invalid image_sha256 for {sample_id}")
        width, height = row.get("width"), row.get("height")
        if (width is None) != (height is None):
            raise RecognizerInputError(f"width and height must appear together for {sample_id}")
        if width is not None and (
            isinstance(width, bool)
            or isinstance(height, bool)
            or not isinstance(width, int)
            or not isinstance(height, int)
            or width <= 0
            or height <= 0
        ):
            raise RecognizerInputError(f"invalid dimensions for {sample_id}")
        examples.append(
            LineExample(sample_id, image_path, text, image_sha256, width, height)
        )
    if not examples:
        raise RecognizerInputError("manifest selection contains no line examples")
    return tuple(examples)


def encode_text(
    text: str,
    charset: CharsetContract | None = None,
    *,
    rtl: bool = True,
) -> np.ndarray:
    charset = charset or load_charset()
    normalized = _validated_text(text, charset, "text")
    try:
        target_text = logical_to_visual_rtl(normalized) if rtl else normalized
    except TextOrderError as exc:
        raise RecognizerInputError(f"unsupported CTC target order: {exc}") from exc
    return np.asarray(
        [charset.character_to_id[character] for character in target_text],
        dtype=np.int64,
    )


def _adapt_image(example: LineExample, target_height: int) -> np.ndarray:
    try:
        image_bytes = example.image_path.read_bytes()
    except OSError as exc:
        raise RecognizerInputError(f"could not read image for {example.sample_id}") from exc
    if example.image_sha256 is not None:
        digest = hashlib.sha256(image_bytes).hexdigest()
        if digest != example.image_sha256:
            raise RecognizerInputError(f"image hash mismatch for {example.sample_id}")
    try:
        with io.BytesIO(image_bytes) as buffer, Image.open(buffer) as image:
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > MAX_LINE_PIXELS:
                raise RecognizerInputError(f"unsafe image dimensions for {example.sample_id}")
            if image.mode != "L":
                raise RecognizerInputError(f"image must use grayscale L for {example.sample_id}")
            if example.width is not None and (width, height) != (example.width, example.height):
                raise RecognizerInputError(f"image dimensions mismatch for {example.sample_id}")
            image.load()
            target_width = max(1, int(round(width * target_height / height)))
            resized = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            grayscale = np.asarray(resized, dtype=np.float32)
    except Image.DecompressionBombError as exc:
        raise RecognizerInputError(f"unsafe image for {example.sample_id}") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise RecognizerInputError(f"could not decode image for {example.sample_id}") from exc
    return 1.0 - grayscale / 255.0


def prepare_batch(
    examples: Sequence[LineExample],
    *,
    charset: CharsetContract | None = None,
    target_height: int = RECOGNIZER_HEIGHT,
) -> RecognizerBatch:
    if not examples:
        raise RecognizerInputError("batch must contain at least one example")
    if target_height != RECOGNIZER_HEIGHT:
        raise RecognizerInputError(f"recognizer height must be {RECOGNIZER_HEIGHT}")
    charset = charset or load_charset()
    images = [_adapt_image(example, target_height) for example in examples]
    texts = [_validated_text(example.text, charset, example.sample_id) for example in examples]
    targets = [encode_text(text, charset) for text in texts]
    widths = np.asarray([image.shape[1] for image in images], dtype=np.int64)
    batch = np.zeros((len(images), 1, target_height, int(widths.max())), dtype=np.float32)
    for index, image in enumerate(images):
        batch[index, 0, :, : image.shape[1]] = image
    return RecognizerBatch(
        sample_ids=tuple(example.sample_id for example in examples),
        texts=tuple(texts),
        pixels=batch,
        input_widths=widths,
        targets=np.concatenate(targets),
        target_lengths=np.asarray([len(target) for target in targets], dtype=np.int64),
    )
