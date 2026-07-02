"""Temporary Gemini OCR page for already-redacted contract images."""

from __future__ import annotations

import streamlit as st

from contract_checker.cache_keys import ocr_page_cache_key
from contract_checker.completeness import audit_completeness
from contract_checker.gemini_engine import (
    DEFAULT_GEMINI_MODEL,
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiRateLimitError,
    GeminiResponseError,
    ocr_redacted_pages_with_gemini,
)
from contract_checker.ocr_quality import assess_ocr_pages_quality, assess_ocr_quality
from contract_checker.redaction import redact_personal_data_with_report
from contract_checker.validator import validate_contract_text


_SHARED_GEMINI_API_KEY_STATE = "shared_gemini_api_key"
_OCR_API_KEY_INPUT_STATE = "ocr_api_key_input"
_GEMINI_ANALYSIS_RAW_RESPONSE_STATE = "gemini_analysis_raw_response"
_GEMINI_ANALYSIS_DEBUG_STATUS_STATE = "gemini_analysis_debug_status"
_GEMINI_ANALYSIS_DEBUG_ERROR_STATE = "gemini_analysis_debug_error"
_OCR_PAGE_CACHE_STATE = "gemini_ocr_page_cache"
_OCR_CACHE_STATUS_STATE = "gemini_ocr_cache_last_status"
_OCR_PROMPT_VERSION = "temporary_gemini_ocr_prompt_v1"


def _clear_gemini_analysis_state_for_source_change() -> None:
    for key in (
        _GEMINI_ANALYSIS_RAW_RESPONSE_STATE,
        _GEMINI_ANALYSIS_DEBUG_STATUS_STATE,
        _GEMINI_ANALYSIS_DEBUG_ERROR_STATE,
        "analysis_result",
        "validation_warnings",
    ):
        st.session_state.pop(key, None)


def _sync_api_key_widget_before_render(widget_key: str) -> None:
    shared_value = str(st.session_state.get(_SHARED_GEMINI_API_KEY_STATE) or "")
    widget_value = str(st.session_state.get(widget_key) or "")
    legacy_main_value = str(st.session_state.get("api_key_input") or "")
    if shared_value and not widget_value:
        st.session_state[widget_key] = shared_value
    elif widget_value and not shared_value:
        st.session_state[_SHARED_GEMINI_API_KEY_STATE] = widget_value
    elif legacy_main_value and not shared_value:
        st.session_state[_SHARED_GEMINI_API_KEY_STATE] = legacy_main_value
        st.session_state[widget_key] = legacy_main_value


def _sync_shared_api_key(value: str) -> str:
    value = value or ""
    st.session_state[_SHARED_GEMINI_API_KEY_STATE] = value
    return value


def _ocr_page_cache() -> dict[str, dict[str, object]]:
    cache = st.session_state.get(_OCR_PAGE_CACHE_STATE)
    if not isinstance(cache, dict):
        cache = {}
        st.session_state[_OCR_PAGE_CACHE_STATE] = cache
    return cache


def _page_label(page: dict[str, object], fallback_index: int) -> tuple[int, str]:
    page_index = int(page.get("page_index", fallback_index))
    page_number = page_index + 1
    filename = str(page.get("filename", f"page_{page_number}.png"))
    return page_number, filename


