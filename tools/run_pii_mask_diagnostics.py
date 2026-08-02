from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

REMOTE_REF = "origin/main"
DIAGNOSTIC_MODULE = "research.hebrew_contract_ocr.pii_mask_diagnostics"


class PIIMaskRunnerError(RuntimeError):
    pass


def _run(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise PIIMaskRunnerError("required local command could not be started") from exc


def _require_success(
    result: subprocess.CompletedProcess[str],
    label: str,
) -> subprocess.CompletedProcess[str]:
    if result.returncode != 0:
        raise PIIMaskRunnerError(f"{label} failed")
    return result


def resolve_repo_root(start: Path) -> Path:
    result = _require_success(
        _run(["git", "rev-parse", "--show-toplevel"], start),
        "repository lookup",
    )
    value = result.stdout.strip()
    if not value:
        raise PIIMaskRunnerError("repository lookup returned no path")
    root = Path(value).resolve()
    if not root.is_dir():
        raise PIIMaskRunnerError("repository root does not exist")
    return root


def default_output_path(review_pack_dir: Path) -> Path:
    return review_pack_dir.parent / f"{review_pack_dir.name}-mask-diagnostics.json"


def run_diagnostics(
    review_pack_dir: Path,
    *,
    output_path: Path | None = None,
    repo_root: Path | None = None,
    python_executable: str | None = None,
) -> tuple[Path, str]:
    try:
        pack = review_pack_dir.expanduser().resolve(strict=True)
    except OSError as exc:
        raise PIIMaskRunnerError("review pack directory does not exist") from exc
    if not pack.is_dir():
        raise PIIMaskRunnerError("review pack input must be a directory")

    output = (
        output_path.expanduser().absolute()
        if output_path is not None
        else default_output_path(pack)
    )
    if output.exists() or output.is_symlink():
        raise PIIMaskRunnerError("diagnostic report already exists")

    root = repo_root.expanduser().resolve() if repo_root else resolve_repo_root(Path.cwd())
    if not root.is_dir():
        raise PIIMaskRunnerError("repository root does not exist")

    python = python_executable or sys.executable
    _require_success(
        _run(["git", "fetch", "--quiet", "origin", "main"], root),
        "main refresh",
    )

    temporary_root = Path(tempfile.mkdtemp(prefix="pii-mask-diagnostics-main-"))
    checkout = temporary_root / "checkout"
    worktree_added = False
    try:
        _require_success(
            _run(
                [
                    "git",
                    "worktree",
                    "add",
                    "--detach",
                    "--quiet",
                    str(checkout),
                    REMOTE_REF,
                ],
                root,
            ),
            "temporary main checkout",
        )
        worktree_added = True

        result = _run(
            [
                python,
                "-m",
                DIAGNOSTIC_MODULE,
                "--review-pack-dir",
                str(pack),
                "--output",
                str(output),
            ],
            checkout,
        )
        if result.returncode != 0:
            output.unlink(missing_ok=True)
            raise PIIMaskRunnerError("mask diagnostics failed")
        if not output.is_file():
            raise PIIMaskRunnerError("mask diagnostics produced no report")
        marker = result.stdout.strip()
        if not marker.startswith("DIAGNOSTICS READY:"):
            output.unlink(missing_ok=True)
            raise PIIMaskRunnerError("mask diagnostics returned no ready marker")
        return output, marker
    finally:
        if worktree_added:
            _run(["git", "worktree", "remove", "--force", str(checkout)], root)
        shutil.rmtree(temporary_root, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the merged geometry-only PII mask diagnostics from a temporary "
            "origin/main checkout without switching the current branch."
        )
    )
    parser.add_argument("review_pack_dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repo-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output, marker = run_diagnostics(
            args.review_pack_dir,
            output_path=args.output,
            repo_root=args.repo_root,
        )
    except PIIMaskRunnerError as exc:
        print(f"DIAGNOSTICS RUN BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(marker)
    print(f"REPORT READY: {output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
