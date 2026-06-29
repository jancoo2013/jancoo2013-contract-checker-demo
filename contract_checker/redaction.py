"""Deterministic PII redaction for Hebrew rental-contract text.

The helpers in this module intentionally avoid logging or returning any side
channel with original personal data. They preserve commercial/legal terms while
removing common identifiers before text is sent to an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

NAME_PLACEHOLDER = "[ИМЯ УДАЛЕНО]"
ID_PLACEHOLDER = "[ID УДАЛЁН]"
PHONE_PLACEHOLDER = "[ТЕЛЕФОН УДАЛЁН]"
EMAIL_PLACEHOLDER = "[EMAIL УДАЛЁН]"
BANK_PLACEHOLDER = "[БАНКОВСКИЕ ДАННЫЕ УДАЛЕНЫ]"
ADDRESS_PLACEHOLDER = "[АДРЕС УДАЛЁН]"
SIGNATURE_PLACEHOLDER = "[ПОДПИСЬ УДАЛЕНА]"
GUARANTOR_PLACEHOLDER = "[ДАННЫЕ ПОРУЧИТЕЛЯ УДАЛЕНЫ]"

_HEBREW = r"\u0590-\u05FF"
_LINE_VALUE = r"[^,\n.;]{1,90}"
_FIELD_VALUE = r"[^,\n.;]{1,120}"
_EXPLICIT_LABEL_SEPARATOR = r"\s*[:#*־\-–—]\s*"
_FLEXIBLE_LABEL_SEPARATOR = rf"(?:{_EXPLICIT_LABEL_SEPARATOR}|\s+)"
_STANDALONE_ID_RE = re.compile(r"(?<![\d/.,₪-])\d{8,9}(?![\d/.,₪-])")

_RISK_CONTEXT_MARKERS = (
    "שכר דירה",
    "דמי שכירות",
    "פיקדון",
    "שיק ביטחון",
    "בטוחה",
    "ערבות",
    "שטר חוב",
    "נספח",
    "כתב ערבות",
    "רשימת ציוד",
    "פרוטוקול מסירה",
    "שוכר חלופי",
    "עזיבה מוקדמת",
    "הודעה מראש",
    "בלאי סביר",
    "צביעה",
    "תיקונים",
    "חשבונות",
    "ועד בית",
    "ארנונה",
    "₪",
)

_ID_LABEL_RE = re.compile(r"ת\.?ז\.?|תז|תעודת\s+זהות|מספר\s+זהות")


@dataclass(frozen=True)
class RedactionReport:
    emails: int = 0
    phones: int = 0
    ids: int = 0
    bank_details: int = 0
    addresses: int = 0
    names: int = 0
    signatures: int = 0
    guarantor_details: int = 0

    @property
    def total(self) -> int:
        return (
            self.emails
            + self.phones
            + self.ids
            + self.bank_details
            + self.addresses
            + self.names
            + self.signatures
            + self.guarantor_details
        )


@dataclass(frozen=True)
class RedactionResult:
    redacted_text: str
    report: RedactionReport


def _report_from_counts(counts: dict[str, int]) -> RedactionReport:
    return RedactionReport(**{field: int(counts.get(field, 0)) for field in RedactionReport.__dataclass_fields__})


def _add_count(counts: dict[str, int] | None, field: str, count: int) -> None:
    if counts is not None and count:
        counts[field] = counts.get(field, 0) + count


def _label_pattern(labels: list[str], separator: str = _FLEXIBLE_LABEL_SEPARATOR) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![{_HEBREW}])(?P<label>{'|'.join(labels)})(?P<sep>{separator})(?P<value>{_FIELD_VALUE})"
    )


def _redact_labeled_values(
    text: str,
    labels: list[str],
    placeholder: str,
    report_field: str,
    counts: dict[str, int] | None = None,
    separator: str = _FLEXIBLE_LABEL_SEPARATOR,
) -> str:
    pattern = _label_pattern(labels, separator)

    def replace(match: re.Match[str]) -> str:
        value = match.group("value")
        if any(
            placeholder in value
            for placeholder in (
                NAME_PLACEHOLDER,
                ID_PLACEHOLDER,
                PHONE_PLACEHOLDER,
                EMAIL_PLACEHOLDER,
                BANK_PLACEHOLDER,
                ADDRESS_PLACEHOLDER,
                SIGNATURE_PLACEHOLDER,
                GUARANTOR_PLACEHOLDER,
            )
        ):
            return match.group(0)
        _add_count(counts, report_field, 1)
        return f"{match.group('label')} {placeholder}"

    return pattern.sub(replace, text)


def redact_emails(text: str, counts: dict[str, int] | None = None) -> str:
    """Replace email addresses without removing unrelated Latin words."""

    text, count = re.subn(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", EMAIL_PLACEHOLDER, text)
    _add_count(counts, "emails", count)
    return text


def redact_phone_numbers(text: str, counts: dict[str, int] | None = None) -> str:
    """Replace Israeli-looking phone numbers, including mobile and landline forms."""

    phone_pattern = re.compile(
        r"(?<!\d)(?:\+972[\s-]?|0)(?:5\d|[23489]|7[0-9])[\s-]?\d{3}[\s-]?\d{4}(?!\d)"
    )
    text, count = phone_pattern.subn(PHONE_PLACEHOLDER, text)
    _add_count(counts, "phones", count)
    return text


def _redact_standalone_ids(text: str, counts: dict[str, int] | None = None) -> str:
    redacted_lines: list[str] = []
    total = 0
    for line in text.splitlines(keepends=True):
        has_risk_context = any(marker in line for marker in _RISK_CONTEXT_MARKERS)
        if has_risk_context and not _ID_LABEL_RE.search(line):
            redacted_lines.append(line)
            continue
        redacted_line, count = _STANDALONE_ID_RE.subn(ID_PLACEHOLDER, line)
        total += count
        redacted_lines.append(redacted_line)
    _add_count(counts, "ids", total)
    return "".join(redacted_lines)


def redact_israeli_ids(text: str, counts: dict[str, int] | None = None) -> str:
    """Replace Israeli ID values in labeled contexts and standalone 8-9 digit IDs.

    The standalone pass deliberately targets only compact 8-9 digit values so it
    does not consume dates, rent amounts, deposits, guarantees, or penalties.
    """

    id_labels = [
        r"תעודת\s+זהות",
        r"ת\.?ז\.?(?!\s*ערב)",
        r"תז(?!\s*ערב)",
        r"מספר\s+זהות(?!\s*ערב)",
    ]
    text = _redact_labeled_values(text, id_labels, ID_PLACEHOLDER, "ids", counts)
    return _redact_standalone_ids(text, counts)


def redact_bank_details(text: str, counts: dict[str, int] | None = None) -> str:
    """Replace bank account, branch, and labeled bank details conservatively."""

    bank_labels = [
        r"פרטי\s+בנק",
        r"חשבון\s+בנק",
        r"מספר\s+חשבון",
        r"בנק",
        r"סניף",
        r"מספר\s+שיק",
        r"מספר\s+צ'?ק",
        r"מס[׳']?\s+שיק",
        r"שיק\s+מס[׳']?",
        r"שיק\s+מספר",
        r"צ'?ק\s+מספר",
    ]
    text = _redact_labeled_values(text, bank_labels, BANK_PLACEHOLDER, "bank_details", counts)
    iban_like = re.compile(r"\bIL\d{2}[\s-]?(?:\d[\s-]?){10,25}\b", re.IGNORECASE)
    text, count = iban_like.subn(BANK_PLACEHOLDER, text)
    _add_count(counts, "bank_details", count)
    return text


def _redact_labeled_value_with_separator(text: str, label_pattern: str, placeholder: str) -> str:
    pattern = re.compile(rf"(?P<label>{label_pattern})\s*[:\-]\s*(?P<value>{_LINE_VALUE})")
    return pattern.sub(lambda m: f"{m.group('label')} {placeholder}", text)


def redact_labeled_personal_fields(text: str, counts: dict[str, int] | None = None) -> str:
    """Redact common Hebrew labels for names, parties, addresses, IDs, and phones.

    Labels must be field-like (usually with ':' or '-') so role words inside
    substantive clauses, such as "המשכיר יהיה אחראי", are preserved.
    """

    guarantor_labels = [
        r"שם\s+הערב",
        r"ת\.?ז\.?\s+ערב",
        r"תז\s+ערב",
        r"מספר\s+זהות\s+ערב",
    ]
    specific_name_labels = [
        r"שם\s+בעל\s+הדירה",
        r"שם\s+המשכיר",
        r"שם\s+השוכר",
        r"שם\s+הסוכן",
        r"שם\s+המתווך",
        r"מיופה\s+כוח",
    ]
    generic_name_labels = [
        r"סוכן",
        r"מתווך",
        r"שם(?!\s+הערב)",
    ]
    address_labels = [r"כתובת"]
    phone_labels = [r"טלפון", r"נייד"]
    email_labels = [r"דואר\s+אלקטרוני", r"מייל", r"אימייל"]
    signature_labels = [r"חתימה", r"חתימת\s+השוכר", r"חתימת\s+המשכיר", r"חתימות"]

    text = _redact_labeled_values(text, guarantor_labels, GUARANTOR_PLACEHOLDER, "guarantor_details", counts)
    text = _redact_labeled_values(text, address_labels, ADDRESS_PLACEHOLDER, "addresses", counts)
    text = _redact_labeled_values(text, phone_labels, PHONE_PLACEHOLDER, "phones", counts)
    text = _redact_labeled_values(text, email_labels, EMAIL_PLACEHOLDER, "emails", counts)
    text = _redact_labeled_values(text, specific_name_labels, NAME_PLACEHOLDER, "names", counts)
    text = _redact_labeled_values(
        text,
        generic_name_labels,
        NAME_PLACEHOLDER,
        "names",
        counts,
        separator=_EXPLICIT_LABEL_SEPARATOR,
    )
    text = _redact_labeled_values(text, signature_labels, SIGNATURE_PLACEHOLDER, "signatures", counts)
    return text


def redact_personal_data_with_report(text: str) -> RedactionResult:
    """Run deterministic redactors and return only safe category counts."""

    counts: dict[str, int] = {}
    redacted = text
    redacted = redact_labeled_personal_fields(redacted, counts)
    redacted = redact_emails(redacted, counts)
    redacted = redact_phone_numbers(redacted, counts)
    redacted = redact_israeli_ids(redacted, counts)
    redacted = redact_bank_details(redacted, counts)
    return RedactionResult(redacted_text=redacted, report=_report_from_counts(counts))


def redact_personal_data(text: str) -> str:
    """Run all deterministic redactors in a safe order."""

    return redact_personal_data_with_report(text).redacted_text
