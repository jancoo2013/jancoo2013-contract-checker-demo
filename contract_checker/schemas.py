"""Pydantic schemas for structured AI contract audit results.

The production dependency is Pydantic v2. A tiny compatibility fallback keeps local
imports/tests working in restricted environments where pip cannot fetch packages;
it preserves the extra-field rejection behavior that this MVP relies on.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Literal, get_args, get_origin, get_type_hints

try:  # pragma: no cover - exercised when dependency is available
    from pydantic import BaseModel, ConfigDict, Field
except ImportError:  # pragma: no cover - fallback for locked-down CI sandboxes
    class _FieldInfo:
        def __init__(self, default: Any = None, default_factory: Any = None, **_: Any) -> None:
            self.default = default
            self.default_factory = default_factory

    def Field(default: Any = None, default_factory: Any = None, **kwargs: Any) -> Any:  # noqa: N802
        return _FieldInfo(default=default, default_factory=default_factory, **kwargs)

    def ConfigDict(**kwargs: Any) -> dict[str, Any]:  # noqa: N802
        return kwargs

    class BaseModel:
        model_config: dict[str, Any] = {}

        def __init__(self, **data: Any) -> None:
            annotations = self._annotations()
            extra = set(data) - set(annotations)
            if extra and self.model_config.get("extra") == "forbid":
                raise ValueError(f"Extra fields are not permitted: {sorted(extra)}")
            for name, annotation in annotations.items():
                if name in data:
                    value = data[name]
                else:
                    default = getattr(type(self), name, None)
                    if isinstance(default, _FieldInfo):
                        value = default.default_factory() if default.default_factory else deepcopy(default.default)
                    elif default is not None:
                        value = deepcopy(default)
                    else:
                        raise ValueError(f"Missing required field: {name}")
                setattr(self, name, self._coerce(annotation, value))

        @classmethod
        def _annotations(cls) -> dict[str, Any]:
            annotations: dict[str, Any] = {}
            for base in reversed(cls.mro()):
                if base is object:
                    continue
                try:
                    resolved = get_type_hints(base, globalns=globals(), localns=globals())
                except Exception:
                    resolved = getattr(base, "__annotations__", {})
                annotations.update(resolved)
            annotations.pop("model_config", None)
            return annotations

        @classmethod
        def _coerce(cls, annotation: Any, value: Any) -> Any:
            origin = get_origin(annotation)
            args = get_args(annotation)
            if origin is Literal:
                if value not in args:
                    raise ValueError(f"Invalid literal value: {value!r}")
                return value
            if origin is list:
                item_type = args[0] if args else Any
                return [cls._coerce(item_type, item) for item in (value or [])]
            if origin is dict:
                return dict(value)
            if origin is None and isinstance(annotation, type) and issubclass(annotation, BaseModel):
                return value if isinstance(value, annotation) else annotation.model_validate(value)
            if origin is type(None):
                return None
            if origin is not None and type(None) in args:
                if value is None:
                    return None
                non_none = next(arg for arg in args if arg is not type(None))
                return cls._coerce(non_none, value)
            return value

        @classmethod
        def model_validate(cls, data: Any) -> Any:
            if isinstance(data, cls):
                return data
            if isinstance(data, dict):
                return cls(**data)
            raise ValueError(f"Cannot validate {type(data)!r}")

        @classmethod
        def model_validate_json(cls, data: str) -> Any:
            return cls.model_validate(json.loads(data))

        @classmethod
        def model_json_schema(cls) -> dict[str, Any]:
            return {"type": "object", "additionalProperties": False}

        def model_dump(self, mode: str = "python") -> dict[str, Any]:
            def dump(value: Any) -> Any:
                if isinstance(value, BaseModel):
                    return value.model_dump(mode=mode)
                if isinstance(value, list):
                    return [dump(item) for item in value]
                return value

            return {name: dump(getattr(self, name)) for name in self._annotations()}

        def model_dump_json(self, **_: Any) -> str:
            return json.dumps(self.model_dump(), ensure_ascii=False)

        def model_copy(self, update: dict[str, Any] | None = None) -> Any:
            payload = self.model_dump()
            payload.update(update or {})
            return type(self).model_validate(payload)


RiskLevel = Literal["red", "yellow", "normal", "unclear"]
Completeness = Literal["high", "medium", "low"]
OverallRiskProfile = Literal[
    "high_risk_found",
    "issues_to_clarify",
    "no_obvious_critical_risk_found",
    "text_unusable",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentQuality(StrictModel):
    usable: bool
    completeness: Completeness
    problems: list[str] = Field(default_factory=list)


class ClauseAnalysis(StrictModel):
    clause_id: str
    page: int | None = None
    source_quote_he: str
    explanation_ru: str
    category: str
    risk_level: RiskLevel
    tenant_obligation: str | None = None
    landlord_obligation: str | None = None
    financial_effect: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class RiskItem(StrictModel):
    title_ru: str
    level: Literal["red", "yellow"]
    page: int | None = None
    source_quote_he: str
    explanation_ru: str
    requested_change_ru: str | None = None


class MissingClause(StrictModel):
    title_ru: str
    explanation_ru: str
    importance: Literal["red", "yellow", "normal", "unclear"] = "yellow"
    requested_change_ru: str | None = None


class UnclearFragment(StrictModel):
    title_ru: str
    page: int | None = None
    source_quote_he: str
    explanation_ru: str
    requested_clarification_ru: str | None = None


class AgentQuestion(StrictModel):
    question_ru: str
    why_ru: str
    related_quote_he: str | None = None


class ProposedChange(StrictModel):
    title_ru: str
    source_quote_he: str | None = None
    proposed_text_ru: str
    priority: Literal["red", "yellow", "normal"] = "yellow"


class ContractAuditResult(StrictModel):
    risk_profile: OverallRiskProfile
    risk_profile_summary_ru: str
    document_quality: DocumentQuality
    clauses: list[ClauseAnalysis] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    missing_clauses: list[MissingClause] = Field(default_factory=list)
    unclear_fragments: list[UnclearFragment] = Field(default_factory=list)
    questions_to_agent: list[AgentQuestion] = Field(default_factory=list)
    proposed_changes: list[ProposedChange] = Field(default_factory=list)
