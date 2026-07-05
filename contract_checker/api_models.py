"""Pydantic models for the first mobile/backend API boundary."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .schemas import ContractAuditResult


class StrictAPIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalyzeRedactedMetadata(StrictAPIModel):
    privacy_review_confirmed: Literal[True]
    client_request_id: str | None = Field(default=None, max_length=128)


class OCRPageQualityResponse(StrictAPIModel):
    page_number: int
    status: Literal["good", "warning", "poor"]
    score: int
    reshoot_hint_ru: str = ""


class OCRQualityResponse(StrictAPIModel):
    status: Literal["good", "warning", "poor"]
    score: int
    pages: list[OCRPageQualityResponse] = Field(default_factory=list)


class TextValidationResponse(StrictAPIModel):
    usable: bool
    completeness: str
    problems: list[str] = Field(default_factory=list)


class CompletenessFindingResponse(StrictAPIModel):
    document_type: str
    title_ru: str
    severity: Literal["red", "yellow", "normal"]
    evidence_block_ids: list[str] = Field(default_factory=list)
    explanation_ru: str
    question_ru: str


class CompletenessAuditResponse(StrictAPIModel):
    status: Literal[
        "referenced_documents_need_check",
        "no_referenced_documents_found",
        "text_unusable",
    ]
    summary_ru: str
    findings: list[CompletenessFindingResponse] = Field(default_factory=list)


class AnalyzeRedactedContractResponse(StrictAPIModel):
    request_id: str
    status: Literal["completed"] = "completed"
    ocr_quality: OCRQualityResponse
    text_validation: TextValidationResponse
    completeness_audit: CompletenessAuditResponse
    report: ContractAuditResult
    evidence_warnings: list[str] = Field(default_factory=list)


class APIErrorBody(StrictAPIModel):
    code: str
    message_ru: str
    details: dict[str, Any] = Field(default_factory=dict)


class APIErrorResponse(StrictAPIModel):
    request_id: str
    status: Literal["error"] = "error"
    error: APIErrorBody
