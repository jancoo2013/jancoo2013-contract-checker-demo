from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .dataset_contract import CharsetContract, load_charset


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

    The recognizer scans source pixels left-to-right. For Hebrew lines, only each
    sample's valid time prefix is reversed before CTC collapse; padded time steps
    are never moved into or decoded as content.
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
    for batch_index, length_value in enumerate(lengths):
        length = int(length_value)
        path = best_paths[:length, batch_index]
        if rtl:
            path = path[::-1]
        class_ids = _collapse_path(path, charset.ctc_blank_id)
        text = "".join(charset.characters[class_id - 1] for class_id in class_ids)
        decoded.append(DecodedLine(text=text, class_ids=class_ids, input_length=length))
    return tuple(decoded)