def _run_gemini_ocr_with_page_cache(
    *,
    prepared_pages: list[dict[str, object]],
    api_key: str,
    model: str,
) -> tuple[str, list[dict[str, object]]]:
    cache = _ocr_page_cache()
    page_texts: list[str] = []
    cache_statuses: list[dict[str, object]] = []
    selected_model = (model or DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL

    for fallback_index, page in enumerate(prepared_pages):
        page_number, filename = _page_label(page, fallback_index)
        image_bytes = page.get("image_bytes")
        if not isinstance(image_bytes, bytes) or not image_bytes:
            raise GeminiConfigurationError(f"Страница {page_number}: нет PNG-байтов для OCR")

        key = ocr_page_cache_key(
            image_bytes=image_bytes,
            model=selected_model,
            prompt_version=_OCR_PROMPT_VERSION,
        )
        cached = cache.get(key)
        if isinstance(cached, dict) and isinstance(cached.get("ocr_text"), str):
            page_text = str(cached["ocr_text"])
            cache_status = "hit"
        else:
            page_text = ocr_redacted_pages_with_gemini(
                prepared_pages=[page],
                api_key=api_key,
                model=selected_model,
            )
            cache[key] = {
                "ocr_text": page_text,
                "page_number": page_number,
                "filename": filename,
                "model": selected_model,
                "prompt_version": _OCR_PROMPT_VERSION,
            }
            cache_status = "miss"

        page_texts.append(page_text)
        cache_statuses.append(
            {
                "page_number": page_number,
                "filename": filename,
                "cache_status": cache_status,
            }
        )

    return "\n\n".join(page_texts).strip(), cache_statuses


def _render_ocr_cache_status(cache_statuses: list[dict[str, object]]) -> None:
    if not cache_statuses:
        return
    hits = sum(1 for item in cache_statuses if item.get("cache_status") == "hit")
    misses = sum(1 for item in cache_statuses if item.get("cache_status") == "miss")
    st.info(f"OCR cache: {hits} reused, {misses} sent to Gemini.")
    with st.expander("Advanced: OCR cache status by page", expanded=False):
        st.write(cache_statuses)


def _render_page_quality_summary(page_quality_reports: list[object]) -> None:
    if not page_quality_reports:
        return

    page_dicts = [report.to_dict() if hasattr(report, "to_dict") else dict(report) for report in page_quality_reports]
    poor_pages = [page for page in page_dicts if page.get("status") == "poor"]
    warning_pages = [page for page in page_dicts if page.get("status") == "warning"]

    if poor_pages:
        page_numbers = ", ".join(str(page.get("page_number")) for page in poor_pages)
        st.error(f"Нужно переснять страницы: {page_numbers}.")
        for page in poor_pages:
            st.warning(str(page.get("reshoot_hint_ru") or "Пересними страницу крупнее, ровнее и ярче."))
    elif warning_pages:
        page_numbers = ", ".join(str(page.get("page_number")) for page in warning_pages)
        st.warning(f"OCR по страницам: есть предупреждения на страницах {page_numbers}. Пересъёмка может улучшить анализ.")
    else:
        st.success("OCR по страницам: критичных проблем не найдено.")

    with st.expander("Advanced: OCR quality by page", expanded=False):
        st.write(page_dicts)


st.set_page_config(page_title="Temporary Gemini OCR", page_icon="🔎", layout="wide")
st.title("🔎 Step 5 — Run temporary OCR")
st.warning("Временный OCR только для закрытого тестирования.")
st.caption(
    "Используются только подготовленные замаскированные страницы. Это не production on-device OCR."
)

prepared_pages = st.session_state.get("image_redaction_ocr_pages") or []
if not prepared_pages:
    st.error(
        "Нет подготовленных страниц. Вернись на основную страницу, загрузи изображения, проверь все страницы, "
        "закрой личные данные масками и нажми 'Подготовить замаскированные страницы для OCR'."
    )
    st.stop()

st.success(f"Подготовлено страниц: {len(prepared_pages)}")

with st.expander("Advanced: подготовленные страницы", expanded=False):
    st.write(
        {
            "подготовлено страниц": len(prepared_pages),
            "режим": "temporary_gemini_ocr_on_redacted_pages",
            "production OCR": "нет",
        }
    )
    for page in prepared_pages:
        st.write(
            {
                "page_index": page.get("page_index"),
                "filename": page.get("filename"),
                "width": page.get("width"),
                "height": page.get("height"),
                "bytes": len(page.get("image_bytes") or b""),
            }
        )

_sync_api_key_widget_before_render(_OCR_API_KEY_INPUT_STATE)
api_key = st.text_input(
    "Gemini API-ключ для временного OCR",
    type="password",
    key=_OCR_API_KEY_INPUT_STATE,
    help="Ключ не выводится в ошибки или отчёты.",
)
api_key = _sync_shared_api_key(api_key)
model = st.text_input(
    "Gemini model ID for OCR",
    value=st.session_state.get("manual_model_id", DEFAULT_GEMINI_MODEL) or DEFAULT_GEMINI_MODEL,
)
confirmed = st.checkbox(
    "Я подтверждаю, что подготовленные страницы проверены и личные данные на них закрыты масками."
)

if st.button("Распознать подготовленные страницы через Gemini OCR", type="primary", disabled=not api_key.strip() or not confirmed):
    try:
        with st.spinner("Gemini распознаёт замаскированные страницы. Уже распознанные неизменённые страницы берутся из session cache..."):
            ocr_text, cache_statuses = _run_gemini_ocr_with_page_cache(
                prepared_pages=prepared_pages,
                api_key=api_key,
                model=model,
            )
    except (GeminiAuthenticationError, GeminiConfigurationError):
        st.error("Не удалось запустить Gemini OCR. Проверь API-ключ и модель.")
    except GeminiRateLimitError:
        st.error("Достигнут лимит запросов Gemini API.")
    except GeminiResponseError as exc:
        error_text = str(exc).lower()
        if "safety" in error_text or "refusal" in error_text:
            st.error("Gemini отказался распознавать одну из страниц. OCR не завершён.")
        else:
            st.error("Gemini OCR не вернул usable text. OCR не завершён.")
    else:
        assembled_text = (
            "--- OCR SOURCE: temporary_gemini_ocr_on_redacted_pages ---\n"
            f"--- IMAGE PAGES PREPARED: {len(prepared_pages)} ---\n\n"
            f"{ocr_text}"
        )
        ocr_quality_report = assess_ocr_quality(ocr_text, expected_pages=len(prepared_pages))
        ocr_page_quality_reports = assess_ocr_pages_quality(ocr_text, expected_pages=len(prepared_pages))
        redaction_result = redact_personal_data_with_report(assembled_text)
        redacted_text = redaction_result.redacted_text
        validation = validate_contract_text(redacted_text)
        completeness_audit = audit_completeness(redacted_text, text_usable=validation.usable)

        _clear_gemini_analysis_state_for_source_change()
        st.session_state.redacted_text = redacted_text
        st.session_state.redaction_report = redaction_result.report
        st.session_state.completeness_audit = completeness_audit
        st.session_state.validation_result = validation
        st.session_state.ocr_quality_report = ocr_quality_report
        st.session_state.ocr_page_quality_reports = ocr_page_quality_reports
        st.session_state.gemini_ocr_raw_text = ocr_text
        st.session_state[_OCR_CACHE_STATUS_STATE] = cache_statuses

        st.success("OCR готов. Текст уже прогнан через redaction, validation и completeness audit.")
        _render_ocr_cache_status(cache_statuses)
        if ocr_quality_report.status == "good":
            st.success(f"OCR quality: good. Score {ocr_quality_report.score}.")
        elif ocr_quality_report.status == "warning":
            st.warning(f"OCR quality: warning. Score {ocr_quality_report.score}. Если это важный договор, пересними страницы с предупреждениями.")
        else:
            st.error("OCR quality is too low; reshoot pages before analysis.")
        st.info("Вернись на основную страницу: там появится обезличенный OCR-текст и будет доступна кнопка анализа, если текст пригоден.")

last_cache_statuses = st.session_state.get(_OCR_CACHE_STATUS_STATE) or []
if last_cache_statuses:
    _render_ocr_cache_status(last_cache_statuses)

ocr_raw_text = st.session_state.get("gemini_ocr_raw_text")
if ocr_raw_text:
    with st.expander("Advanced: последний сырой OCR-текст", expanded=False):
        st.text_area("Raw OCR", value=ocr_raw_text, height=360, disabled=True, label_visibility="collapsed")

validation = st.session_state.get("validation_result")
if validation:
    st.subheader("Статус OCR-текста")
    if validation.usable:
        st.success("OCR-текст пригоден для дальнейшего AI-анализа.")
    else:
        st.warning("OCR-текст пока не прошёл validation как пригодный договор.")
    with st.expander("Advanced: метрики OCR-текста", expanded=False):
        st.write(
            {
                "полнота": validation.completeness,
                "символы иврита": validation.hebrew_char_count,
                "признаки аренды": validation.indicator_count,
                "пункты/абзацы": validation.clause_count,
                "доля мусора": validation.garbage_ratio,
                "разделители страниц": validation.page_separator_count,
            }
        )

ocr_quality_report = st.session_state.get("ocr_quality_report")
if ocr_quality_report:
    with st.expander("Advanced: OCR quality details", expanded=False):
        if hasattr(ocr_quality_report, "to_dict"):
            st.write(ocr_quality_report.to_dict())
        else:
            st.write(ocr_quality_report)

ocr_page_quality_reports = st.session_state.get("ocr_page_quality_reports") or []
_render_page_quality_summary(ocr_page_quality_reports)
