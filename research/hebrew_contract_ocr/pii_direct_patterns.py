"""Bounded direct-value PII pattern evidence for already available text."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True, slots=True)
class DirectValueMatch:
    """A value-free match reference into the original input string."""

    pii_class: str
    start: int
    end: int
    detector_id: str


_EMAIL_RE = re.compile(
    r"(?<![A-Z0-9._%+-])"
    r"[A-Z0-9](?:[A-Z0-9._%+-]{0,62}[A-Z0-9])?@"
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}"
    r"(?![A-Z0-9-])",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+972[ -]?|0)(?:5\d|[23489]|7[0-9])[ -]?\d{3}[ -]?\d{4}(?!\d)"
)
_ISRAELI_ID_RE = re.compile(r"(?<!\d)\d(?:[ -]?\d){8}(?!\d)")
_ISRAELI_IBAN_RE = re.compile(r"(?<![A-Z0-9])IL(?:[ -]?\d){21}(?![A-Z0-9])", re.IGNORECASE)
_SEPARATORS = frozenset({" ", "-"})

_PRIORITY = ("bank_identifier", "email", "phone", "israeli_id")


def _without_separators(value: str) -> str:
    return "".join(character for character in value if character not in _SEPARATORS)


def _valid_email(value: str) -> bool:
    local_part = value.split("@", 1)[0]
    return ".." not in local_part and not local_part.startswith(".") and not local_part.endswith(".")


def _valid_israeli_id(value: str) -> bool:
    digits = _without_separators(value)
    if len(digits) != 9 or not digits.isascii() or not digits.isdigit():
        return False
    total = 0
    for index, character in enumerate(digits):
        product = int(character) * (1 if index % 2 == 0 else 2)
        total += product if product < 10 else product - 9
    return total % 10 == 0


def _valid_israeli_iban(value: str) -> bool:
    normalized = _without_separators(value).upper()
    if len(normalized) != 23 or not normalized.startswith("IL") or not normalized[2:].isdigit():
        return False
    rearranged = normalized[4:] + normalized[:4]
    remainder = 0
    for character in rearranged:
        digits = str(ord(character) - ord("A") + 10) if character.isalpha() else character
        for digit in digits:
            remainder = (remainder * 10 + int(digit)) % 97
    return remainder == 1


def _is_partial_separated_number(text: str, start: int, end: int) -> bool:
    before = start >= 2 and text[start - 1] in _SEPARATORS and text[start - 2].isdigit()
    after = end + 1 < len(text) and text[end] in _SEPARATORS and text[end + 1].isdigit()
    return before or after


def _collect_matches(text: str) -> dict[str, list[DirectValueMatch]]:
    matches: dict[str, list[DirectValueMatch]] = {pii_class: [] for pii_class in _PRIORITY}
    detector_ids = {
        "bank_identifier": "direct-israeli-iban-v0",
        "email": "direct-email-v0",
        "phone": "direct-israeli-phone-v0",
        "israeli_id": "direct-israeli-id-v0",
    }
    patterns = {
        "bank_identifier": (_ISRAELI_IBAN_RE, _valid_israeli_iban),
        "email": (_EMAIL_RE, _valid_email),
        "phone": (_PHONE_RE, lambda _value: True),
        "israeli_id": (_ISRAELI_ID_RE, _valid_israeli_id),
    }
    for pii_class in _PRIORITY:
        pattern, validator = patterns[pii_class]
        for found in pattern.finditer(text):
            if pii_class == "israeli_id" and _is_partial_separated_number(text, found.start(), found.end()):
                continue
            if validator(found.group(0)):
                matches[pii_class].append(
                    DirectValueMatch(pii_class, found.start(), found.end(), detector_ids[pii_class])
                )
    return matches


def _overlaps(left: DirectValueMatch, right: DirectValueMatch) -> bool:
    return left.start < right.end and right.start < left.end


def find_direct_value_matches(text: str) -> tuple[DirectValueMatch, ...]:
    """Return non-overlapping high-confidence matches without retaining values."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text:
        return ()

    accepted: list[DirectValueMatch] = []
    matches = _collect_matches(text)
    for pii_class in _PRIORITY:
        for match in sorted(matches[pii_class], key=lambda item: (item.start, item.end, item.detector_id)):
            if not any(_overlaps(match, existing) for existing in accepted):
                accepted.append(match)
    return tuple(sorted(accepted, key=lambda item: (item.start, item.end, item.detector_id)))


def make_direct_value_evidence(
    match: DirectValueMatch,
    evidence_id: str,
    geometry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a value-free direct-value evidence record for the candidate schema."""
    if not isinstance(match, DirectValueMatch):
        raise TypeError("match must be a DirectValueMatch")
    if not isinstance(evidence_id, str):
        raise TypeError("evidence_id must be a string")
    record: dict[str, Any] = {
        "evidence_id": evidence_id,
        "family": "direct_value",
        "detector_id": match.detector_id,
    }
    if geometry is not None:
        record["geometry"] = deepcopy(geometry)
    return record


__all__ = ["DirectValueMatch", "find_direct_value_matches", "make_direct_value_evidence"]
