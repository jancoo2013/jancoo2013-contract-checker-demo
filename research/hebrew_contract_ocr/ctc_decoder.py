from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .dataset_contract import CharsetContract, load_charset
from .text_order import TextOrderError, visual_to_logical_rtl


class CTCDecoderError(ValueError):
    pass


@dataclass(frozen=True)
class DecodedLine:
    text: str
    class_ids: tuple[int, ...]
    input_length: int


def _validated_lengths(values: Sequence[int] | np.ndarray, batch: int, time: int) -> np.ndarray:
    lengths = np.asarray(values)
    if lengths.ndim != 1 or lengths.shape[0] != batch:
        raise CTCDecoderError("input_lengths must have shape [batch]")
    if lengths.dtype.kind not in {"i", "u"}:
        raise CTCDecoderError("input_lengths must contain integers")
    lengths = lengths.astype(np.int64, copy=False)
    if np.any(lengths <= 0) or np.any(lengths > time):
        raise CTCDecoderError("every input length must be within [1, time]")
    return lengths


def _collapse_path(path: np.ndarray, blank_id: int) -> tuple[int, ...]:
    result: list[int] = []
    previous: int | None = None
    for value in path:
        class_id = int(value)
        if class_id != previous and class_id != blank_id:
            result.append(class_id)
        previous = class_id
    return tuple(result)


def greedy_decode(
    logits: np.ndarray,
    input_lengths: Sequence[int] | np.ndarray,
    *,
    charset: CharsetContract | None = None,
    rtl: bool = True,
) -> tuple[DecodedLine, ...]:
    """Decode `[time, batch, classes]` logits into logical-order text.

    CTC repeat collapse and blank removal happen in the recognizer's left-to-right
    source scan order. RTL lines are then reordered by the bounded text-order v0
    contract; padded time steps are never decoded as content.
    """

    values = np.asarray(logits)
    if values.ndim != 3:
        raise CTCDecoderError("logits must have shape [time, batch, classes]")
    if values.dtype.kind not in {"f", "i", "u"} or not np.all(np.isfinite(values)):
        raise CTCDecoderError("logits must contain finite numeric values")
    time, batch, classes = values.shape
    if time <= 0 or batch <= 0:
        raise CTCDecoderError("time and batch dimensions must be non-empty")
    charset = charset or load_charset()
    if charset.ctc_blank_id != 0 or classes != len(charset.characters) + 1:
        raise CTCDecoderError("logit class count must match charset plus CTC blank")
    lengths = _validated_lengths(input_lengths, batch, time)
    best_paths = values.argmax(axis=2)

    decoded: list[DecodedLine] = []
    character_to_id = charset.character_to_id
    for batch_index, length_value in enumerate(lengths):
        length = int(length_value)
        visual_class_ids = _collapse_path(
            best_paths[:length, batch_index],
            charset.ctc_blank_id,
        )
        visual_text = "".join(
            charset.characters[class_id - 1] for class_id in visual_class_ids
        )
        try:
            text = visual_to_logical_rtl(visual_text) if rtl else visual_text
        except TextOrderError as exc:
            raise CTCDecoderError(f"unsupported RTL text order: {exc}") from exc
        class_ids = tuple(character_to_id[character] for character in text)
        decoded.append(
            DecodedLine(text=text, class_ids=class_ids, input_length=length)
        )
    return tuple(decoded)
