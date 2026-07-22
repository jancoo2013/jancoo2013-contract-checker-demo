#!/usr/bin/env python3
"""Trusted, dependency-free validation for the repository PR Context Gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

PATHS = (
    "AGENTS.md",
    "docs/ARCHITECTURE.md",
    "docs/CUSTOM_OCR_PIPELINE.md",
    "docs/OCR_PROJECT_STATE.md",
    "docs/OCR_PROJECT_STATE.json",
)
CHECKS = (
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
VERSION = re.compile(r"^privacy-ocr-(\d{4}-\d{2}-\d{2})-(\d{2,})$")
CHANGE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def read(root: Path, rel: str) -> bytes:
    path = root.resolve(strict=True) / rel
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError(f"unsafe or missing required file: {rel}")
    if path.resolve(strict=True).parent != (root.resolve() / rel).parent.resolve():
        raise ValueError(f"required file escapes checkout: {rel}")
    return path.read_bytes()


def text(root: Path, rel: str) -> str:
    return read(root, rel).decode("utf-8")


def state(root: Path) -> dict[str, Any]:
    value = json.loads(text(root, "docs/OCR_PROJECT_STATE.json"))
    if not isinstance(value, dict):
        raise ValueError("state JSON must be an object")
    return value


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def fenced(body: str, title: str) -> str:
    match = re.search(rf"```text\s*\n{re.escape(title)}\s*\n(.*?)\n```", body, re.S)
    return match.group(1) if match else ""


def pairs(block: str) -> tuple[dict[str, str], dict[str, str]]:
    values: dict[str, str] = {}
    shas: dict[str, str] = {}
    target = values
    for line in block.splitlines():
        if line.strip() == "binding_document_shas:":
            target = shas
        elif ":" in line:
            key, value = line.strip().split(":", 1)
            target[key.strip()] = value.strip()
    return values, shas


def checked(body: str, snippet: str) -> bool:
    return any(re.match(r"^\s*-\s*\[[xX]\]", line) and snippet in line for line in body.splitlines())


def parsed_version(value: Any, name: str, errors: list[str]) -> tuple[date, int] | None:
    match = VERSION.fullmatch(value) if isinstance(value, str) else None
    if not match:
        errors.append(f"{name} must match privacy-ocr-YYYY-MM-DD-NN")
        return None
    try:
        return date.fromisoformat(match.group(1)), int(match.group(2))
    except ValueError:
        errors.append(f"{name} contains an invalid date")
        return None


def validate(event: dict[str, Any], base: Path, head: Path) -> list[str]:
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        return ["event.pull_request must be an object"]
    if pr.get("draft") is True:
        return []
    number = pr.get("number") or event.get("number")
    body = pr.get("body")
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        return ["invalid PR number"]
    if not isinstance(body, str) or not body.strip() or len(body) > 100_000:
        return ["non-empty bounded PR body is required"]

    errors = [f"unchecked required box: {item}" for item in CHECKS if not checked(body, item)]
    context, shas = pairs(fenced(body, "PR CONTEXT GATE"))
    update, _ = pairs(fenced(body, "state_update:"))
    if not context:
        errors.append("missing PR CONTEXT GATE block")
    if not update:
        errors.append("missing state_update block")

    try:
        base_state, head_state = state(base), state(head)
        base_md = text(base, "docs/OCR_PROJECT_STATE.md")
        head_md = text(head, "docs/OCR_PROJECT_STATE.md")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        return errors + [str(exc)]

    for rel in ("docs/OCR_PROJECT_STATE.md", "docs/OCR_PROJECT_STATE.json"):
        if read(base, rel) == read(head, rel):
            errors.append(f"every PR must change {rel}")

    for key in ("active_track", "state_version", "next_step_id"):
        if context.get(key) != base_state.get(key):
            errors.append(f"context {key} must match base state")
    if " ".join(context.get("permitted_next_step", "").split()) != " ".join(
        str(base_state.get("next_step_summary", "")).split()
    ):
        errors.append("permitted_next_step must match base next_step_summary")
    for key in ("task_scope", "explicitly_out_of_scope", "exception_authorization", "state_change"):
        if not context.get(key):
            errors.append(f"missing context field: {key}")
    for rel in PATHS:
        if shas.get(rel) != blob_sha(read(base, rel)):
            errors.append(f"binding SHA mismatch: {rel}")

    if head_state.get("schema_version") != base_state.get("schema_version"):
        errors.append("schema_version changed")
    if head_state.get("state_update_required_per_pr") is not True:
        errors.append("state_update_required_per_pr must remain true")
    if head_state.get("canonical_state_document") != "docs/OCR_PROJECT_STATE.md":
        errors.append("canonical_state_document changed")

    base_ver = parsed_version(base_state.get("state_version"), "base state_version", errors)
    head_ver = parsed_version(head_state.get("state_version"), "head state_version", errors)
    if base_ver and head_ver and head_ver <= base_ver:
        errors.append("state_version must increase")
    if head_ver and head_state.get("updated_on") != head_ver[0].isoformat():
        errors.append("updated_on must match state_version date")
    if head_state.get("last_recorded_pr") != number:
        errors.append(f"last_recorded_pr must equal {number}")
    change = head_state.get("last_recorded_change")
    if not isinstance(change, str) or not CHANGE.fullmatch(change):
        errors.append("last_recorded_change must be lowercase kebab-case")
        change = ""

    if update.get("recorded_pr") != str(number):
        errors.append(f"state_update.recorded_pr must equal {number}")
    if update.get("new_state_version") != head_state.get("state_version"):
        errors.append("state_update.new_state_version mismatch")
    if update.get("recorded_change") != change:
        errors.append("state_update.recorded_change mismatch")

    effect = update.get("next_step_effect")
    changed = any(
        head_state.get(key) != base_state.get(key)
        for key in ("active_track", "next_step_id", "next_step_summary")
    )
    authorized = context.get("exception_authorization", "").strip().lower() not in {"", "none"}
    if changed and (effect != "changed with explicit authorization" or not authorized):
        errors.append("active track/next step changed without explicit authorization")
    if not changed and effect != "unchanged":
        errors.append("unchanged next step must declare next_step_effect: unchanged")

    updated = head_state.get("updated_on")
    if f"Последнее обновление: {updated}, PR #{number}" not in head_md:
        errors.append("state header does not record current PR")
    record_match = re.search(rf"^### PR #{number}\b.*?\n(.*?)(?=^##\s|\Z)", head_md, re.M | re.S)
    if not record_match:
        errors.append(f"missing structured PR #{number} state record")
    else:
        record = record_match.group(1)
        for token in ("Идентификатор:", "Изменение:", "Проверено:", "Осталось:", "Влияние:", "Следующий шаг:"):
            if token not in record:
                errors.append(f"state record missing {token}")
        if change not in record or str(head_state.get("next_step_id", "")) not in record:
            errors.append("state record lacks change or next-step identifier")
    if base_md == head_md:
        errors.append("state Markdown did not change")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True, type=Path)
    parser.add_argument("--base-root", required=True, type=Path)
    parser.add_argument("--head-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        event = json.loads(args.event.read_text(encoding="utf-8"))
        errors = validate(event, args.base_root, args.head_root)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Context Gate input error: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("PR Context Gate failed:\n- " + "\n- ".join(errors), file=sys.stderr)
        return 1
    print("PR Context Gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
