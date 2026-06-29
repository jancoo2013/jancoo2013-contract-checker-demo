"""Build a safe project snapshot for external Gemini audit.

This script does not call Gemini or any external API. It only reads selected
repository files and writes a Markdown bundle that can be uploaded or pasted
manually into Gemini for product/logic/privacy/legal-language audit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "audit_bundle"
OUTPUT_FILE = OUTPUT_DIR / "GEMINI_PROJECT_AUDIT_BUNDLE.md"

MAX_FILE_CHARS = 60_000

EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "audit_bundle",
    "venv",
    ".venv",
    "env",
    ".env",
    "node_modules",
    "dist",
    "build",
}

SENSITIVE_FILENAME_TOKENS = {
    ".env",
    "secret",
    "secrets",
    "credential",
    "credentials",
    "token",
    "tokens",
    "apikey",
    "api_key",
    "private_key",
    "service_account",
}

INCLUDE_EXACT = [
    "docs/ARCHITECTURE.md",
    "docs/GEMINI_PROJECT_AUDIT.md",
    "AGENTS.md",
    "README.md",
    "requirements.txt",
    "app.py",
]

INCLUDE_GLOBS = [
    "contract_checker/*.py",
    "tests/*.py",
]

RISKY_TEXT_PATTERNS = [
    "можно подписывать",
    "нельзя подписывать",
    "безопасно подписывать",
    "договор безопасен",
    "вердикт",
    "юридический вывод",
    "юридическая консультация",
    "AI lawyer",
    "legal verdict",
    "safe to sign",
    "illegal",
    "void",
    "enforceable",
    "unenforceable",
    "требуйте удалить",
    "вы выиграете",
    "нарушает закон",
    "Google Vision",
    "Tesseract",
    "Gemini image",
    "external OCR",
    "Airtable API",
    "source_quote_he",
    "verdict",
]


@dataclass(frozen=True)
class RiskMatch:
    path: str
    line_number: int
    pattern: str
    line: str


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_sensitive_path(path: Path) -> bool:
    rel = relative(path).lower()
    parts = set(rel.split("/"))
    name = path.name.lower()
    if any(part in EXCLUDED_DIRS for part in parts):
        return True
    return any(token in name or token in rel for token in SENSITIVE_FILENAME_TOKENS)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def collect_file_list() -> list[Path]:
    paths: list[Path] = []

    for rel in INCLUDE_EXACT:
        path = ROOT / rel
        if path.exists() and path.is_file() and not is_sensitive_path(path):
            paths.append(path)

    for pattern in INCLUDE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if path.exists() and path.is_file() and not is_sensitive_path(path):
                paths.append(path)

    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def collect_project_tree() -> list[str]:
    lines: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        rel = relative(path)
        if any(part in EXCLUDED_DIRS for part in rel.split("/")):
            continue
        if is_sensitive_path(path):
            continue
        if path.is_file():
            lines.append(rel)
    return lines


def scan_risky_text(paths: list[Path]) -> list[RiskMatch]:
    matches: list[RiskMatch] = []
    compiled = [(pattern, re.compile(re.escape(pattern), re.IGNORECASE)) for pattern in RISKY_TEXT_PATTERNS]
    for path in paths:
        text = read_text(path)
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern, regex in compiled:
                if regex.search(line):
                    matches.append(
                        RiskMatch(
                            path=relative(path),
                            line_number=line_number,
                            pattern=pattern,
                            line=line.strip(),
                        )
                    )
    return matches


def fence_for(path: Path, text: str) -> str:
    suffix = path.suffix.lower()
    if suffix == ".py":
        language = "python"
    elif suffix == ".md":
        language = "markdown"
    elif suffix in {".txt", ".cfg", ".ini"}:
        language = "text"
    else:
        language = "text"

    rel = relative(path)
    if len(text) > MAX_FILE_CHARS:
        text = text[:MAX_FILE_CHARS] + "\n\n[TRUNCATED BY build_audit_bundle.py]\n"
    return f"### {rel}\n\n```{language}\n{text}\n```\n"


def build_bundle() -> str:
    selected_paths = collect_file_list()
    tree_lines = collect_project_tree()
    risky_matches = scan_risky_text(selected_paths)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    sections: list[str] = []
    sections.append("# Gemini Project Audit Bundle\n")
    sections.append(f"Generated at: `{generated_at}`\n")
    sections.append(
        "This bundle is a manually generated project snapshot for external Gemini audit. "
        "It does not include raw user contracts, uploaded images, API keys, `.env` files, or known secret-like files.\n"
    )

    sections.append("## Auditor Instructions\n")
    sections.append(
        "Use `docs/GEMINI_PROJECT_AUDIT.md` as the audit instruction. "
        "Use `docs/ARCHITECTURE.md` and `AGENTS.md` as binding project context. "
        "Audit product logic, legal-language risk, privacy/PII handling, UX wording, schemas, prompts, validation, and tests. "
        "Do not write large code patches unless explicitly asked.\n"
    )

    sections.append("## Selected Files Included\n")
    sections.append("```text\n" + "\n".join(relative(path) for path in selected_paths) + "\n```\n")

    sections.append("## Project Tree Snapshot\n")
    sections.append("```text\n" + "\n".join(tree_lines) + "\n```\n")

    sections.append("## Risky Text Scan\n")
    if risky_matches:
        sections.append(
            "These are simple literal matches for terms that may require human review. "
            "A match is not automatically a bug; Gemini should classify it in context.\n"
        )
        sections.append("| File | Line | Pattern | Text |\n|---|---:|---|---|\n")
        for item in risky_matches:
            safe_line = item.line.replace("|", "\\|")
            safe_pattern = item.pattern.replace("|", "\\|")
            sections.append(f"| `{item.path}` | {item.line_number} | `{safe_pattern}` | {safe_line} |\n")
        sections.append("\n")
    else:
        sections.append("No risky-text literal matches found in selected files.\n")

    sections.append("## File Contents\n")
    for path in selected_paths:
        sections.append(fence_for(path, read_text(path)))

    sections.append("## Required Gemini Response\n")
    sections.append(
        "Return findings grouped as `BLOCKER`, `MAJOR`, `MINOR`, `QUESTION`, and `OK`. "
        "End with overall status, top 3 risks, and recommended next Codex tasks.\n"
    )
    return "\n".join(sections)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(build_bundle(), encoding="utf-8")
    print(f"Wrote {relative(OUTPUT_FILE)}")


if __name__ == "__main__":
    main()
