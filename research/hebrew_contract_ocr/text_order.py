from __future__ import annotations

import unicodedata


class TextOrderError(ValueError):
    pass


_RTL_BIDI_CLASSES = frozenset({"R", "AL"})
_LTR_BIDI_CLASSES = frozenset({"L", "EN", "AN"})
_MIRRORED_PAIRS = {
    "(": ")",
    ")": "(",
    "[": "]",
    "]": "[",
    "{": "}",
    "}": "{",
    "<": ">",
    ">": "<",
}


def _strong_direction(character: str) -> str | None:
    bidi_class = unicodedata.bidirectional(character)
    if bidi_class in _RTL_BIDI_CLASSES:
        return "rtl"
    if bidi_class in _LTR_BIDI_CLASSES:
        return "ltr"
    return None


def _mirror(text: str) -> str:
    return "".join(_MIRRORED_PAIRS.get(character, character) for character in text)


def _reorder_rtl_token(token: str) -> str:
    return _mirror(token[::-1])


def _reorder_ltr_token(token: str) -> str:
    strong_positions = [
        index
        for index, character in enumerate(token)
        if _strong_direction(character) == "ltr"
    ]
    if not strong_positions:
        return _reorder_rtl_token(token)
    first = strong_positions[0]
    last = strong_positions[-1]
    prefix = token[:first]
    core = token[first : last + 1]
    suffix = token[last + 1 :]
    return _mirror(suffix) + core + _mirror(prefix)


def _reorder_rtl_visual_logical(text: str) -> str:
    if not isinstance(text, str):
        raise TextOrderError("text must be a string")
    if not any(_strong_direction(character) == "rtl" for character in text):
        return text

    reordered: list[str] = []
    for token in reversed(text.split(" ")):
        directions = {
            direction
            for character in token
            if (direction := _strong_direction(character)) is not None
        }
        if directions == {"rtl"}:
            reordered.append(_reorder_rtl_token(token))
        elif directions == {"ltr"}:
            reordered.append(_reorder_ltr_token(token))
        elif not directions:
            reordered.append(_reorder_rtl_token(token))
        else:
            raise TextOrderError(
                "mixed Hebrew and LTR strong characters require an ASCII-space "
                f"boundary in text-order v0: {token!r}"
            )
    return " ".join(reordered)


def visual_to_logical_rtl(text: str) -> str:
    """Convert left-to-right source scan order into logical Unicode order."""

    return _reorder_rtl_visual_logical(text)


def logical_to_visual_rtl(text: str) -> str:
    """Convert logical Unicode into the reversible CTC alignment order."""

    return _reorder_rtl_visual_logical(text)
