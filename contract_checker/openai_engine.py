"""OpenAI Responses API integration for structured contract audit."""

from __future__ import annotations

from typing import Any

from .prompt_builder import build_contract_audit_prompt
from .schemas import ContractAuditResult

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


class ContractAnalysisError(RuntimeError):
    """Safe user-facing error that never contains API keys or contract text."""


def _safe_error(prefix: str, exc: Exception) -> ContractAnalysisError:
    message = str(exc).splitlines()[0][:240]
    return ContractAnalysisError(f"{prefix}: {message}")


def _extract_parsed_response(response: Any) -> ContractAuditResult:
    parsed = getattr(response, "output_parsed", None)
    if parsed is not None:
        if isinstance(parsed, ContractAuditResult):
            return parsed
        return ContractAuditResult.model_validate(parsed)

    output = getattr(response, "output", None) or []
    for item in output:
        for content in getattr(item, "content", []) or []:
            refusal = getattr(content, "refusal", None)
            if refusal:
                raise ContractAnalysisError("Модель отказалась выполнить анализ")
            parsed = getattr(content, "parsed", None)
            if parsed is not None:
                return parsed if isinstance(parsed, ContractAuditResult) else ContractAuditResult.model_validate(parsed)

    text = getattr(response, "output_text", None)
    if text:
        return ContractAuditResult.model_validate_json(text)
    raise ContractAnalysisError("Ответ OpenAI не содержит структурированного результата")


def analyze_contract_with_openai(
    redacted_text: str,
    api_key: str,
    model: str = DEFAULT_OPENAI_MODEL,
) -> ContractAuditResult:
    """Analyze redacted text using OpenAI Structured Outputs and Pydantic schema."""

    if not api_key or not api_key.strip():
        raise ContractAnalysisError("Не указан OpenAI API-ключ")
    selected_model = (model or DEFAULT_OPENAI_MODEL).strip()

    try:
        from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, RateLimitError
    except ImportError as exc:  # pragma: no cover - environment setup issue
        raise ContractAnalysisError("Пакет openai не установлен") from exc

    client = OpenAI(api_key=api_key.strip(), timeout=60.0)
    messages = build_contract_audit_prompt(redacted_text)

    try:
        # New SDKs expose a parsing helper that accepts a Pydantic model directly.
        if hasattr(client.responses, "parse"):
            response = client.responses.parse(
                model=selected_model,
                input=messages,
                text_format=ContractAuditResult,
                max_output_tokens=8000,
            )
        else:
            response = client.responses.create(
                model=selected_model,
                input=messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "ContractAuditResult",
                        "schema": ContractAuditResult.model_json_schema(),
                        "strict": True,
                    }
                },
                max_output_tokens=8000,
            )
        return _extract_parsed_response(response)
    except AuthenticationError as exc:
        raise _safe_error("Ошибка аутентификации OpenAI", exc) from exc
    except RateLimitError as exc:
        raise _safe_error("Превышен лимит OpenAI", exc) from exc
    except APIConnectionError as exc:
        raise _safe_error("Не удалось подключиться к OpenAI", exc) from exc
    except APIStatusError as exc:
        raise _safe_error("OpenAI вернул ошибку", exc) from exc
    except ContractAnalysisError:
        raise
    except Exception as exc:
        raise _safe_error("Не удалось разобрать структурированный ответ OpenAI", exc) from exc
