"""Framework-agnostic contract analysis orchestration.

This module composes the existing Gemini structured-analysis integration with
existing deterministic evidence validation. It does not perform OCR, redact
PII, or depend on Streamlit state.
"""

from __future__ import annotations

from dataclasses import dataclass

from .gemini_engine import DEFAULT_GEMINI_MODEL, analyze_contract_with_gemini
from .output_validator import validate_model_evidence
from .schemas import ContractAuditResult


@dataclass(frozen=True)
class AnalysisPipelineResult:
    result: ContractAuditResult
    evidence_warnings: list[str]


def run_contract_analysis(
    redacted_text: str,
    api_key: str,
    *,
    model: str = DEFAULT_GEMINI_MODEL,
) -> AnalysisPipelineResult:
    """Run structured Gemini analysis and deterministic evidence validation.

    The caller must provide already-redacted contract text. Gemini integration
    remains responsible for request handling and schema validation; this layer
    only composes that result with deterministic evidence validation.
    """

    parsed_result = analyze_contract_with_gemini(
        redacted_text=redacted_text,
        api_key=api_key,
        model=model,
    )
    validated = validate_model_evidence(parsed_result, redacted_text)
    return AnalysisPipelineResult(
        result=validated.result,
        evidence_warnings=list(validated.warnings),
    )
