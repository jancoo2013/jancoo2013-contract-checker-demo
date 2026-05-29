"""Data models for the public-safe contract checker demo."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CheckFinding:
    """A single review finding produced by the demo rules engine."""

    title: str
    status: str
    detail: str
    recommendation: str


@dataclass(frozen=True)
class CheckResult:
    """Aggregated output for a contract text review."""

    word_count: int
    risk_level: str
    findings: list[CheckFinding] = field(default_factory=list)
