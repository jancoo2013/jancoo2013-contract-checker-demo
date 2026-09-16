from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time
from typing import Callable

import fitz

from contract_checker.gemini_engine import (
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiRateLimitError,
    GeminiResponseError,
    analyze_contract_with_gemini,
)
from contract_checker.redaction import NAME_PLACEHOLDER, redact_personal_data_with_report
from contract_checker.schemas import ContractAuditResult
from contract_checker.validator import validate_contract_text

AUTO_MODEL_ROUTE = (
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
)
MAX_PDF_BYTES = 25 * 1024 * 1024
MAX_PAGES = 40
MAX_TEXT_CHARS = 250_000
MIN_TEXT_CHARS = 500

_BODY_START_RE = re.compile(
    r"לפיכך\s+הוסכם[^\n]{0,50}?והותנה\s+בין\s+הצדדים\s+כדלקמן"
)
_END_MARKERS = (
    "ולראיה באו הצדדים על החתום",
    "ולראיה באו הצדדים על החתום:",
)
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+972[\s-]?|0)(?:5\d|[23489]|7[0-9])[\s-]?\d{3}[\s-]?\d{4}(?!\d)")
_ID_RE = re.compile(r"(?<![\d/.,₪-])\d{8,9}(?![\d/.,₪-])")
_IBAN_RE = re.compile(r"\bIL\d{2}[\s-]?(?:\d[\s-]?){10,25}\b", re.IGNORECASE)
_ID_LABEL_RE = re.compile(r"ת\.?\s*ז\.?|תז|תעודת\s+זהות")
_HEBREW_TOKEN_RE = re.compile(r"[\u0590-\u05FF]+(?:['׳״\"][\u0590-\u05FF]+)*")
_HEADER_NAME_STOPWORDS = {
    "בין", "לבין", "באמצעות", "המשכיר", "המשכירה", "השוכר", "השוכרת",
    "משכיר", "משכירה", "שוכר", "שוכרת", "להלן", "מצד", "אחד", "שני",
    "יחד", "לחוד", "אשלא", "עורך", "דין", "אפוטרופוס", "המרכז", "הישראלי",
}


def desktop_dirs() -> list[Path]:
    bases = [Path.home()]
    bases += [Path(value) for key in ("USERPROFILE", "OneDrive", "OneDriveConsumer")
              if (value := os.environ.get(key))]
    return list(dict.fromkeys(base / name for base in bases for name in ("Desktop", "Рабочий стол")))


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    for folder in desktop_dirs():
        path = folder / ".env.local"
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            if raw.strip().startswith("GEMINI_API_KEY="):
                value = raw.split("=", 1)[1].strip().strip("\"'")
                if value:
                    return value
    raise RuntimeError("GEMINI_API_KEY not found. Put .env.local on the Desktop.")


