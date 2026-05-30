"""Public Streamlit demo for deterministic contract checks."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from contract_checker.cloud_ocr import (
    get_provider_status,
    ocr_with_azure_vision,
    ocr_with_google_vision,
)
from contract_checker.ocr_image import ocr_json_to_text
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


def _render_analysis(result: Any, report_notice: str | None = None) -> None:
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
    if report_notice:
        report_markdown = f"{report_notice}\n\n{report_markdown}"
        st.warning(report_notice)
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
    """Render the photo upload workflow without running server-side OCR."""

    import streamlit as st

    st.warning(
        "Серверный Tesseract OCR временно отключён: на реальных договорах он слишком медленный "
        "и нестабильный в Streamlit Cloud. Следующий этап — подключение облачного OCR."
    )
    st.info(
        "Фото-вкладка сейчас показывает только предпросмотр загруженных страниц и не запускает долгие OCR-задачи. "
        "Рукописный иврит не считается автоматически подтверждённым."
    )

    st.subheader("OCR-движок")
    provider_options = {
        "OCR пока не подключён": "not_configured",
        "Google Cloud Vision OCR — подготовлено, но не настроено": "google_vision",
        "Azure AI Vision Read OCR — подготовлено, но не настроено": "azure_vision",
    }
    provider_label = st.selectbox(
        "Выбери OCR-провайдера",
        list(provider_options),
        help="Публичное демо не показывает поля API-ключей. Будущая интеграция должна читать секреты из защищённой конфигурации.",
    )
    provider = provider_options[provider_label]
    provider_status = get_provider_status(provider)
    st.info(provider_status["message"])
    st.caption(
        "Для включения этого режима нужно добавить ключи в Streamlit secrets. "
        "Ключи нельзя хранить в GitHub."
    )

    st.markdown(
        "**Пока Cloud OCR не подключён, можно загрузить OCR JSON от внешнего распознавателя.** "
        "Также можно вставить проверенный текст вручную во вкладке **\"Вставить текст договора\"**."
    )

    st.subheader("Временный ручной сценарий")
    st.markdown(
        "1. распознай текст внешним OCR;\n"
        "2. загрузи OCR JSON во вкладке **\"Загрузить OCR JSON\"** или вставь текст во вкладку **\"Вставить текст договора\"**;\n"
        "3. проверь отчёт."
    )

    st.caption("Совет для будущего OCR: загружай страницы по порядку: 1, 2, 3...")
    uploaded_images = st.file_uploader(
        "Загрузи фото страниц для предпросмотра",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help=(
            "Сейчас фото не распознаются на сервере. Не загружай реальные частные фото в публичное демо; "
            "используй этот блок только для проверки будущего сценария загрузки."
        ),
    )

    if not uploaded_images:
        st.info(
            "Загрузи JPG или PNG для предпросмотра, используй вкладку OCR JSON для готового результата "
            "или вставь проверенный текст вручную."
        )
        return

    st.subheader("Порядок загруженных страниц")
    st.dataframe(
        [
            {"Страница": index, "Файл": uploaded_image.name}
            for index, uploaded_image in enumerate(uploaded_images, start=1)
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Предпросмотр загруженных страниц")
    for index, uploaded_image in enumerate(uploaded_images, start=1):
        with st.expander(f"Страница {index}: {uploaded_image.name}", expanded=False):
            st.image(uploaded_image, caption=f"Страница {index}: {uploaded_image.name}", use_container_width=True)

    if st.button("Распознать через Cloud OCR"):
        if provider == "google_vision":
            ocr_result = ocr_with_google_vision(uploaded_images)
        elif provider == "azure_vision":
            ocr_result = ocr_with_azure_vision(uploaded_images)
        else:
            ocr_result = None

        if ocr_result is None:
            st.warning(
                "Cloud OCR пока не подключён. Выбери подготовленный провайдер "
                "или загрузи OCR JSON от внешнего распознавателя."
            )
        else:
            st.error(ocr_result.error)
            st.json(ocr_result.to_dict())

    st.warning(
        "Автоматический анализ фото отключён. Чтобы продолжить проверку, распознай текст внешним OCR "
        "и вставь его во вкладку \"Вставить текст договора\" или загрузи готовый OCR JSON."
    )


def _render_json_tab() -> None:
    """Render a JSON upload placeholder without changing raw JSON behavior."""

    import json

    import streamlit as st

    uploaded_json = st.file_uploader(
        "Загрузи OCR JSON",
        type=["json"],
        accept_multiple_files=False,
        help="Можно загрузить JSON с полем raw_text, text или pages. Сырой JSON будет показан без изменений.",
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
    extracted_text = ocr_json_to_text(payload)

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
