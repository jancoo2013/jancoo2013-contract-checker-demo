"""Public Streamlit demo for deterministic contract checks."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from contract_checker.ocr_image import is_ocr_quality_sufficient, ocr_images_to_text, ocr_json_to_text
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

_RETAKE_PHOTO_INSTRUCTION = """Не удалось достаточно надёжно распознать текст на этой странице.

Попробуй переснять страницу:
— найди хорошо освещённое место или включи вспышку;
— положи лист на ровную тёмную поверхность;
— держи камеру строго перпендикулярно листу;
— страница должна полностью помещаться в кадр;
— текст должен быть резким, без размытия;
— избегай теней, бликов и складок;
— не фотографируй под углом;
— если текст мелкий, поднеси камеру ближе, но не обрезай края."""

_LOW_OCR_REPORT_WARNING = "Внимание: отчёт основан на OCR низкого качества. Проверь все важные пункты вручную."


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


def _uploaded_files_signature(uploaded_files: list[Any]) -> tuple[tuple[str, int], ...]:
    """Return a stable signature for the current multi-file upload."""

    return tuple((str(file.name), int(getattr(file, "size", 0) or 0)) for file in uploaded_files)


def _page_is_usable(page: dict[str, Any]) -> bool:
    """Return page-level deterministic OCR usability from stored metrics."""

    quality = page.get("quality") or {}
    metrics = quality.get("metrics") or {}
    return bool(page.get("ocr_available")) and bool(metrics.get("ocr_text_usable"))


def _ocr_page_status(page: dict[str, Any]) -> str:
    """Return Russian status for one OCR page."""

    if page.get("error") or not page.get("ocr_available"):
        return "ошибка OCR"
    if _page_is_usable(page):
        return "достаточно для чернового анализа"
    return "недостаточно качества"


def _ocr_status_rows(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build Russian page-level OCR diagnostics for Streamlit tables."""

    rows: list[dict[str, Any]] = []
    for page in pages:
        quality = page.get("quality") or {}
        metrics = quality.get("metrics") or {}
        raw_text = str(page.get("raw_text") or "")
        status = _ocr_page_status(page)
        if status == "достаточно для чернового анализа":
            comment = "Текст можно проверить вручную и использовать для чернового анализа."
        elif status == "ошибка OCR":
            comment = "OCR не вернул надёжный текст для этой страницы."
        else:
            comment = "Текст ненадёжен: пересними страницу или исправь OCR вручную."
        rows.append(
            {
                "Страница": page.get("page_index"),
                "Файл": page.get("filename"),
                "Статус": status,
                "Символов иврита": metrics.get("hebrew_char_count", 0),
                "Найдено ключевых слов": metrics.get("known_anchor_hits", 0),
                "Комментарий": comment,
            }
        )
    return rows


