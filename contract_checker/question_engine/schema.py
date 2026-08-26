"""Immutable, standard-library schema primitives for a question inventory."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
import re


_SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_DOTTED_QUESTION_ID_PATTERN = re.compile(
    r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:_[a-z0-9]+)*)+$"
)
_SUPPORTED_SCHEMA_VERSION = 1


class AnswerState(str, Enum):
    """Canonical states for a future question answer."""

    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    HANDWRITING_DEPENDENCY = "HANDWRITING_DEPENDENCY"
    CLAUSE_PRESENT_VALUE_BLANK = "CLAUSE_PRESENT_VALUE_BLANK"


def _as_tuple(value: object, *, field_name: str) -> tuple[object, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field_name} must be a sequence")
    return tuple(value)


@dataclass(frozen=True)
class QuestionSpec:
    """Definition of one inventory question, without populated answers."""

    question_id: str
    domain: str
    purpose: str
    answer_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.question_id, str)
            or not _DOTTED_QUESTION_ID_PATTERN.fullmatch(self.question_id)
        ):
            raise ValueError("question_id must be a dotted snake_case identifier")
        if not isinstance(self.domain, str) or not self.domain.strip():
            raise ValueError("domain must not be empty")
        if not isinstance(self.purpose, str) or not self.purpose.strip():
            raise ValueError("purpose must not be empty")

        answer_fields = _as_tuple(self.answer_fields, field_name="answer_fields")
        if not answer_fields:
            raise ValueError("answer_fields must not be empty")
        for answer_field in answer_fields:
            if not isinstance(answer_field, str) or not _SNAKE_CASE_PATTERN.fullmatch(
                answer_field
            ):
                raise ValueError(
                    "answer_fields must contain only snake_case identifiers"
                )
        if len(set(answer_fields)) != len(answer_fields):
            raise ValueError("answer_fields must not contain duplicates")

        object.__setattr__(self, "answer_fields", answer_fields)


@dataclass(frozen=True)
class QuestionInventory:
    """Versioned, non-empty collection of unique question specifications."""

    schema_version: int
    questions: tuple[QuestionSpec, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version <= 0:
            raise ValueError("schema_version must be a positive integer")
        if self.schema_version != _SUPPORTED_SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version: {self.schema_version}")

        questions = _as_tuple(self.questions, field_name="questions")
        if not questions:
            raise ValueError("questions must not be empty")
        if not all(isinstance(question, QuestionSpec) for question in questions):
            raise ValueError("questions must contain only QuestionSpec values")

        question_ids = tuple(question.question_id for question in questions)
        if len(set(question_ids)) != len(question_ids):
            raise ValueError("questions must not contain duplicate question IDs")

        object.__setattr__(self, "questions", questions)


__all__ = ("AnswerState", "QuestionInventory", "QuestionSpec")