def choose_pdf() -> Path | None:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(
            title="Выберите один договор PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        root.destroy()
    except Exception as exc:
        raise RuntimeError("Windows PDF picker is unavailable") from exc
    return Path(selected) if selected else None


def extract_pdf_text(pdf_path: Path) -> str:
    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        raise RuntimeError("Selected file is not a PDF")
    if pdf_path.stat().st_size > MAX_PDF_BYTES:
        raise RuntimeError("PDF exceeds local analysis size limit")

    with fitz.open(pdf_path) as document:
        if document.page_count < 1 or document.page_count > MAX_PAGES:
            raise RuntimeError("PDF page count is outside local analysis limits")
        parts: list[str] = []
        total = 0
        for page_number, page in enumerate(document, 1):
            text = page.get_text("text") or ""
            total += len(text)
            if total > MAX_TEXT_CHARS:
                raise RuntimeError("Extracted PDF text exceeds local analysis limit")
            parts.append(f"--- СТРАНИЦА {page_number} ---\n{text.strip()}")

    combined = "\n\n".join(parts).strip()
    if len(combined) < MIN_TEXT_CHARS:
        raise RuntimeError("PDF has no usable text layer; OCR is required before this runner can analyze it")
    return combined


def _body_start(text: str) -> tuple[int, str]:
    match = _BODY_START_RE.search(text)
    if not match:
        raise RuntimeError("Could not locate the contract-body start marker; refusing cloud handoff")
    return match.start(), match.group(0)


def _normalized_hebrew_token(token: str) -> str:
    return re.sub(r"['׳״\"]", "", token)


def _candidate_name_tokens(text: str) -> list[str]:
    result: list[str] = []
    for token in _HEBREW_TOKEN_RE.findall(text):
        hebrew_len = len(re.findall(r"[\u0590-\u05FF]", token))
        if hebrew_len < 2:
            continue
        if _normalized_hebrew_token(token) in _HEADER_NAME_STOPWORDS:
            continue
        result.append(token)
    return result


def _header_person_tokens(text: str) -> set[str]:
    start, _ = _body_start(text)
    header = text[:start]
    lines = [line.strip() for line in header.splitlines() if line.strip()]
    tokens: set[str] = set()
    for index, line in enumerate(lines):
        match = _ID_LABEL_RE.search(line)
        if not match:
            continue
        candidates = _candidate_name_tokens(line[:match.start()])
        if not candidates:
            for previous in range(index - 1, max(-1, index - 4), -1):
                candidates = _candidate_name_tokens(lines[previous])
                if candidates:
                    break
        tokens.update(candidates)
    return tokens


def _redact_header_names(body: str, tokens: set[str]) -> tuple[str, int]:
    total = 0
    redacted = body
    for token in sorted(tokens, key=len, reverse=True):
        pattern = re.compile(rf"(?<![\u0590-\u05FF]){re.escape(token)}(?![\u0590-\u05FF])")
        redacted, count = pattern.subn(NAME_PLACEHOLDER, redacted)
        total += count
    return redacted, total


def _trim_identity_zones(text: str) -> str:
    start, marker = _body_start(text)
    body = text[start + len(marker):]
    end_positions = [body.find(marker) for marker in _END_MARKERS if body.find(marker) >= 0]
    if end_positions:
        body = body[: min(end_positions)]
    return body.strip()


def residual_pii_findings(text: str, header_name_tokens: set[str] | None = None) -> list[str]:
    findings: list[str] = []
    if _EMAIL_RE.search(text):
        findings.append("email")
    if _PHONE_RE.search(text):
        findings.append("phone")
    if _ID_RE.search(text):
        findings.append("id")
    if _IBAN_RE.search(text):
        findings.append("iban")
    for token in header_name_tokens or set():
        pattern = re.compile(rf"(?<![\u0590-\u05FF]){re.escape(token)}(?![\u0590-\u05FF])")
        if pattern.search(text):
            findings.append("header_name")
            break
    return sorted(set(findings))


def prepare_sanitized_contract_text(raw_text: str) -> tuple[str, dict[str, int]]:
    name_tokens = _header_person_tokens(raw_text)
    body = _trim_identity_zones(raw_text)
    body, header_name_replacements = _redact_header_names(body, name_tokens)
    redaction = redact_personal_data_with_report(body)
    sanitized = redaction.redacted_text.strip()
    residual = residual_pii_findings(sanitized, name_tokens)
    if residual:
        raise RuntimeError("Privacy gate blocked provider handoff: " + ", ".join(residual))

    validation = validate_contract_text(sanitized)
    if not validation.usable:
        raise RuntimeError("Sanitized contract text is not usable for analysis: " + "; ".join(validation.problems))

    report = redaction.report
    counts = {
        "emails": report.emails,
        "phones": report.phones,
        "ids": report.ids,
        "bank_details": report.bank_details,
        "addresses": report.addresses,
        "names": report.names + header_name_replacements,
        "signatures": report.signatures,
        "guarantor_details": report.guarantor_details,
        "total": report.total + header_name_replacements,
    }
    return sanitized, counts


def analyze_with_auto_route(
    sanitized_text: str,
    api_key: str,
    analyze_fn: Callable[..., ContractAuditResult] = analyze_contract_with_gemini,
) -> tuple[ContractAuditResult, str, list[dict[str, object]]]:
    attempts: list[dict[str, object]] = []
    for model in AUTO_MODEL_ROUTE:
        started = time.monotonic()
        try:
            result = analyze_fn(redacted_text=sanitized_text, api_key=api_key, model=model)
        except (GeminiAuthenticationError, GeminiConfigurationError):
            raise
        except (GeminiRateLimitError, GeminiResponseError) as exc:
            attempts.append({
                "model": model,
                "status": "FAILED",
                "error": type(exc).__name__,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            continue
        attempts.append({
            "model": model,
            "status": "OK",
            "elapsed_seconds": round(time.monotonic() - started, 3),
        })
        return result, model, attempts
    raise RuntimeError("All configured Gemini Flash models failed for this contract")


def write_report(
    pdf_path: Path,
    model_used: str,
    attempts: list[dict[str, object]],
    redaction_counts: dict[str, int],
    result: ContractAuditResult,
) -> Path:
    report = {
        "model_used": model_used,
        "attempts": attempts,
        "redaction_counts": redaction_counts,
        "analysis": result.model_dump(mode="json"),
    }
    path = pdf_path.with_name(f"single_contract_analysis_{time.strftime('%Y%m%d_%H%M%S')}.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    pdf_path = choose_pdf()
    if pdf_path is None:
        print("Договор не выбран.")
        return 1

    try:
        raw_text = extract_pdf_text(pdf_path)
        sanitized_text, redaction_counts = prepare_sanitized_contract_text(raw_text)
        result, model_used, attempts = analyze_with_auto_route(sanitized_text, load_key())
        report_path = write_report(pdf_path, model_used, attempts, redaction_counts, result)
    except Exception as exc:
        print(f"Анализ остановлен: {exc}")
        return 1

    print(f"Готово. Использована модель: {model_used}")
    print(f"Отчёт: {report_path}")
    if os.name == "nt":
        os.startfile(report_path)  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
