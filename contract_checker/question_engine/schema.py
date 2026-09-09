"""Immutable, standard-library schema primitives for the Question Engine."""

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


class PresenceStatus(str, Enum):
    """Whether the requested contract mechanism/fact can be located."""

    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class ValueStatus(str, Enum):
    """Condition of a requested value, independent of mechanism presence."""

    PROVIDED = "PROVIDED"
    OMITTED = "OMITTED"
    BLANK = "BLANK"
    UNKNOWN = "UNKNOWN"


class EvidenceStatus(str, Enum):
    """Whether the provided source material is sufficient for this answer."""

    SUFFICIENT = "SUFFICIENT"
    HANDWRITING_DEPENDENCY = "HANDWRITING_DEPENDENCY"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    UNREADABLE = "UNREADABLE"


class SourceStatus(str, Enum):
    """Clarity/consistency of the source wording itself."""

    CLEAR = "CLEAR"
    AMBIGUOUS = "AMBIGUOUS"
    CONTRADICTORY = "CONTRADICTORY"


class DocumentLifecycle(str, Enum):
    """Known lifecycle context for interpreting source states such as blanks."""

    UNKNOWN = "UNKNOWN"
    TEMPLATE = "TEMPLATE"
    DRAFT = "DRAFT"
    EXECUTED = "EXECUTED"


@dataclass(frozen=True)
class AnswerState:
    """Minimal orthogonal state envelope for a future question answer."""

    presence: PresenceStatus
    value: ValueStatus
    evidence: EvidenceStatus
    source: SourceStatus
    lifecycle: DocumentLifecycle

    def __post_init__(self) -> None:
        expected = (
            ("presence", self.presence, PresenceStatus),
            ("value", self.value, ValueStatus),
            ("evidence", self.evidence, EvidenceStatus),
            ("source", self.source, SourceStatus),
            ("lifecycle", self.lifecycle, DocumentLifecycle),
        )
        for field_name, value, enum_type in expected:
            if not isinstance(value, enum_type):
                raise ValueError(f"{field_name} must be a {enum_type.__name__}")


def _as_tuple(value: object, *, field_name: str) -> tuple[object, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field_name} must be a sequence")
    return tuple(value)


@dataclass(frozen=True)
class MechanismProperty:
    """One named property attached to one repeatable mechanism instance."""

    name: str
    value: object
    state: AnswerState

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _SNAKE_CASE_PATTERN.fullmatch(self.name):
            raise ValueError("property name must be a snake_case identifier")
        if not isinstance(self.state, AnswerState):
            raise ValueError("state must be an AnswerState")


@dataclass(frozen=True)
class MechanismInstance:
    """One locally identified mechanism whose properties cannot drift to peers."""

    mechanism_id: str
    mechanism_type: str
    properties: tuple[MechanismProperty, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.mechanism_id, str)
            or not _SNAKE_CASE_PATTERN.fullmatch(self.mechanism_id)
        ):
            raise ValueError("mechanism_id must be a snake_case identifier")
        if (
            not isinstance(self.mechanism_type, str)
            or not _SNAKE_CASE_PATTERN.fullmatch(self.mechanism_type)
        ):
            raise ValueError("mechanism_type must be a snake_case identifier")

        properties = _as_tuple(self.properties, field_name="properties")
        if not all(isinstance(item, MechanismProperty) for item in properties):
            raise ValueError("properties must contain only MechanismProperty values")
        property_names = tuple(item.name for item in properties)
        if len(set(property_names)) != len(property_names):
            raise ValueError("properties must not contain duplicate names")
        object.__setattr__(self, "properties", properties)


@dataclass(frozen=True)
class MechanismCollection:
    """Repeatable mechanisms in one domain with collection-local stable IDs."""

    domain: str
    mechanisms: tuple[MechanismInstance, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.domain, str) or not _SNAKE_CASE_PATTERN.fullmatch(self.domain):
            raise ValueError("domain must be a snake_case identifier")

        mechanisms = _as_tuple(self.mechanisms, field_name="mechanisms")
        if not all(isinstance(item, MechanismInstance) for item in mechanisms):
            raise ValueError("mechanisms must contain only MechanismInstance values")
        mechanism_ids = tuple(item.mechanism_id for item in mechanisms)
        if len(set(mechanism_ids)) != len(mechanism_ids):
            raise ValueError("mechanisms must not contain duplicate mechanism IDs")
        object.__setattr__(self, "mechanisms", mechanisms)

    @property
    def cardinality(self) -> int:
        return len(self.mechanisms)


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


__all__ = (
    "AnswerState",
    "DocumentLifecycle",
    "EvidenceStatus",
    "MechanismCollection",
    "MechanismInstance",
    "MechanismProperty",
    "PresenceStatus",
    "QuestionInventory",
    "QuestionSpec",
    "SourceStatus",
    "ValueStatus",
)
