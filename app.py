"""Public Streamlit demo for deterministic contract checks."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from contract_checker.ocr_image import ocr_image_to_text
from contract_checker.pipeline import analyze_contract_text
from contract_checker.report import result_to_markdown
from contract_checker.web_helpers import (
    finding_detail_label,
    finding_title_label,
    recommendation_label,
    result_summary,
    sample_contract_text,
    status_badge,
    status_label,
)


def _result_payload(result: Any) -> dict[str, Any]:
    """Build the raw JSON payload shown in the public demo."""

    return asdict(result)


def _render_analysis(result: Any) -> None:
    """Render deterministic analysis sections for pasted or OCR text."""

    import streamlit as st

    summary = result_summary(result)

    st.subheader("Краткий отчёт")
    cols = st.columns(4)
    for column, (label, value) in zip(cols, summary.items(), strict=True):
        column.metric(label, value)

    st.subheader("Найденные поля")
    fields = [
        {
            "Поле": finding_title_label(finding.title),
            "Статус": status_label(finding.status),
            "Комментарий": finding_detail_label(finding),
        }
        for finding in result.findings
    ]
    st.dataframe(fields, use_container_width=True, hide_index=True)

    st.subheader("Проверки")
    for finding in result.findings:
        title = finding_title_label(finding.title)
        with st.expander(f"{status_badge(finding.status)} — {title}", expanded=True):
            st.write(finding_detail_label(finding))
            st.write(f"**Рекомендация:** {recommendation_label(finding)}")

    st.subheader("Зоны для ручной проверки")
    crop_requests = [
        {
            "Тема": finding_title_label(finding.title),
            "Что проверить": "Проверь соответствующий фрагмент договора вручную: рукописный иврит не считается подтверждённым.",
        }
        for finding in result.findings
        if finding.status in {"Missing", "Caution"}
    ]
    if crop_requests:
        st.dataframe(crop_requests, use_container_width=True, hide_index=True)
    else:
        st.success("Дополнительные зоны для ручной проверки не найдены простыми правилами демо.")

    st.subheader("Сырой JSON")
    st.json(_result_payload(result))

    st.subheader("Экспорт")
    report_markdown = result_to_markdown(result)
    st.download_button(
        "Скачать Markdown-отчёт",
        data=report_markdown,
        file_name="contract-check-report.md",
        mime="text/markdown",
    )
    st.markdown(report_markdown)


def _render_paste_tab() -> None:
    """Render the pasted-text workflow."""

    import streamlit as st

    if "contract_text" not in st.session_state:
        st.session_state.contract_text = ""

    if st.button("Загрузить синтетический пример"):
        st.session_state.contract_text = sample_contract_text()

    contract_text = st.text_area(
        "Текст договора",
        key="contract_text",
        height=280,
        placeholder="Вставь сюда текст договора на иврите. Не вставляй личные данные, если демо публичное.",
        help="Режим вставки текста остаётся основным запасным вариантом, если OCR недоступен или ошибается.",
    )

    if not contract_text.strip():
        st.warning("Добавь текст договора, чтобы запустить проверку.")
        return

    if st.button("Анализировать текст"):
        result = analyze_contract_text(contract_text)
        _render_analysis(result)


def _render_image_tab() -> None:
    """Render the experimental server-side OCR upload workflow."""

    import streamlit as st

    st.warning(
        "OCR экспериментальный: печатный иврит может распознаваться, рукописный иврит не считается подтверждённым."
    )
    uploaded_image = st.file_uploader(
        "Загрузи фото или скан договора",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        help="Поддерживаются JPG, JPEG и PNG. Не загружай реальные частные фото в публичное демо.",
    )

    if uploaded_image is None:
        st.info("Загрузи JPG или PNG с чётким печатным ивритом либо используй вкладку вставки текста.")
        return

    st.image(uploaded_image, caption="Предпросмотр загруженного изображения", use_container_width=True)

    if "last_ocr_file" not in st.session_state or st.session_state.last_ocr_file != uploaded_image.name:
        st.session_state.last_ocr_file = uploaded_image.name
        st.session_state.ocr_text = ""
        st.session_state.ocr_result = None

    if st.button("Распознать фото"):
        with st.spinner("Идёт OCR через серверный Tesseract..."):
            uploaded_image.seek(0)
            st.session_state.ocr_result = ocr_image_to_text(uploaded_image)
            st.session_state.ocr_text = st.session_state.ocr_result["raw_text"]

    ocr_result = st.session_state.get("ocr_result")
    if ocr_result is None:
        st.info("Нажми «Распознать фото», чтобы получить редактируемый текст перед анализом.")
        return

    if not ocr_result["ocr_available"]:
        st.error(ocr_result["error"] or "OCR недоступен в этом окружении. Используй вставку текста договора.")
        return

    if ocr_result["blocks"]:
        with st.expander("Диагностика OCR-блоков", expanded=False):
            block_rows = [
                {
                    "Текст": block["text"],
                    "Уверенность": block["confidence"],
                    "Рамка": block["bbox"],
                }
                for block in ocr_result["blocks"]
            ]
            st.dataframe(block_rows, use_container_width=True, hide_index=True)

    if not st.session_state.ocr_text.strip():
        st.warning(
            "Не удалось уверенно распознать текст. Попробуй более чёткое фото или используй ручную вставку текста."
        )

    edited_ocr_text = st.text_area(
        "Распознанный текст. Проверь и исправь ошибки OCR перед анализом.",
        key="ocr_text",
        height=280,
        help="Текст можно редактировать. Рукописный иврит не считается подтверждённым и требует ручной проверки.",
    )

    if st.button("Анализировать распознанный текст"):
        if not edited_ocr_text.strip():
            st.warning("Текст OCR пустой. Исправь распознавание вручную или используй вкладку вставки текста.")
            return
        result = analyze_contract_text(edited_ocr_text)
        _render_analysis(result)


def _render_json_tab() -> None:
    """Render a JSON upload placeholder without changing raw JSON behavior."""

    import json

    import streamlit as st

    uploaded_json = st.file_uploader(
        "Загрузи OCR JSON",
        type=["json"],
        accept_multiple_files=False,
        help="Можно загрузить JSON с полем raw_text или text. Сырой JSON будет показан без изменений.",
    )
    if uploaded_json is None:
        st.info("Если у тебя уже есть результат OCR в JSON, загрузи файл здесь или используй вставку текста.")
        return

    try:
        payload = json.load(uploaded_json)
    except json.JSONDecodeError:
        st.error("Не удалось прочитать JSON. Проверь формат файла.")
        return

    st.subheader("Сырой JSON")
    st.json(payload)
    extracted_text = ""
    if isinstance(payload, dict):
        extracted_text = str(payload.get("raw_text") or payload.get("text") or "")

    json_text = st.text_area(
        "Текст из OCR JSON. Проверь и исправь его перед анализом.",
        value=extracted_text,
        height=280,
    )
    if st.button("Анализировать текст из JSON"):
        if not json_text.strip():
            st.warning("В JSON не найден текст для анализа. Вставь текст вручную.")
            return
        result = analyze_contract_text(json_text)
        _render_analysis(result)


def main() -> None:
    """Run the Streamlit application."""

    import streamlit as st

    st.set_page_config(page_title="Проверка договора аренды на иврите", page_icon="📄", layout="wide")
    st.title("📄 Проверка договора аренды на иврите")
    st.caption(
        "Публичное демо с простыми детерминированными проверками: без LLM, платных API, секретов и реальных фото договоров."
    )

    st.info(
        "Это прототип для предварительной проверки договора. Он не заменяет адвоката. OCR может ошибаться. "
        "Рукописный иврит не считается автоматически подтверждённым. Перед подписанием спорного договора "
        "проверь опасные пункты вручную или с юристом."
    )

    paste_tab, json_tab, image_tab = st.tabs(
        ["Вставить текст договора", "Загрузить OCR JSON", "Загрузить фото договора"]
    )
    with paste_tab:
        _render_paste_tab()
    with json_tab:
        _render_json_tab()
    with image_tab:
        _render_image_tab()


if __name__ == "__main__":
    main()
