"""Temporary Gemini OCR page for already-redacted contract images."""

from __future__ import annotations

import streamlit as st

from contract_checker.completeness import audit_completeness
from contract_checker.gemini_engine import (
    DEFAULT_GEMINI_MODEL,
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiRateLimitError,
    GeminiResponseError,
    ocr_redacted_pages_with_gemini,
)
from contract_checker.ocr_quality import assess_ocr_quality
from contract_checker.redaction import redact_personal_data_with_report
from contract_checker.validator import validate_contract_text


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
        "закрой личные данные масками и нажми 'Продолжить к распознаванию текста'."
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

api_key = st.text_input(
    "Gemini API-ключ для временного OCR",
    type="password",
    value=st.session_state.get("api_key_input", ""),
    help="Ключ не выводится в ошибки или отчёты.",
)
model = st.text_input(
    "Gemini model ID for OCR",
    value=st.session_state.get("manual_model_id", DEFAULT_GEMINI_MODEL) or DEFAULT_GEMINI_MODEL,
)
confirmed = st.checkbox(
    "Я подтверждаю, что подготовленные страницы проверены и личные данные на них закрыты масками."
)

if st.button("Распознать подготовленные страницы через Gemini OCR", type="primary", disabled=not api_key.strip() or not confirmed):
    try:
        with st.spinner("Gemini распознаёт замаскированные страницы..."):
            ocr_text = ocr_redacted_pages_with_gemini(
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
        redaction_result = redact_personal_data_with_report(assembled_text)
        redacted_text = redaction_result.redacted_text
        validation = validate_contract_text(redacted_text)
        completeness_audit = audit_completeness(redacted_text, text_usable=validation.usable)

        st.session_state.redacted_text = redacted_text
        st.session_state.redaction_report = redaction_result.report
        st.session_state.completeness_audit = completeness_audit
        st.session_state.validation_result = validation
        st.session_state.ocr_quality_report = ocr_quality_report
        st.session_state.gemini_ocr_raw_text = ocr_text
        st.session_state.pop("analysis_result", None)
        st.session_state.pop("validation_warnings", None)

        st.success("OCR готов. Текст уже прогнан через redaction, validation и completeness audit.")
        if ocr_quality_report.status == "good":
            st.success(f"OCR quality: good. Score {ocr_quality_report.score}.")
        elif ocr_quality_report.status == "warning":
            st.warning(f"OCR quality: warning. Score {ocr_quality_report.score}. Проверь текст перед анализом.")
        else:
            st.error("OCR quality is too low; reshoot pages before analysis.")
        st.info("Вернись на основную страницу: там появится обезличенный OCR-текст и будет доступна кнопка анализа, если текст пригоден.")

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
