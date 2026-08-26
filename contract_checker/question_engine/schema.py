"""Strict, provider-independent schema primitives for a future question inventory.

This module defines only the shape of inventory entries. It intentionally contains
no populated questions, contract-specific answers, statutory conclusions, or
runtime model/provider integration.
"""

from typing import Literal

from contract_checker.schemas import Field, StrictModel


AnswerState = Literal[
    "FOUND",
    "NOT_FOUND",
    "AMBIGUOUS",
    "HANDWRITING_DEPENDENCY",
    "CLAUSE_PRESENT_VALUE_BLANK",
]

EvidenceLayer = Literal[
    "CONTRACT_FACT",
    "STATUTORY_RULE",
    "PRODUCT_EXPLANATION",
]

QuestionKind = Literal[
    "CORE",
    "CONDITIONAL",
    "CATCH_ALL",
]

AnswerValueType = Literal[
    "TEXT",
    "BOOLEAN",
    "INTEGER",
    "DECIMAL",
    "DATE",
    "MONEY",
    "DURATION",
    "ENUM",
    "REFERENCE",
]


class AnswerFieldDefinition(StrictModel):
    """A topic-specific field that a future question may populate."""

    field_id: str
    value_type: AnswerValueType
    required: bool = True


class EvidenceTarget(StrictModel):
    """A value-free target for deterministic evidence references."""

    target_id: str
    layer: EvidenceLayer = "CONTRACT_FACT"
    required: bool = True


class ConditionalFollowUp(StrictModel):
    """A follow-up question activated by one or more canonical answer states."""

    question_id: str
    when_states: list[AnswerState]


class QuestionDefinition(StrictModel):
    """Definition of one future deterministic or conditional question."""

    question_id: str
    topic_id: str
    kind: QuestionKind = "CORE"
    answer_fields: list[AnswerFieldDefinition] = Field(default_factory=list)
    evidence_targets: list[EvidenceTarget] = Field(default_factory=list)
    conditional_follow_ups: list[ConditionalFollowUp] = Field(default_factory=list)
    statutory_rule_ids: list[str] = Field(default_factory=list)
    remediation_ids: list[str] = Field(default_factory=list)


class QuestionInventory(StrictModel):
    """Versioned container for inventory definitions added by later slices."""

    schema_version: Literal[1] = 1
    questions: list[QuestionDefinition] = Field(default_factory=list)


__all__ = (
    "AnswerFieldDefinition",
    "AnswerState",
    "AnswerValueType",
    "ConditionalFollowUp",
    "EvidenceLayer",
    "EvidenceTarget",
    "QuestionDefinition",
    "QuestionInventory",
    "QuestionKind",
)
