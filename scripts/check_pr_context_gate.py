#!/usr/bin/env python3
"""Trusted, dependency-free validation for repository PR scope and state continuity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

STATE_MD = "docs/OCR_PROJECT_STATE.md"
STATE_JSON = "docs/OCR_PROJECT_STATE.json"
REQUIRED_STATE_PATHS = {STATE_MD, STATE_JSON}
CONTRACT_VERSION = 1
MAX_BODY_BYTES = 100_000
MAX_ALLOWED_PATHS = 100
MAX_TRACKED_FILES = 50_000
MAX_TRACKED_BYTES = 2 * 1024 * 1024 * 1024
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
    value = json.loads(text(root, STATE_JSON))
    if not isinstance(value, dict):
        raise ValueError("state JSON must be an object")
    return value


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


def canonical_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 300 or "\\" in value:
        return None
    if any(ord(char) < 32 for char in value):
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", "..", ".git"} for part in path.parts):
        return None
    normalized = path.as_posix()
    return normalized if normalized == value else None


def parse_contract(body: str, errors: list[str]) -> tuple[str, set[str]]:
    candidates: list[dict[str, Any]] = []
    for raw in re.findall(r"```json\s*\n(.*?)\n```", body, re.S | re.I):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "context_gate_version" in value:
            candidates.append(value)
    if len(candidates) != 1:
        errors.append("PR body must contain exactly one context gate JSON block")
        return "", set()

    value = candidates[0]
    expected_keys = {"context_gate_version", "change", "allowed_paths"}
    if set(value) != expected_keys:
        errors.append("context gate JSON must contain only context_gate_version, change, and allowed_paths")
    if value.get("context_gate_version") != CONTRACT_VERSION:
        errors.append(f"context_gate_version must equal {CONTRACT_VERSION}")

    change = value.get("change")
    if not isinstance(change, str) or not CHANGE.fullmatch(change):
        errors.append("change must be lowercase kebab-case")
        change = ""

    raw_paths = value.get("allowed_paths")
    if not isinstance(raw_paths, list) or not raw_paths or len(raw_paths) > MAX_ALLOWED_PATHS:
        errors.append(f"allowed_paths must be a non-empty list with at most {MAX_ALLOWED_PATHS} items")
        return change, set()

    paths: list[str] = []
    for item in raw_paths:
        normalized = canonical_path(item)
        if normalized is None:
            errors.append(f"invalid allowed path: {item!r}")
        else:
            paths.append(normalized)
    if len(paths) != len(set(paths)):
        errors.append("allowed_paths must not contain duplicates")
    allowed = set(paths)
    missing_state = REQUIRED_STATE_PATHS - allowed
    if missing_state:
        errors.append("allowed_paths must include both state files: " + ", ".join(sorted(missing_state)))
    return change, allowed


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root: Path) -> dict[str, tuple[Any, ...]]:
    resolved = root.resolve(strict=True)
    result: dict[str, tuple[Any, ...]] = {}
    total_bytes = 0
    for current, dirs, files in os.walk(resolved, topdown=True, followlinks=False):
        traversable_dirs: list[str] = []
        for name in sorted(dirs):
            if name == ".git":
                continue
            path = Path(current) / name
            rel = path.relative_to(resolved).as_posix()
            info = path.lstat()
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                result[rel] = ("symlink", mode, os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                traversable_dirs.append(name)
            else:
                raise ValueError(f"unsupported checkout entry: {rel}")
            if len(result) > MAX_TRACKED_FILES:
                raise ValueError("checkout exceeds tracked-file safety limit")
        dirs[:] = traversable_dirs
        for name in sorted(files):
            path = Path(current) / name
            rel = path.relative_to(resolved).as_posix()
            if rel == ".git" or rel.startswith(".git/"):
                continue
            info = path.lstat()
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                result[rel] = ("symlink", mode, os.readlink(path))
            elif stat.S_ISREG(info.st_mode):
                total_bytes += info.st_size
                if total_bytes > MAX_TRACKED_BYTES:
                    raise ValueError("checkout exceeds tracked-byte safety limit")
                result[rel] = ("file", mode, info.st_size, file_digest(path))
            else:
                raise ValueError(f"unsupported checkout entry: {rel}")
            if len(result) > MAX_TRACKED_FILES:
                raise ValueError("checkout exceeds tracked-file safety limit")
    return result


def changed_paths(base: Path, head: Path) -> set[str]:
    before, after = snapshot(base), snapshot(head)
    return {path for path in before.keys() | after.keys() if before.get(path) != after.get(path)}


def validate_state(number: int, change: str, base: Path, head: Path, errors: list[str]) -> None:
    try:
        base_state, head_state = state(base), state(head)
        base_md, head_md = text(base, STATE_MD), text(head, STATE_MD)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
        return

    if head_state.get("schema_version") != base_state.get("schema_version"):
        errors.append("schema_version changed")
    if head_state.get("state_update_required_per_pr") is not True:
        errors.append("state_update_required_per_pr must remain true")
    if head_state.get("canonical_state_document") != STATE_MD:
        errors.append("canonical_state_document changed")

    base_ver = parsed_version(base_state.get("state_version"), "base state_version", errors)
    head_ver = parsed_version(head_state.get("state_version"), "head state_version", errors)
    if base_ver and head_ver and head_ver <= base_ver:
        errors.append("state_version must increase")
    if head_ver and head_state.get("updated_on") != head_ver[0].isoformat():
        errors.append("updated_on must match state_version date")
    if head_state.get("last_recorded_pr") != number:
        errors.append(f"last_recorded_pr must equal {number}")
    if head_state.get("last_recorded_change") != change:
        errors.append("last_recorded_change must match context gate change")

    for key in ("active_track", "next_step_id", "next_step_summary"):
        if not isinstance(head_state.get(key), str) or not head_state.get(key).strip():
            errors.append(f"state field {key} must be a non-empty string")

    if base_md == head_md:
        errors.append("state Markdown did not change")
    top = head_md.split("\n## 1.", 1)[0]
    required_fragments = (
        f"PR #{number}",
        str(head_state.get("updated_on", "")),
        change,
        str(head_state.get("next_step_id", "")),
    )
    for fragment in required_fragments:
        if fragment and fragment not in top:
            errors.append(f"state summary is missing: {fragment}")


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
    if not isinstance(body, str) or not body.strip() or len(body.encode("utf-8")) > MAX_BODY_BYTES:
        return ["non-empty bounded PR body is required"]

    errors: list[str] = []
    change, allowed = parse_contract(body, errors)
    try:
        actual = changed_paths(base, head)
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        return errors

    undeclared = actual - allowed
    not_changed = allowed - actual
    if undeclared:
        errors.append("undeclared changed paths: " + ", ".join(sorted(undeclared)))
    if not_changed:
        errors.append("allowed_paths entries did not change: " + ", ".join(sorted(not_changed)))

    validate_state(number, change, base, head, errors)
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
