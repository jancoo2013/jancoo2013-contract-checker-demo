"""Deterministic PII redaction for Hebrew rental-contract text.

The helpers in this module intentionally avoid logging or returning any side
channel with original personal data. They preserve commercial/legal terms while
removing common identifiers before text is sent to an LLM.
"""

from __future__ import annotations

import re

NAME_PLACEHOLDER = "[ИМЯ УДАЛЕНО]"
ID_PLACEHOLDER = "[ID УДАЛЁН]"
PHONE_PLACEHOLDER = "[ТЕЛЕФОН УДАЛЁН]"
EMAIL_PLACEHOLDER = "[EMAIL УДАЛЁН]"
BANK_PLACEHOLDER = "[БАНКОВСКИЕ ДАННЫЕ УДАЛЕНЫ]"
ADDRESS_PLACEHOLDER = "[АДРЕС УДАЛЁН]"

_HEBREW = r"\u0590-\u05FF"
_LINE_VALUE = r"[^,\n.;]{1,90}"


def redact_emails(text: str) -> str:
    """Replace email addresses without removing unrelated Latin words."""

    return re.sub(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", EMAIL_PLACEHOLDER, text)


def redact_phone_numbers(text: str) -> str:
    """Replace Israeli-looking phone numbers, including mobile and landline forms."""

    phone_pattern = re.compile(
        r"(?<!\d)(?:\+972[\s-]?|0)(?:5\d|[23489]|7[0-9])[\s-]?\d{3}[\s-]?\d{4}(?!\d)"
    )
    return phone_pattern.sub(PHONE_PLACEHOLDER, text)


def redact_israeli_ids(text: str) -> str:
    """Replace Israeli ID values in labeled contexts and standalone 8-9 digit IDs.

    The standalone pass deliberately targets only compact 8-9 digit values so it
    does not consume dates, rent amounts, deposits, guarantees, or penalties.
    """

    labeled = re.compile(r"(?P<label>ת\.?ז\.?|תז|מספר\s+זהות)\s*[:#\-]?\s*\d[\d\s-]{6,12}\d")
    text = labeled.sub(lambda m: f"{m.group('label')} {ID_PLACEHOLDER}", text)
    return re.sub(r"(?<![\d/.,-])\d{8,9}(?![\d/.,-])", ID_PLACEHOLDER, text)


def redact_bank_details(text: str) -> str:
    """Replace bank account, branch, and labeled bank details conservatively."""

    bank_line = re.compile(r"(?P<label>בנק|חשבון|סניף)\s*[:#\-]?\s*" + _LINE_VALUE)
    text = bank_line.sub(lambda m: f"{m.group('label')} {BANK_PLACEHOLDER}", text)
    iban_like = re.compile(r"\bIL\d{2}[\s-]?(?:\d[\s-]?){10,25}\b", re.IGNORECASE)
    return iban_like.sub(BANK_PLACEHOLDER, text)


def _redact_labeled_value_with_separator(text: str, label_pattern: str, placeholder: str) -> str:
    pattern = re.compile(rf"(?P<label>{label_pattern})\s*[:\-]\s*(?P<value>{_LINE_VALUE})")
    return pattern.sub(lambda m: f"{m.group('label')} {placeholder}", text)

def redact_labeled_personal_fields(text: str) -> str:
    """Redact common Hebrew labels for names, parties, addresses, IDs, and phones.

    Labels must be field-like (usually with ':' or '-') so role words inside
    substantive clauses, such as "המשכיר יהיה אחראי", are preserved.
    """

    text = _redact_labeled_value_with_separator(text, r"כתובת", ADDRESS_PLACEHOLDER)
    text = _redact_labeled_value_with_separator(
        text, r"שם(?:\s+(?:המשכיר|השוכר))?|המשכיר|השוכר|מיופה כוח", NAME_PLACEHOLDER
    )
    text = re.sub(r"(טלפון)\s*[:\-]?\s*[^,\n.;]{5,30}", rf"\1 {PHONE_PLACEHOLDER}", text)
    text = re.sub(r"(ת\.?ז\.?|תז|מספר\s+זהות)\s*[:\-]?\s*[^,\n.;]{{5,30}}", rf"\1 {ID_PLACEHOLDER}", text)
    return text


def redact_personal_data(text: str) -> str:
    """Run all deterministic redactors in a safe order."""

    redacted = text
    redacted = redact_emails(redacted)
    redacted = redact_phone_numbers(redacted)
    redacted = redact_israeli_ids(redacted)
    redacted = redact_bank_details(redacted)
    redacted = redact_labeled_personal_fields(redacted)
    return redacted
