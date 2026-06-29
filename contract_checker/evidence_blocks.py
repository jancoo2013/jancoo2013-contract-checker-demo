"""Deterministic evidence-block construction for redacted contract text."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .validator import PAGE_SEPARATOR_RE


@dataclass(frozen=True)
class EvidenceBlock:
    block_id: str
    page: int | None
    index: int
    text: str


_NUMBERED_LINE_RE = re.compile(r"^\s*(?:\d+|[\u0590-\u05FF])[.)-]\s+")


def _page_sections(redacted_text: str) -> list[tuple[int, str]]:
    matches = list(PAGE_SEPARATOR_RE.finditer(redacted_text))
    if not matches:
        return [(1, redacted_text)]

    sections: list[tuple[int, str]] = []
    first_prefix = redacted_text[: matches[0].start()]
    if first_prefix.strip():
        sections.append((1, first_prefix))

    for index, match in enumerate(matches):
        page = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(redacted_text)
        section_text = redacted_text[start:end]
        if section_text.strip():
            sections.append((page, section_text))
    return sections


def _paragraph_candidates(section_text: str) -> list[str]:
    normalized = section_text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n\s*\n+", normalized)
    candidates: list[str] = []
    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if not stripped:
            continue
        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        numbered_lines = [line for line in lines if _NUMBERED_LINE_RE.match(line)]
        if len(numbered_lines) >= 2:
            candidates.extend(lines)
        else:
            candidates.append(stripped)
    return candidates


def build_evidence_blocks(redacted_text: str) -> list[EvidenceBlock]:
    """Split already-redacted text into stable numbered evidence blocks."""

    blocks: list[EvidenceBlock] = []
    page_indexes: dict[int, int] = {}
    for page, section_text in _page_sections(redacted_text):
        for candidate in _paragraph_candidates(section_text):
            if not candidate.strip():
                continue
            page_indexes[page] = page_indexes.get(page, 0) + 1
            index = page_indexes[page]
            blocks.append(
                EvidenceBlock(
                    block_id=f"P{page}-B{index:02d}",
                    page=page,
                    index=index,
                    text=candidate,
                )
            )
    return blocks


def format_evidence_blocks_for_prompt(blocks: list[EvidenceBlock]) -> str:
    """Format evidence blocks for the LLM prompt without adding source text elsewhere."""

    return "\n\n".join(f"[{block.block_id}]\n{block.text}" for block in blocks)


def evidence_block_map(blocks: list[EvidenceBlock]) -> dict[str, EvidenceBlock]:
    return {block.block_id: block for block in blocks}
