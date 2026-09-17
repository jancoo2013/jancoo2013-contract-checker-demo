"""Gemini structured-output integration for redacted contract audit."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
import re
from typing import Any

from .cache_keys import analysis_cache_key
from .evidence_blocks import build_evidence_blocks
from .prompt_builder import (
    SYSTEM_PROMPT_RU,
    build_contract_audit_prompt,
    question_engine_expected_answer_fields,
)
from .schemas import ContractAuditResult

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"

# Test seams. In production these are loaded lazily from google-genai so importing
# the Streamlit app does not require an API key or initialize an SDK client.
genai: Any = None
_genai_types: Any = None

# Session-scoped in-memory cache. Values are raw Gemini analysis responses for
# already-redacted contract text. No API keys are stored.
_ANALYSIS_RAW_TEXT_CACHE: dict[str, dict[str, str]] = {}


class GeminiError(Exception):
    """Base controlled Gemini error that never contains API keys or contract text."""


class GeminiConfigurationError(GeminiError):
    """Gemini SDK or local configuration is missing/invalid."""


class GeminiAuthenticationError(GeminiError):
    """Gemini rejected the supplied API key or credentials."""


class GeminiRateLimitError(GeminiError):
    """Gemini quota or rate limit was reached, with safe retry metadata."""

    def __init__(
        self,
        message: str,
        *,
        quota_scope: str = "unknown",
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.quota_scope = quota_scope
        self.retry_after_seconds = retry_after_seconds


class GeminiResponseError(GeminiError):
    """Gemini returned no usable structured response, malformed JSON, or refusal."""

    def __init__(self, message: str, *, retryable_provider: bool = False) -> None:
        super().__init__(message)
        self.retryable_provider = retryable_provider


@dataclass(frozen=True)
class GeminiAnalysisDebugResult:
    raw_text: str
    parsed_result: ContractAuditResult | None
    parse_error: str | None


def _streamlit_session_id() -> str | None:
    """Return the current Streamlit session ID when running inside Streamlit."""

    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except Exception:
        return None
    try:
        context = get_script_run_ctx()
    except Exception:
        return None
    session_id = getattr(context, "session_id", None)
    return str(session_id) if session_id else None


def _analysis_schema_version() -> str:
    return json.dumps(ContractAuditResult.model_json_schema(), ensure_ascii=False, sort_keys=True)


def _analysis_cache_get(cache_key: str) -> str | None:
    session_id = _streamlit_session_id()
    if not session_id:
        return None
    return _ANALYSIS_RAW_TEXT_CACHE.get(session_id, {}).get(cache_key)


def _analysis_cache_set(cache_key: str, raw_text: str) -> None:
    session_id = _streamlit_session_id()
    if not session_id:
        return
    _ANALYSIS_RAW_TEXT_CACHE.setdefault(session_id, {})[cache_key] = raw_text


def clear_current_session_analysis_cache() -> None:
    """Clear cached raw Gemini analysis responses for the current Streamlit session."""

    session_id = _streamlit_session_id()
    if not session_id:
        return
    _ANALYSIS_RAW_TEXT_CACHE.pop(session_id, None)


def _load_genai_modules() -> tuple[Any, Any]:
    global genai, _genai_types
    if genai is None:
        from google import genai as loaded_genai

        genai = loaded_genai
    if _genai_types is None:
        from google.genai import types as loaded_types

        _genai_types = loaded_types
    return genai, _genai_types


def _safe_message(prefix: str, _exc: Exception) -> str:
    # Never include SDK exception text because it could contain request metadata,
    # API keys, or snippets of contract text.
    return prefix


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def _error_payload(exc: Exception) -> dict[str, Any]:
    details = getattr(exc, "details", None)
    if not isinstance(details, dict):
        return {}
    nested = details.get("error")
    return nested if isinstance(nested, dict) else details


def _error_detail_items(exc: Exception) -> list[dict[str, Any]]:
    items = _error_payload(exc).get("details", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _parse_retry_delay(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, float(value))
    if isinstance(value, str):
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)s\s*", value)
        return float(match.group(1)) if match else None
    if isinstance(value, dict):
        seconds = value.get("seconds", 0)
        nanos = value.get("nanos", 0)
        try:
            return max(0.0, float(seconds) + float(nanos) / 1_000_000_000)
        except (TypeError, ValueError):
            return None
    return None


def _retry_after_seconds(exc: Exception) -> float | None:
    for item in _error_detail_items(exc):
        item_type = str(item.get("@type", "")).lower()
        if "retryinfo" in item_type:
            delay = _parse_retry_delay(item.get("retryDelay", item.get("retry_delay")))
            if delay is not None:
                return delay

    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None:
        try:
            value = headers.get("Retry-After")
        except Exception:
            value = None
        delay = _parse_retry_delay(value)
        if delay is None and isinstance(value, str):
            try:
                delay = max(0.0, float(value.strip()))
            except ValueError:
                delay = None
        if delay is not None:
            return delay
    return None


def _quota_scope(exc: Exception) -> str:
    daily_markers = ("perday", "per_day", "per-day", "requestsperday", "requests_per_day", "daily")
    for item in _error_detail_items(exc):
        item_type = str(item.get("@type", "")).lower()
        if "quotafailure" not in item_type:
            continue
        violations = item.get("violations", [])
        if not isinstance(violations, list):
            continue
        for violation in violations:
            if not isinstance(violation, dict):
                continue
            safe_fields = {
                key: violation.get(key)
                for key in ("quotaId", "quotaMetric", "quotaDimensions", "description")
            }
            compact = json.dumps(safe_fields, ensure_ascii=True, sort_keys=True).lower()
            if any(marker in compact for marker in daily_markers):
                return "daily"
    return "temporary_or_unknown"


def _analysis_http_options(types_module: Any) -> Any:
    """Disable SDK-owned retries so the runner controls request amplification."""

    retry_options_type = getattr(types_module, "HttpRetryOptions", None)
    retry_options = retry_options_type(attempts=1) if retry_options_type else {"attempts": 1}
    http_options_type = getattr(types_module, "HttpOptions", None)
    options = {"retry_options": retry_options}
    return http_options_type(**options) if http_options_type else options


def _classify_sdk_error(exc: Exception) -> GeminiError:
    code = _status_code(exc)
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if code in {401, 403} or "auth" in name or "permission" in name or "api key" in text:
        return GeminiAuthenticationError(_safe_message("Gemini authentication failed", exc))
    if code == 429 or "ratelimit" in name or "rate_limit" in name or "quota" in name or "quota" in text:
        return GeminiRateLimitError(
            _safe_message("Gemini quota or rate limit reached", exc),
            quota_scope=_quota_scope(exc),
            retry_after_seconds=_retry_after_seconds(exc),
        )
    if code is not None and 400 <= code < 500:
        return GeminiResponseError(_safe_message("Gemini rejected the request", exc))
    if code is not None and code >= 500:
        return GeminiResponseError(
            _safe_message("Gemini service error", exc),
            retryable_provider=True,
        )
    if any(token in name for token in ("timeout", "connection", "network", "transport")):
        return GeminiResponseError(
            _safe_message("Gemini network error", exc),
            retryable_provider=True,
        )
    return GeminiResponseError(_safe_message("Gemini request failed", exc))


def _is_safety_or_refusal(response: Any) -> bool:
    prompt_feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(prompt_feedback, "block_reason", None)
    if block_reason:
        return True

    candidates = getattr(response, "candidates", None) or []
    refusal_markers = {"SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "RECITATION"}
    for candidate in candidates:
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason and str(finish_reason).split(".")[-1].upper() in refusal_markers:
            return True
    return False


def _response_text(response: Any) -> str:
    if _is_safety_or_refusal(response):
        raise GeminiResponseError("Gemini safety refusal")
    try:
        text = getattr(response, "text", None)
    except Exception as exc:
        if _is_safety_or_refusal(response):
            raise GeminiResponseError("Gemini safety refusal") from exc
        raise GeminiResponseError(_safe_message("Gemini response text is unavailable", exc)) from exc
    if not isinstance(text, str) or not text.strip():
        if _is_safety_or_refusal(response):
            raise GeminiResponseError("Gemini safety refusal")
        raise GeminiResponseError("Gemini returned an empty response")
    return text.strip()


def _build_contents(redacted_text: str) -> str:
    messages = build_contract_audit_prompt(redacted_text)
    system = next((item["content"] for item in messages if item.get("role") == "system"), "")
    user = next((item["content"] for item in messages if item.get("role") == "user"), "")
    return f"{system}\n\n{user}".strip()


def _build_config(types_module: Any) -> Any:
    config = {
        "response_mime_type": "application/json",
        "response_json_schema": ContractAuditResult.model_json_schema(),
        "max_output_tokens": 8000,
        "temperature": 0.2,
    }
    generate_config = getattr(types_module, "GenerateContentConfig", None)
    return generate_config(**config) if generate_config else config


def _build_ocr_config(types_module: Any) -> Any:
    config = {
        "max_output_tokens": 8000,
        "temperature": 0.0,
    }
    generate_config = getattr(types_module, "GenerateContentConfig", None)
    return generate_config(**config) if generate_config else config


def _ocr_prompt(page_number: int, filename: str) -> str:
    return (
        "You are an OCR engine for Israeli Hebrew rental contracts.\n"
        "Extract all visible printed Hebrew text from this already-redacted page image.\n"
        "Return OCR text only. Do not translate. Do not summarize. Do not explain.\n"
        "Preserve line breaks when reasonably possible.\n"
        "If a line is hidden by a black privacy mask, write [MASKED].\n"
        "If a character is unclear, keep the closest visible Hebrew character rather than guessing legal meaning.\n\n"
        f"Page: {page_number}\n"
        f"Filename: {filename}"
    )


def _image_part(types_module: Any, image_bytes: bytes) -> Any:
    part = getattr(types_module, "Part", None)
    from_bytes = getattr(part, "from_bytes", None) if part is not None else None
    if from_bytes is None:
        raise GeminiConfigurationError("google-genai image part API is unavailable")
    return from_bytes(data=image_bytes, mime_type="image/png")


def ocr_redacted_pages_with_gemini(
    prepared_pages: list[dict[str, Any]],
    api_key: str,
    model: str = DEFAULT_GEMINI_MODEL,
) -> str:
    """Run temporary Gemini OCR on already-redacted page images.

    This is a test bridge only. It must receive redacted images produced by the
    manual masking flow, not raw contract photos.
    """

    if not api_key or not api_key.strip():
        raise GeminiConfigurationError("Не указан Gemini API-ключ")
    if not prepared_pages:
        raise GeminiConfigurationError("Нет подготовленных замаскированных страниц для OCR")
    if genai is None and importlib.util.find_spec("google.genai") is None:
        raise GeminiConfigurationError("Пакет google-genai не установлен")

    genai_module, types_module = _load_genai_modules()
    selected_model = (model or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    config = _build_ocr_config(types_module)

    try:
        client = genai_module.Client(api_key=api_key.strip())
    except Exception as exc:
        raise _classify_sdk_error(exc) from exc

    page_texts: list[str] = []
    for page in prepared_pages:
        page_index = int(page.get("page_index", len(page_texts)))
        page_number = page_index + 1
        filename = str(page.get("filename", f"page_{page_number}.png"))
        image_bytes = page.get("image_bytes")
        if not isinstance(image_bytes, bytes) or not image_bytes:
            raise GeminiConfigurationError(f"Страница {page_number}: нет PNG-байтов для OCR")

        contents = [
            _ocr_prompt(page_number=page_number, filename=filename),
            _image_part(types_module, image_bytes),
        ]
        try:
            response = client.models.generate_content(model=selected_model, contents=contents, config=config)
        except GeminiError:
            raise
        except Exception as exc:
            raise _classify_sdk_error(exc) from exc

        text = _response_text(response)
        page_texts.append(f"--- PAGE {page_number}: {filename} ---\n{text}")

    return "\n\n".join(page_texts).strip()


def generate_contract_analysis_raw_text(
    redacted_text: str,
    api_key: str,
    model: str = DEFAULT_GEMINI_MODEL,
) -> str:
    """Generate raw Gemini structured-output text for already-redacted contract text."""

    if not api_key or not api_key.strip():
        raise GeminiConfigurationError("Не указан Gemini API-ключ")
    if not redacted_text or not redacted_text.strip():
        raise GeminiConfigurationError("Нет обезличенного текста для анализа")

    selected_model = (model or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    cache_key = analysis_cache_key(
        redacted_text=redacted_text,
        model=selected_model,
        prompt_text=SYSTEM_PROMPT_RU,
        schema_version=_analysis_schema_version(),
    )
    cached_raw_text = _analysis_cache_get(cache_key)
    if cached_raw_text is not None:
        return cached_raw_text

    if genai is None and importlib.util.find_spec("google.genai") is None:
        raise GeminiConfigurationError("Пакет google-genai не установлен")

    genai_module, types_module = _load_genai_modules()

    contents = _build_contents(redacted_text)
    config = _build_config(types_module)

    try:
        client = genai_module.Client(
            api_key=api_key.strip(),
            http_options=_analysis_http_options(types_module),
        )
        response = client.models.generate_content(model=selected_model, contents=contents, config=config)
    except GeminiError:
        raise
    except Exception as exc:
        raise _classify_sdk_error(exc) from exc

    raw_text = _response_text(response)
    _analysis_cache_set(cache_key, raw_text)
    return raw_text


def _validate_question_engine_answers(
    result: ContractAuditResult,
    redacted_text: str,
) -> ContractAuditResult:
    """Fail closed unless every deterministic core question is explicitly answered."""

    expected = question_engine_expected_answer_fields()
    valid_evidence_ids = {block.block_id for block in build_evidence_blocks(redacted_text)}
    seen: set[str] = set()

    for answer in result.question_engine_answers:
        question_id = answer.question_id
        if question_id not in expected or question_id in seen:
            raise GeminiResponseError("Gemini returned invalid Question Engine coverage")
        seen.add(question_id)

        if len(answer.values) != len(expected[question_id]):
            raise GeminiResponseError("Gemini returned incomplete Question Engine values")

        if len(set(answer.evidence_block_ids)) != len(answer.evidence_block_ids):
            raise GeminiResponseError("Gemini returned invalid Question Engine evidence")
        if any(block_id not in valid_evidence_ids for block_id in answer.evidence_block_ids):
            raise GeminiResponseError("Gemini returned invalid Question Engine evidence")

        if answer.status == "NOT_FOUND":
            if any(value is not None for value in answer.values):
                raise GeminiResponseError("Gemini returned inconsistent Question Engine state")
        else:
            if not answer.evidence_block_ids:
                raise GeminiResponseError("Gemini returned ungrounded Question Engine answer")
            if answer.status == "FOUND" and not any(
                isinstance(value, str) and value.strip() for value in answer.values
            ):
                raise GeminiResponseError("Gemini returned empty Question Engine answer")

    if seen != set(expected):
        raise GeminiResponseError("Gemini omitted mandatory Question Engine answers")

    return result


def analyze_contract_with_gemini(
    redacted_text: str,
    api_key: str,
    model: str = DEFAULT_GEMINI_MODEL,
) -> ContractAuditResult:
    """Analyze already-redacted contract text with Gemini structured JSON output."""

    text = generate_contract_analysis_raw_text(redacted_text=redacted_text, api_key=api_key, model=model)
    try:
        result = ContractAuditResult.model_validate_json(text)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise GeminiResponseError("Gemini returned malformed structured JSON") from exc
    return _validate_question_engine_answers(result, redacted_text)


def analyze_contract_with_gemini_debug(
    redacted_text: str,
    api_key: str,
    model: str = DEFAULT_GEMINI_MODEL,
) -> GeminiAnalysisDebugResult:
    """Analyze with raw response capture for closed developer diagnostics."""

    raw_text = generate_contract_analysis_raw_text(redacted_text=redacted_text, api_key=api_key, model=model)
    try:
        parsed = ContractAuditResult.model_validate_json(raw_text)
        parsed = _validate_question_engine_answers(parsed, redacted_text)
    except (ValueError, TypeError, json.JSONDecodeError, GeminiResponseError) as exc:
        return GeminiAnalysisDebugResult(
            raw_text=raw_text,
            parsed_result=None,
            parse_error=type(exc).__name__,
        )
    return GeminiAnalysisDebugResult(raw_text=raw_text, parsed_result=parsed, parse_error=None)