def _render_image_tab() -> None:
    """Render the experimental server-side multi-page OCR upload workflow."""

    import streamlit as st

    st.warning(
        "OCR экспериментальный: печатный иврит может распознаваться, рукописный иврит не считается подтверждённым."
    )
    st.warning(
        "Если загрузить только одну страницу, система может не найти пункты, которые находятся на других страницах. "
        "Для нормальной проверки загрузи весь договор."
    )
    st.info(
        "Для лучшего распознавания загружай все страницы договора. "
        "Рукописный иврит всё равно требует ручной проверки.\n\n"
        + _RETAKE_PHOTO_INSTRUCTION.replace(
            "Не удалось достаточно надёжно распознать текст на этой странице.\n\n", ""
        )
    )
    uploaded_images = st.file_uploader(
        "Загрузи все страницы договора сразу",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help=(
            "Лучше загружать страницы по порядку: 1, 2, 3... Поддерживаются JPG, JPEG и PNG. "
            "Не загружай реальные частные фото в публичное демо."
        ),
    )
    st.caption("Лучше загружать страницы по порядку: 1, 2, 3...")

    if not uploaded_images:
        st.info("Загрузи JPG или PNG с чётким печатным ивритом либо используй вкладку вставки текста.")
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

    upload_signature = _uploaded_files_signature(uploaded_images)
    if st.session_state.get("last_ocr_files") != upload_signature:
        st.session_state.last_ocr_files = upload_signature
        st.session_state.ocr_text = ""
        st.session_state.ocr_result = None

    if st.button("Распознать все страницы"):
        with st.spinner("Идёт OCR всех страниц через серверный Tesseract..."):
            st.session_state.ocr_result = ocr_images_to_text(uploaded_images)
            st.session_state.ocr_text = st.session_state.ocr_result["raw_text"]

    ocr_result = st.session_state.get("ocr_result")
    if ocr_result is None:
        st.info("Нажми «Распознать все страницы», чтобы получить редактируемый текст всего договора перед анализом.")
        return

    pages = ocr_result.get("pages", [])
    combined_quality = ocr_result.get("quality") or {}
    combined_level = str(combined_quality.get("quality_level") or "failed")
    st.subheader("Статус OCR по страницам")
    st.dataframe(_ocr_status_rows(pages), use_container_width=True, hide_index=True)
    st.caption(
        f"Общее качество OCR: {combined_level}; score: {combined_quality.get('score', 0.0)}"
    )

    unusable_pages = [page for page in pages if not _page_is_usable(page)]
    all_pages_failed = bool(pages) and all(
        bool(page.get("error")) or not str(page.get("raw_text") or "").strip() for page in pages
    )

    if unusable_pages:
        for page in unusable_pages:
            st.warning(f"Страница {page.get('page_index')} ({page.get('filename')}):\n\n{_RETAKE_PHOTO_INSTRUCTION}")
        if any(str(page.get("raw_text") or "").strip() for page in unusable_pages):
            st.info("Можно вручную исправить распознанный текст и затем запустить анализ.")

    if ocr_result.get("errors"):
        for error in ocr_result["errors"]:
            st.error(error)

    if not ocr_result["ocr_available"]:
        st.error("Не удалось распознать ни одну страницу. Используй вставку текста договора или проверь OCR окружение.")
        st.warning(_RETAKE_PHOTO_INSTRUCTION)
        return

    all_blocks = [
        {
            "Страница": page["page_index"],
            "Текст": block["text"],
            "Уверенность": block["confidence"],
            "Рамка": block["bbox"],
        }
        for page in pages
        for block in page.get("blocks", [])
    ]
    if all_blocks:
        with st.expander("Диагностика OCR-блоков", expanded=False):
            st.dataframe(all_blocks, use_container_width=True, hide_index=True)

    quality_sufficient = is_ocr_quality_sufficient(combined_quality) and not unusable_pages
    if not quality_sufficient:
        st.warning(
            "Качество OCR недостаточно для автоматического анализа без ручной проверки. "
            "Распознанный текст ниже может быть ненадёжным."
        )

    if not st.session_state.ocr_text.strip():
        st.warning(
            "Не удалось уверенно распознать текст. Попробуй более чёткие фото или используй ручную вставку текста."
        )

    edited_ocr_text = st.text_area(
        "Распознанный текст всего договора. Проверь и исправь ошибки OCR перед анализом.",
        key="ocr_text",
        height=360,
        help="Текст можно редактировать. Рукописный иврит не считается подтверждённым и требует ручной проверки.",
    )

    user_confirmed_low_quality = True
    if not quality_sufficient and not all_pages_failed:
        user_confirmed_low_quality = st.checkbox(
            "Я проверил распознанный текст вручную и понимаю, что OCR мог ошибиться."
        )
    elif all_pages_failed:
        user_confirmed_low_quality = False
        st.error(
            "Все страницы не удалось распознать достаточно надёжно. "
            "Автоматический анализ не запускается; пересними страницы или используй ручную вставку проверенного текста."
        )

    analyze_disabled = (not quality_sufficient and not user_confirmed_low_quality) or all_pages_failed
    if not all_pages_failed and st.button("Анализировать весь договор", disabled=analyze_disabled):
        if not edited_ocr_text.strip():
            st.warning("Текст OCR пустой. Исправь распознавание вручную или используй вкладку вставки текста.")
            return
        result = analyze_contract_text(edited_ocr_text)
        notice = None
        if not quality_sufficient:
            notice = _LOW_OCR_REPORT_WARNING
        _render_analysis(result, report_notice=notice)


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
