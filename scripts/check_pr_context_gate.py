#!/usr/bin/env python3
"""Validate the repository PR Context Gate against trusted base state.

The workflow executes this file from the pull request base revision. Candidate
files are treated only as untrusted data and are never imported or executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable

MAX_TEXT_BYTES = 1_000_000
MAX_EVENT_BYTES = 2_000_000
MAX_BODY_CHARS = 100_000

BINDING_PATHS = (
    "AGENTS.md",
    "docs/ARCHITECTURE.md",
    "docs/CUSTOM_OCR_PIPELINE.md",
    "docs/OCR_PROJECT_STATE.md",
    "docs/OCR_PROJECT_STATE.json",
)

REQUIRED_CHECKBOX_SNIPPETS = (
    "I read `AGENTS.md` from the PR base branch.",
    "I read `docs/ARCHITECTURE.md` from the PR base branch.",
    "I read `docs/CUSTOM_OCR_PIPELINE.md` from the PR base branch.",
    "I read `docs/OCR_PROJECT_STATE.md` from the PR base branch.",
    "I read `docs/OCR_PROJECT_STATE.json` from the PR base branch.",
    "The Markdown and JSON state documents agree.",
    "`docs/OCR_PROJECT_STATE.md` records this PR number",
    "`docs/OCR_PROJECT_STATE.json` has an incremented `state_version`.",
    "`last_recorded_pr` equals this PR number.",
    "`last_recorded_change` identifies this bounded change.",
    "`active_track` and `next_step_id` remain unchanged unless the product owner explicitly changed them.",
    "State-update commit is present.",
    "Ready for review.",
    "No auto-merge requested.",
)

STATE_VERSION_RE = re.compile(r"^privacy-ocr-(\d{4}-\d{2}-\d{2})-(\d{2,})$")
CHANGE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ValidationInputError(ValueError):
    """Raised when the checker itself cannot safely read required input."""


def _safe_file(root: Path, relative_path: str, *, max_bytes: int = MAX_TEXT_BYTES) -> Path:
    root = root.resolve(strict=True)
    path = root / relative_path
    try:
        st = path.lstat()
    except FileNotFoundError as exc:
        raise ValidationInputError(f"missing required file: {relative_path}") from exc
    if path.is_symlink():
        raise ValidationInputError(f"symlink is not allowed for required file: {relative_path}")
    if not path.is_file():
        raise ValidationInputError(f"required path is not a regular file: {relative_path}")
    if st.st_size > max_bytes:
        raise ValidationInputError(
            f"required file exceeds {max_bytes} bytes: {relative_path}"
        )
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValidationInputError(f"required file escapes checkout root: {relative_path}") from exc
    return resolved


def _read_text(root: Path, relative_path: str) -> str:
    path = _safe_file(root, relative_path)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationInputError(f"required file is not valid UTF-8: {relative_path}") from exc


def _read_json(root: Path, relative_path: str) -> dict[str, Any]:
    text = _read_text(root, relative_path)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationInputError(f"invalid JSON in {relative_path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationInputError(f"top-level JSON must be an object: {relative_path}")
    return value


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _blob_sha(root: Path, relative_path: str) -> str:
    return git_blob_sha(_safe_file(root, relative_path).read_bytes())


def _collapse_space(value: str) -> str:
    return " ".join(value.split())


def _extract_fenced_block(body: str, first_line: str) -> str | None:
    pattern = re.compile(
        rf"```text\s*\n{re.escape(first_line)}\s*\n(?P<body>.*?)\n```",
        re.DOTALL,
    )
    match = pattern.search(body)
    return match.group("body") if match else None


def _parse_context_block(block: str) -> tuple[dict[str, str], dict[str, str]]:
    fields: dict[str, str] = {}
    shas: dict[str, str] = {}
    in_shas = False
    for raw_line in block.splitlines():
        if not raw_line.strip():
            continue
        if raw_line.strip() == "binding_document_shas:":
            in_shas = True
            continue
        if ":" not in raw_line:
            continue
        key, value = raw_line.strip().split(":", 1)
        if in_shas:
            shas[key.strip()] = value.strip()
        else:
            fields[key.strip()] = value.strip()
    return fields, shas


def _parse_state_update_block(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in block.splitlines():
        if not raw_line.strip() or ":" not in raw_line:
            continue
        key, value = raw_line.strip().split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _is_checked(body: str, snippet: str) -> bool:
    for line in body.splitlines():
        if re.match(r"^\s*-\s*\[[xX]\]\s*", line) and snippet in line:
            return True
    return False


def _parse_state_version(value: Any, field_name: str, errors: list[str]) -> tuple[date, int] | None:
    if not isinstance(value, str):
        errors.append(f"{field_name} must be a string")
        return None
    match = STATE_VERSION_RE.fullmatch(value)
    if not match:
        errors.append(
            f"{field_name} must match privacy-ocr-YYYY-MM-DD-NN, got {value!r}"
        )
        return None
    try:
        version_date = date.fromisoformat(match.group(1))
    except ValueError:
        errors.append(f"{field_name} contains an invalid date: {value!r}")
        return None
    return version_date, int(match.group(2))


def _state_record(markdown: str, pr_number: int) -> str | None:
    pattern = re.compile(
        rf"^### PR #{pr_number}\b.*?\n(?P<body>.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(markdown)
    return match.group("body") if match else None


def _required_string(mapping: dict[str, Any], key: str, errors: list[str], prefix: str) -> str | None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}.{key} must be a non-empty string")
        return None
    return value.strip()


def validate_gate(event: dict[str, Any], base_root: Path, head_root: Path) -> list[str]:
    errors: list[str] = []

    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return ["event.pull_request must be an object"]

    if pull_request.get("draft") is True:
        return []

    pr_number = pull_request.get("number") or event.get("number")
    if not isinstance(pr_number, int) or isinstance(pr_number, bool) or pr_number <= 0:
        return ["pull request number must be a positive integer"]

    body = pull_request.get("body")
    if not isinstance(body, str) or not body.strip():
        return ["pull request body is required"]
    if len(body) > MAX_BODY_CHARS:
        return [f"pull request body exceeds {MAX_BODY_CHARS} characters"]

    for snippet in REQUIRED_CHECKBOX_SNIPPETS:
        if not _is_checked(body, snippet):
            errors.append(f"required checkbox is not checked: {snippet}")

    context_raw = _extract_fenced_block(body, "PR CONTEXT GATE")
    if context_raw is None:
        errors.append("missing fenced PR CONTEXT GATE block")
        context_fields: dict[str, str] = {}
        binding_shas: dict[str, str] = {}
    else:
        context_fields, binding_shas = _parse_context_block(context_raw)

    state_update_raw = _extract_fenced_block(body, "state_update:")
    if state_update_raw is None:
        errors.append("missing fenced state_update block")
        state_update: dict[str, str] = {}
    else:
        state_update = _parse_state_update_block(state_update_raw)

    try:
        base_state = _read_json(base_root, "docs/OCR_PROJECT_STATE.json")
        head_state = _read_json(head_root, "docs/OCR_PROJECT_STATE.json")
        base_markdown = _read_text(base_root, "docs/OCR_PROJECT_STATE.md")
        head_markdown = _read_text(head_root, "docs/OCR_PROJECT_STATE.md")
    except ValidationInputError as exc:
        return errors + [str(exc)]

    for relative_path in ("docs/OCR_PROJECT_STATE.md", "docs/OCR_PROJECT_STATE.json"):
        try:
            base_bytes = _safe_file(base_root, relative_path).read_bytes()
            head_bytes = _safe_file(head_root, relative_path).read_bytes()
        except ValidationInputError as exc:
            errors.append(str(exc))
            continue
        if base_bytes == head_bytes:
            errors.append(f"every PR must change {relative_path}")

    for key in ("active_track", "state_version", "next_step_id"):
        expected = base_state.get(key)
        actual = context_fields.get(key)
        if not isinstance(expected, str):
            errors.append(f"base state field {key} must be a string")
        elif actual != expected:
            errors.append(
                f"context {key} must match base state: expected {expected!r}, got {actual!r}"
            )

    expected_summary = base_state.get("next_step_summary")
    permitted = context_fields.get("permitted_next_step")
    if not isinstance(expected_summary, str):
        errors.append("base state next_step_summary must be a string")
    elif _collapse_space(permitted or "") != _collapse_space(expected_summary):
        errors.append("context permitted_next_step must exactly match base next_step_summary")

    for key in ("task_scope", "explicitly_out_of_scope", "exception_authorization", "state_change"):
        value = context_fields.get(key)
        if not value:
            errors.append(f"context field is required: {key}")

    for relative_path in BINDING_PATHS:
        try:
            expected_sha = _blob_sha(base_root, relative_path)
        except ValidationInputError as exc:
            errors.append(str(exc))
            continue
        actual_sha = binding_shas.get(relative_path)
        if actual_sha != expected_sha:
            errors.append(
                f"binding SHA mismatch for {relative_path}: expected {expected_sha}, got {actual_sha!r}"
            )

    if head_state.get("schema_version") != base_state.get("schema_version"):
        errors.append("schema_version may not change in Context Gate CI v0")
    if head_state.get("state_update_required_per_pr") is not True:
        errors.append("head state must keep state_update_required_per_pr=true")
    if head_state.get("canonical_state_document") != "docs/OCR_PROJECT_STATE.md":
        errors.append("head canonical_state_document must remain docs/OCR_PROJECT_STATE.md")

    base_version = _parse_state_version(base_state.get("state_version"), "base.state_version", errors)
    head_version = _parse_state_version(head_state.get("state_version"), "head.state_version", errors)
    if base_version and head_version and head_version <= base_version:
        errors.append("head state_version must be strictly newer than base state_version")

    head_version_text = head_state.get("state_version")
    updated_on = head_state.get("updated_on")
    if head_version and updated_on != head_version[0].isoformat():
        errors.append("head updated_on must equal the date encoded in head state_version")

    if head_state.get("last_recorded_pr") != pr_number:
        errors.append(
            f"head last_recorded_pr must equal PR number {pr_number}"
        )

    change_id = _required_string(head_state, "last_recorded_change", errors, "head")
    if change_id and not CHANGE_ID_RE.fullmatch(change_id):
        errors.append("head.last_recorded_change must be a lowercase kebab-case identifier")

    recorded_pr_text = state_update.get("recorded_pr")
    if recorded_pr_text != str(pr_number):
        errors.append(
            f"state_update.recorded_pr must equal {pr_number}, got {recorded_pr_text!r}"
        )
    if state_update.get("new_state_version") != head_version_text:
        errors.append("state_update.new_state_version must match head state_version")
    if change_id and state_update.get("recorded_change") != change_id:
        errors.append("state_update.recorded_change must match head last_recorded_change")

    next_step_effect = state_update.get("next_step_effect")
    if next_step_effect not in {"unchanged", "changed with explicit authorization"}:
        errors.append(
            "state_update.next_step_effect must be 'unchanged' or 'changed with explicit authorization'"
        )

    state_keys = ("active_track", "next_step_id", "next_step_summary")
    state_changed = any(head_state.get(key) != base_state.get(key) for key in state_keys)
    authorization = (context_fields.get("exception_authorization") or "").strip().lower()
    if state_changed:
        if next_step_effect != "changed with explicit authorization":
            errors.append("changed active track/next step requires explicit next_step_effect")
        if authorization in {"", "none"}:
            errors.append("changed active track/next step requires exception_authorization")
    elif next_step_effect != "unchanged":
        errors.append("unchanged active track/next step must declare next_step_effect: unchanged")

    if updated_on and f"Последнее обновление: {updated_on}, PR #{pr_number}" not in head_markdown:
        errors.append("state Markdown header must record updated_on and current PR number")

    record = _state_record(head_markdown, pr_number)
    if record is None:
        errors.append(f"state Markdown must contain a ### PR #{pr_number} record")
    else:
        required_record_tokens: Iterable[str] = (
            "Идентификатор:",
            "Изменение:",
            "Проверено:",
            "Осталось:",
            "Влияние:",
            "Следующий шаг:",
        )
        for token in required_record_tokens:
            if token not in record:
                errors.append(f"state PR record is missing structured field: {token}")
        if change_id and change_id not in record:
            errors.append("state PR record must include head last_recorded_change")
        head_next_step = head_state.get("next_step_id")
        if isinstance(head_next_step, str) and head_next_step not in record:
            errors.append("state PR record must include head next_step_id")

    if base_markdown == head_markdown:
        errors.append("state Markdown must change for every PR")

    return errors


def _load_event(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValidationInputError("event path must be a regular file")
    if path.stat().st_size > MAX_EVENT_BYTES:
        raise ValidationInputError(f"event file exceeds {MAX_EVENT_BYTES} bytes")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationInputError(f"invalid event JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationInputError("event JSON must be an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True, type=Path)
    parser.add_argument("--base-root", required=True, type=Path)
    parser.add_argument("--head-root", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        event = _load_event(args.event)
        errors = validate_gate(event, args.base_root, args.head_root)
    except (ValidationInputError, OSError) as exc:
        print(f"Context Gate input error: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("PR Context Gate failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("PR Context Gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
