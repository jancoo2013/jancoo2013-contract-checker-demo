"""Russian-first Streamlit app for text-based AI contract audit."""

from __future__ import annotations

from typing import Any

from contract_checker.completeness import CompletenessAudit, audit_completeness
from contract_checker.gemini_engine import (
    DEFAULT_GEMINI_MODEL,
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiRateLimitError,
    GeminiResponseError,
    analyze_contract_with_gemini,
)
from contract_checker.output_validator import EvidenceValidationResult, validate_model_evidence
from contract_checker.redaction import RedactionReport, redact_personal_data_with_report
from contract_checker.schemas import ContractAuditResult
from contract_checker.validator import ContractTextValidationResult, validate_contract_text


def _model_to_dict(result: ContractAuditResult) -> dict[str, Any]:
    return result.model_dump(mode="json")


def _risk_profile_label(risk_profile: str) -> str:
    labels = {
        "high_risk_found": "Найдены существенные риски",
        "issues_to_clarify": "Есть вопросы для уточнения",
        "no_obvious_critical_risk_found": "Явных критических рисков не найдено",
        "text_unusable": "Текст непригоден для анализа",
    }
    return labels.get(risk_profile, "Риск-профиль требует проверки")


def _evidence_ids_label(evidence_block_ids: list[str]) -> str:
    return ", ".join(evidence_block_ids)


def _render_risk_list(title: str, risks: list[Any]) -> None:
    import streamlit as st

    st.subheader(title)
    if not risks:
        st.info("Нет подтверждённых пунктов в этом разделе.")
        return
    for risk in risks:
        with st.expander(risk.title_ru, expanded=True):
            st.markdown(f"**Уровень:** `{risk.level}`")
            if risk.page:
                st.markdown(f"**Страница:** {risk.page}")
            if risk.evidence_block_ids:
                st.markdown(f"**Источник:** `{_evidence_ids_label(risk.evidence_block_ids)}`")
            st.markdown(f"**Цитата:** {risk.source_quote_he}")
            st.markdown(risk.explanation_ru)
            if risk.requested_change_ru:
                st.markdown(f"**Что просить изменить:** {risk.requested_change_ru}")


def _render_analysis(validated: EvidenceValidationResult) -> None:
    import streamlit as st

    result = validated.result
    st.header("Итоговый риск-профиль загруженных материалов")
    st.metric("Риск-профиль", _risk_profile_label(result.risk_profile))
    st.write(result.risk_profile_summary_ru)
    st.warning(
        "Это не означает, что договор безопасен или что его можно подписывать без консультации. "
        "Сервис показывает только риск-профиль загруженных и проанализированных материалов."
    )

    if validated.warnings:
        st.warning("Есть предупреждения проверки источников.")
        with st.expander("Предупреждения проверки источников", expanded=False):
            for warning in validated.warnings:
                st.warning(warning)

    red_risks = [risk for risk in result.risks if risk.level == "red"]
    yellow_risks = [risk for risk in result.risks if risk.level == "yellow"]
    _render_risk_list("Красные риски", red_risks)
    _render_risk_list("Жёлтые риски", yellow_risks)

    st.subheader("Обычные пункты")
    normal_clauses = [clause for clause in result.clauses if clause.risk_level == "normal"]
    if normal_clauses:
        for clause in normal_clauses:
            with st.expander(f"{clause.clause_id}: {clause.category}"):
                if clause.evidence_block_ids:
                    st.markdown(f"**Источник:** `{_evidence_ids_label(clause.evidence_block_ids)}`")
                st.markdown(f"**Цитата:** {clause.source_quote_he}")
                st.markdown(clause.explanation_ru)
    else:
        st.info("Модель не вернула обычные пункты или они не прошли проверку.")

    st.subheader("Отсутствующие условия")
    if result.missing_clauses:
        for item in result.missing_clauses:
            st.markdown(f"* **{item.title_ru}** — {item.explanation_ru}")
            if item.requested_change_ru:
                st.markdown(f"  *Просить:* {item.requested_change_ru}")
    else:
        st.info("Нет отмеченных отсутствующих условий.")

    st.subheader("Неясные фрагменты")
    if result.unclear_fragments:
        for item in result.unclear_fragments:
            with st.expander(item.title_ru):
                if item.evidence_block_ids:
                    st.markdown(f"**Источник:** `{_evidence_ids_label(item.evidence_block_ids)}`")
                st.markdown(f"**Цитата:** {item.source_quote_he}")
                st.markdown(item.explanation_ru)
                if item.requested_clarification_ru:
                    st.markdown(f"**Уточнить:** {item.requested_clarification_ru}")
    else:
        st.info("Нет подтверждённых неясных фрагментов.")

    st.subheader("Вопросы агенту/арендодателю")
    if result.questions_to_agent:
        for question in result.questions_to_agent:
            st.markdown(f"* **{question.question_ru}** — {question.why_ru}")
    else:
        st.info("Нет дополнительных вопросов.")

    st.subheader("Предлагаемые изменения")
    if result.proposed_changes:
        for change in result.proposed_changes:
            st.markdown(f"* **{change.title_ru}** (`{change.priority}`): {change.proposed_text_ru}")
    else:
        st.info("Нет предложенных формулировок.")

    with st.expander("Advanced: сырой структурированный JSON", expanded=False):
        st.json(_model_to_dict(result))


def _render_validation_status(validation: ContractTextValidationResult) -> None:
    import streamlit as st

    if validation.usable:
        st.success("Текст пригоден для AI-анализа после обезличивания.")
    else:
        st.error("Текст пока непригоден для AI-анализа.")
    for problem in validation.problems:
        st.warning(problem)
    with st.expander("Advanced: технические метрики текста", expanded=False):
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


def _render_redaction_report(report: RedactionReport) -> None:
    import streamlit as st

    if report.total <= 0:
        st.info("Автофильтр не нашёл типовые персональные поля в тексте.")
        return

    labels = {
        "phones": ("телефоны", report.phones),
        "emails": ("email", report.emails),
        "ids": ("ID", report.ids),
        "bank_details": ("банковские реквизиты", report.bank_details),
        "addresses": ("адреса", report.addresses),
        "names": ("имена", report.names),
        "signatures": ("подписи", report.signatures),
        "guarantor_details": ("данные поручителя", report.guarantor_details),
    }
    categories = [label for label, count in labels.values() if count > 0]
    st.info(f"Автофильтр заменил возможные персональные данные: {report.total}.")
    with st.expander("Advanced: категории замен", expanded=False):
        st.write(", ".join(categories))


def _render_completeness_audit(audit: CompletenessAudit) -> None:
    import streamlit as st

    st.subheader("Комплектность загруженных материалов")
    if audit.status == "text_unusable":
        st.warning(audit.summary_ru)
        return
    if audit.status == "no_referenced_documents_found":
        st.info(audit.summary_ru)
        return

    st.warning(audit.summary_ru)
    severity_labels = {
        "red": "существенно проверить",
        "yellow": "проверить",
        "normal": "к сведению",
    }
    for finding in audit.findings:
        with st.expander(f"{finding.title_ru} — {severity_labels.get(finding.severity, finding.severity)}"):
            if finding.evidence_block_ids:
                st.markdown(f"**Источник:** `{_evidence_ids_label(finding.evidence_block_ids)}`")
            st.markdown(finding.explanation_ru)
            st.markdown(f"**Вопрос:** {finding.question_ru}")


def _clear_sensitive_state() -> None:
    import streamlit as st

    for key in (
        "contract_text_input",
        "api_key_input",
        "redacted_text",
        "redaction_report",
        "completeness_audit",
        "validation_result",
        "analysis_result",
        "validation_warnings",
        "manual_model_id",
        "ocr_text_input",
        "ocr_source_input",
        "ocr_txt_upload",
    ):
        st.session_state.pop(key, None)


def _clear_image_redaction_state() -> None:
    import streamlit as st

    for key in (
        "image_redaction_results",
        "image_manual_masks",
        "image_redaction_ocr_pages",
        "image_redaction_ocr_confirmed",
        "image_page_reviewed",
        "active_image_page_index",
        "image_redaction_page_select",
    ):
        st.session_state.pop(key, None)
    for key in list(st.session_state.keys()):
        if str(key).startswith("image_redaction_uploads_"):
            st.session_state.pop(key, None)
        if str(key).startswith("image_redaction_last_click_"):
            st.session_state.pop(key, None)
        if str(key).startswith("image_redaction_ignored_click_after_undo_"):
            st.session_state.pop(key, None)
        if str(key).startswith("image_redaction_page_select_"):
            st.session_state.pop(key, None)
        if str(key).endswith(":reviewed"):
            st.session_state.pop(key, None)


def _render_image_redaction_status(has_masks: bool) -> None:
    import streamlit as st

    if has_masks:
        st.success("Ручные маски применены")
    else:
        st.info("На этой странице пока нет масок. Это допустимо, если личных данных нет.")


def _render_image_redaction_test() -> None:
    import streamlit as st
    from PIL import Image
    from io import BytesIO
    try:
        from streamlit_image_coordinates import streamlit_image_coordinates
    except ImportError:
        streamlit_image_coordinates = None

    from contract_checker.image_redaction import (
        DetectedMarker,
        MANUAL_DETECTOR_NAME,
        create_row_mask_from_y,
        make_manual_detection,
        redact_detected_rows,
    )

    def clear_ocr_handoff() -> None:
        st.session_state.pop("image_redaction_ocr_pages", None)
        st.session_state.pop("image_redaction_ocr_confirmed", None)

    def image_to_png_bytes(image: Image.Image) -> bytes:
        output = BytesIO()
        image.convert("RGB").save(output, format="PNG")
        return output.getvalue()

    def build_manual_detections(page_manual_masks: list[dict], image: Image.Image) -> list[DetectedMarker]:
        manual_detections: list[DetectedMarker] = []
        for mask in page_manual_masks:
            bbox = (int(mask["x1"]), int(mask["y1"]), int(mask["x2"]), int(mask["y2"]))
            marker = str(mask.get("marker", "ручная строка"))
            if marker == "manual_row":
                manual_detections.append(
                    DetectedMarker(
                        marker="manual_row",
                        confidence=1.0,
                        bbox=bbox,
                        row_bbox=bbox,
                        detector=MANUAL_DETECTOR_NAME,
                    )
                )
            else:
                manual_detections.append(
                    make_manual_detection(
                        bbox,
                        image.width,
                        image.height,
                        marker=marker,
                    )
                )
        return manual_detections

    def move_mask_to_point(mask: dict, x: int, y: int, image_width: int, image_height: int) -> dict:
        marker = str(mask.get("marker", "manual_row"))
        x1 = int(mask["x1"])
        y1 = int(mask["y1"])
        x2 = int(mask["x2"])
        y2 = int(mask["y2"])
        if marker == "manual_row":
            row_height = max(1, y2 - y1)
            new_bbox = create_row_mask_from_y(image_width, image_height, int(y), row_height=row_height)
        else:
            width = max(1, x2 - x1)
            height = max(1, y2 - y1)
            new_x1 = max(0, min(image_width - width, int(x) - width // 2))
            new_y1 = max(0, min(image_height - height, int(y) - height // 2))
            new_bbox = (new_x1, new_y1, new_x1 + width, new_y1 + height)
        return {
            "x1": int(new_bbox[0]),
            "y1": int(new_bbox[1]),
            "x2": int(new_bbox[2]),
            "y2": int(new_bbox[3]),
            "marker": marker,
        }

    def prepare_ocr_pages(uploaded_files, manual_masks: dict) -> tuple[list[dict], list[str]]:
        prepared_pages: list[dict] = []
        errors: list[str] = []
        for page_index, uploaded_file in enumerate(uploaded_files or []):
            page_key = f"{page_index}:{uploaded_file.name}"
            try:
                image = Image.open(BytesIO(uploaded_file.getvalue()))
                image.load()
            except Exception as exc:
                errors.append(f"{uploaded_file.name}: {exc}")
                continue

            manual_detections = build_manual_detections(manual_masks.get(page_key, []), image)
            redacted_image = redact_detected_rows(image, manual_detections) if manual_detections else image
            prepared_pages.append(
                {
                    "page_index": page_index,
                    "filename": uploaded_file.name,
                    "width": image.width,
                    "height": image.height,
                    "image_bytes": image_to_png_bytes(redacted_image),
                }
            )
        return prepared_pages, errors

    def page_label(page_index: int, uploaded_files, page_keys: list[str], manual_masks: dict) -> str:
        page_key = page_keys[page_index]
        mask_count = len(manual_masks.get(page_key, []))
        return f"Страница {page_index + 1}: {uploaded_files[page_index].name} — {mask_count} масок"

    st.divider()
    st.header("Step 1 — Upload pages")
    st.caption("Закрытый тестовый режим Streamlit. Загруженные фото остаются в сессии приложения и не отправляются во внешние API.")

    upload_generation = st.session_state.setdefault("image_redaction_upload_generation", 0)
    upload_key = f"image_redaction_uploads_{upload_generation}"
    uploaded_images = st.file_uploader(
        "Загрузи страницы договора как JPG/JPEG/PNG",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=upload_key,
    )

    col_clear, _ = st.columns([1, 3])
    with col_clear:
        if st.button("Удалить загруженные изображения из сессии"):
            _clear_image_redaction_state()
            st.session_state.image_redaction_upload_generation = upload_generation + 1
            st.rerun()

    manual_masks = st.session_state.setdefault("image_manual_masks", {})
    reviewed_pages = st.session_state.setdefault("image_page_reviewed", {})

    if not uploaded_images:
        st.info("Загрузи страницы договора. После загрузки здесь появится навигация по одной активной странице.")
        return

    page_keys = [f"{page_index}:{uploaded_file.name}" for page_index, uploaded_file in enumerate(uploaded_images)]
    current_page_keys = set(page_keys)
    for stale_key in list(manual_masks.keys()):
        if stale_key not in current_page_keys:
            manual_masks.pop(stale_key, None)
    for stale_key in list(reviewed_pages.keys()):
        if stale_key not in current_page_keys:
            reviewed_pages.pop(stale_key, None)
    for page_key in page_keys:
        reviewed_widget_key = f"{page_key}:reviewed"
        if reviewed_widget_key in st.session_state:
            reviewed_pages[page_key] = bool(st.session_state[reviewed_widget_key])
    st.session_state.image_manual_masks = manual_masks
    st.session_state.image_page_reviewed = reviewed_pages

    page_count = len(uploaded_images)
    active_index = int(st.session_state.get("active_image_page_index", 0))
    active_index = max(0, min(active_index, page_count - 1))
    st.session_state.active_image_page_index = active_index

    status_rows = []
    reviewed_count = 0
    pages_with_masks = 0
    for page_index, uploaded_file in enumerate(uploaded_images):
        page_key = page_keys[page_index]
        mask_count = len(manual_masks.get(page_key, []))
        if mask_count > 0:
            pages_with_masks += 1
        reviewed = bool(reviewed_pages.get(page_key, False))
        if reviewed:
            reviewed_count += 1
        status_rows.append(
            {
                "Страница": page_index + 1,
                "Файл": uploaded_file.name,
                "Маски": mask_count,
                "Статус": "✅ проверена" if reviewed else "⚠️ не проверена",
            }
        )
    all_pages_reviewed = reviewed_count == page_count
    summary_cols = st.columns(4)
    summary_cols[0].metric("Страниц", page_count)
    summary_cols[1].metric("Проверено", reviewed_count)
    summary_cols[2].metric("С масками", pages_with_masks)
    summary_cols[3].metric("OCR", "доступен" if all_pages_reviewed else "после проверки")
    with st.expander("Advanced: статус страниц", expanded=False):
        st.dataframe(status_rows, use_container_width=True, hide_index=True)

    prev_col, select_col, next_col = st.columns([1, 4, 1])
    with prev_col:
        if st.button("← Предыдущая", disabled=active_index <= 0):
            st.session_state.active_image_page_index = active_index - 1
            st.rerun()
    with select_col:
        selected_index = st.selectbox(
            "Активная страница",
            options=list(range(page_count)),
            index=active_index,
            format_func=lambda item: page_label(item, uploaded_images, page_keys, manual_masks),
            key=f"image_redaction_page_select_{page_count}_{active_index}",
        )
        if int(selected_index) != active_index:
            st.session_state.active_image_page_index = int(selected_index)
            st.rerun()
    with next_col:
        if st.button("Следующая →", disabled=active_index >= page_count - 1):
            st.session_state.active_image_page_index = active_index + 1
            st.rerun()

    uploaded_file = uploaded_images[active_index]
    page_key = page_keys[active_index]
    st.header("Step 2 — Mask personal data")
    st.subheader(f"Рабочая область: страница {active_index + 1} из {page_count}")

    raw_bytes = uploaded_file.getvalue()
    original_image = None
    try:
        original_image = Image.open(BytesIO(raw_bytes))
        original_image.load()
        st.caption(f"Файл: `{uploaded_file.name}`")
        with st.expander("Advanced: параметры изображения", expanded=False):
            st.write({"width": original_image.width, "height": original_image.height})
    except Exception as exc:
        st.error(f"Не удалось показать оригинал: {exc}")

    if original_image is not None:
        page_manual_masks = manual_masks.setdefault(page_key, [])
        manual_detections = build_manual_detections(page_manual_masks, original_image)
        working_image = redact_detected_rows(original_image, manual_detections) if manual_detections else original_image

        reviewed_widget_key = f"{page_key}:reviewed"
        if reviewed_widget_key not in st.session_state:
            st.session_state[reviewed_widget_key] = bool(reviewed_pages.get(page_key, False))
        previous_reviewed = bool(reviewed_pages.get(page_key, False))
        st.caption("Кликни по строке с личными данными. Для перемещения выбери существующую маску и кликни новое место.")
        max_x = max(1, original_image.width)
        max_y = max(1, original_image.height)
        row_height = st.slider(
            "Высота маски строки",
            min_value=10,
            max_value=140,
            value=30,
            step=1,
            key=f"{page_key}:row-height",
        )

        click_action = "Добавить новую маску"
        selected_mask_index = 0
        if page_manual_masks:
            click_action = st.radio(
                "Действие при клике по изображению",
                ["Добавить новую маску", "Переместить выбранную маску"],
                horizontal=True,
                key=f"{page_key}:click-action",
            )
            if click_action == "Переместить выбранную маску":
                selected_mask_index = st.selectbox(
                    "Какую маску переместить",
                    options=list(range(len(page_manual_masks))),
                    format_func=lambda item: f"{item + 1}. {(page_manual_masks[item]['x1'], page_manual_masks[item]['y1'], page_manual_masks[item]['x2'], page_manual_masks[item]['y2'])}",
                    key=f"{page_key}:move-mask-index",
                )

        last_click_state_key = f"image_redaction_last_click_{page_key}"
        ignored_click_state_key = f"image_redaction_ignored_click_after_undo_{page_key}"
        if streamlit_image_coordinates is None:
            st.warning(
                "Интерактивный клик по изображению временно недоступен. "
                "Используй ручной ввод Y-координаты или прямоугольника."
            )
            caption = "Рабочее изображение: текущий предпросмотр с ручными масками" if manual_detections else "Рабочее изображение"
            st.image(working_image, caption=caption, use_container_width=True)
        else:
            caption = "Рабочее изображение: текущий предпросмотр с ручными масками" if manual_detections else "Рабочее изображение"
            st.caption(caption)
            click_value = streamlit_image_coordinates(working_image, key=f"{page_key}:click-row")
            if click_value and click_value.get("y") is not None:
                click_coordinates = (int(click_value.get("x", -1)), int(click_value["y"]))
                click_signature = (click_action, selected_mask_index, click_coordinates[0], click_coordinates[1])
                ignored_click = st.session_state.get(ignored_click_state_key)
                last_processed_click = st.session_state.get(last_click_state_key)
                if ignored_click == click_coordinates:
                    st.session_state[last_click_state_key] = click_signature
                elif last_processed_click != click_signature:
                    st.session_state.pop(ignored_click_state_key, None)
                    if click_action == "Переместить выбранную маску" and page_manual_masks:
                        page_manual_masks[int(selected_mask_index)] = move_mask_to_point(
                            page_manual_masks[int(selected_mask_index)],
                            click_coordinates[0],
                            click_coordinates[1],
                            original_image.width,
                            original_image.height,
                        )
                    else:
                        try:
                            row_bbox = create_row_mask_from_y(
                                original_image.width,
                                original_image.height,
                                click_coordinates[1],
                                row_height=int(row_height),
                            )
                        except ValueError as exc:
                            st.error(str(exc))
                            row_bbox = None
                        if row_bbox is not None:
                            page_manual_masks.append(
                                {
                                    "x1": row_bbox[0],
                                    "y1": row_bbox[1],
                                    "x2": row_bbox[2],
                                    "y2": row_bbox[3],
                                    "marker": "manual_row",
                                }
                            )
                    manual_masks[page_key] = page_manual_masks
                    st.session_state.image_manual_masks = manual_masks
                    clear_ocr_handoff()
                    st.session_state[last_click_state_key] = click_signature
                    st.rerun()

        with st.expander("Показать оригинал", expanded=False):
            st.image(original_image, caption="Оригинал", use_container_width=True)

        with st.expander("Ручной ввод Y-координаты", expanded=streamlit_image_coordinates is None):
            row_y = st.number_input(
                "Y-координата строки",
                min_value=0,
                max_value=max_y,
                value=max_y // 2,
                step=1,
                key=f"{page_key}:row-y",
            )
            if st.button("Закрыть строку по Y", key=f"{page_key}:add-row-mask"):
                try:
                    row_bbox = create_row_mask_from_y(
                        original_image.width,
                        original_image.height,
                        int(row_y),
                        row_height=int(row_height),
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    page_manual_masks.append(
                        {
                            "x1": row_bbox[0],
                            "y1": row_bbox[1],
                            "x2": row_bbox[2],
                            "y2": row_bbox[3],
                            "marker": "manual_row",
                        }
                    )
                    manual_masks[page_key] = page_manual_masks
                    st.session_state.image_manual_masks = manual_masks
                    clear_ocr_handoff()
                    st.rerun()

        with st.expander("Расширенное ручное маскирование прямоугольником", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                x1 = st.number_input("x1", min_value=0, max_value=max_x, value=0, key=f"{page_key}:x1")
            with c2:
                y1 = st.number_input("y1", min_value=0, max_value=max_y, value=0, key=f"{page_key}:y1")
            with c3:
                x2 = st.number_input("x2", min_value=0, max_value=max_x, value=max_x, key=f"{page_key}:x2")
            with c4:
                y2 = st.number_input("y2", min_value=0, max_value=max_y, value=min(max_y, 30), key=f"{page_key}:y2")
            if st.button("Добавить прямоугольную маску", key=f"{page_key}:add-rect-mask"):
                page_manual_masks.append(
                    {
                        "x1": int(x1),
                        "y1": int(y1),
                        "x2": int(x2),
                        "y2": int(y2),
                        "marker": "manual_rect",
                    }
                )
                manual_masks[page_key] = page_manual_masks
                st.session_state.image_manual_masks = manual_masks
                clear_ocr_handoff()
                st.rerun()

        undo_col, reset_col = st.columns([1, 3])
        has_page_masks = bool(page_manual_masks)
        if undo_col.button(
            "←",
            key=f"{page_key}:undo-last-mask",
            help="Откатить последний шаг добавления маски",
            disabled=not has_page_masks,
        ):
            page_manual_masks.pop()
            if page_manual_masks:
                manual_masks[page_key] = page_manual_masks
            else:
                manual_masks.pop(page_key, None)
            st.session_state.image_manual_masks = manual_masks
            clear_ocr_handoff()
            last_processed_click = st.session_state.get(last_click_state_key)
            if last_processed_click is not None:
                if isinstance(last_processed_click, tuple) and len(last_processed_click) >= 4:
                    st.session_state[ignored_click_state_key] = (last_processed_click[-2], last_processed_click[-1])
                else:
                    st.session_state[ignored_click_state_key] = last_processed_click
            st.rerun()
        if reset_col.button(
            "Отменить изменения на этой странице",
            key=f"{page_key}:reset-page-masks",
            disabled=not has_page_masks,
        ):
            manual_masks.pop(page_key, None)
            st.session_state.image_manual_masks = manual_masks
            clear_ocr_handoff()
            last_processed_click = st.session_state.get(last_click_state_key)
            if last_processed_click is not None:
                if isinstance(last_processed_click, tuple) and len(last_processed_click) >= 4:
                    st.session_state[ignored_click_state_key] = (last_processed_click[-2], last_processed_click[-1])
                else:
                    st.session_state[ignored_click_state_key] = last_processed_click
            st.rerun()

        st.subheader("Маски на активной странице")
        if page_manual_masks:
            for mask_index, mask in enumerate(list(page_manual_masks)):
                mask_label = "строка по Y" if mask.get("marker") == "manual_row" else "прямоугольник"
                cols = st.columns([5, 1])
                cols[0].write(f"{mask_index + 1}. {mask_label}")
                if cols[1].button("Удалить", key=f"{page_key}:remove:{mask_index}"):
                    page_manual_masks.pop(mask_index)
                    if page_manual_masks:
                        manual_masks[page_key] = page_manual_masks
                    else:
                        manual_masks.pop(page_key, None)
                    st.session_state.image_manual_masks = manual_masks
                    clear_ocr_handoff()
                    last_processed_click = st.session_state.get(last_click_state_key)
                    if last_processed_click is not None:
                        if isinstance(last_processed_click, tuple) and len(last_processed_click) >= 4:
                            st.session_state[ignored_click_state_key] = (last_processed_click[-2], last_processed_click[-1])
                        else:
                            st.session_state[ignored_click_state_key] = last_processed_click
                    st.rerun()
        else:
            st.info("Ручных масок на этой странице пока нет.")

        detections_for_table = [
            {
                "marker": marker.marker,
                "confidence": marker.confidence,
                "row_bbox": marker.row_bbox,
                "detector": marker.detector,
            }
            for marker in manual_detections
        ]
        with st.expander("Advanced: технические детали масок", expanded=False):
            if detections_for_table:
                st.dataframe(detections_for_table, use_container_width=True)
            else:
                st.info("Список ручных масок пуст. Персональные значения не извлекаются и не показываются.")

        _render_image_redaction_status(bool(manual_detections))

        st.header("Step 3 — Review pages")
        reviewed_value = st.checkbox("Я проверил эту страницу", key=reviewed_widget_key)
        reviewed_pages[page_key] = bool(reviewed_value)
        st.session_state.image_page_reviewed = reviewed_pages
        if previous_reviewed != bool(reviewed_value):
            clear_ocr_handoff()

    st.header("Step 4 — Prepare for OCR")
    reviewed_pages[page_key] = bool(st.session_state.get(f"{page_key}:reviewed", reviewed_pages.get(page_key, False)))
    st.session_state.image_page_reviewed = reviewed_pages
    all_pages_reviewed = all(bool(reviewed_pages.get(key, False)) for key in page_keys)
    if not all_pages_reviewed:
        st.warning("Перед переходом к распознаванию текста нужно отметить каждую страницу как проверенную.")

    confirmed = st.checkbox(
        "Я проверил, что личные данные закрыты на всех страницах",
        key="image_redaction_ocr_confirmed",
        disabled=not all_pages_reviewed,
    )
    if st.button(
        "Продолжить к распознаванию текста",
        type="primary",
        disabled=not all_pages_reviewed or not confirmed,
    ):
        prepared_pages, errors = prepare_ocr_pages(uploaded_images, manual_masks)
        if errors:
            st.error("Не удалось подготовить некоторые страницы для распознавания текста.")
            for error in errors:
                st.warning(error)
        else:
            st.session_state.image_redaction_ocr_pages = prepared_pages
            st.success("Обезличенные страницы подготовлены для распознавания текста.")
            st.info("Открой страницу Temporary Gemini OCR. Временный OCR использует только эти подготовленные замаскированные страницы.")


def _render_manual_ocr_test_mode() -> None:
    import streamlit as st

    prepared_pages = st.session_state.get("image_redaction_ocr_pages") or []
    if not prepared_pages:
        return

    st.divider()
    with st.expander("Advanced / Legacy test mode: ручная вставка OCR-текста", expanded=False):
        st.caption(
            "Legacy helper только для закрытого теста. Используй текст, полученный из уже подготовленных/замаскированных страниц, а не из raw-договора."
        )
        st.write(
            {
                "подготовлено страниц": len(prepared_pages),
                "режим OCR": "legacy_manual_ocr_paste",
                "автоматический OCR": "не подключён",
            }
        )

        ocr_source = st.selectbox(
            "Источник тестового текста",
            [
                "Текст из подготовленных замаскированных страниц",
                "Тестовый синтетический текст",
                "Загруженный .txt из подготовленных страниц",
            ],
            key="ocr_source_input",
        )
        uploaded_txt = st.file_uploader(
            "Или загрузи .txt с тестовым OCR-текстом",
            type=["txt"],
            key="ocr_txt_upload",
        )
        pasted_text = st.text_area(
            "Вставь OCR-текст из подготовленных страниц",
            key="ocr_text_input",
            height=260,
            placeholder="Только текст из уже замаскированных подготовленных страниц.",
        )

        uploaded_text = ""
        if uploaded_txt is not None:
            uploaded_text = uploaded_txt.getvalue().decode("utf-8", errors="replace")
            st.info("Будет использован текст из загруженного .txt.")

        ocr_text = uploaded_text.strip() or pasted_text.strip()
        if ocr_text:
            hebrew_chars = sum(1 for char in ocr_text if "\u0590" <= char <= "\u05ff")
            with st.expander("Advanced: метрики вставленного текста", expanded=False):
                st.write(
                    {
                        "символов всего": len(ocr_text),
                        "символов иврита": hebrew_chars,
                        "примерная доля иврита": round(hebrew_chars / max(1, len(ocr_text)), 3),
                    }
                )

        if st.button("Подготовить OCR-текст к анализу", type="primary", disabled=not bool(ocr_text)):
            assembled_text = (
                f"--- OCR SOURCE: {ocr_source} ---\n"
                f"--- OCR MODE: legacy_manual_ocr_paste ---\n"
                f"--- IMAGE PAGES PREPARED: {len(prepared_pages)} ---\n\n"
                f"{ocr_text}"
            )
            redaction_result = redact_personal_data_with_report(assembled_text)
            redacted_text = redaction_result.redacted_text
            validation = validate_contract_text(redacted_text)
            completeness_audit = audit_completeness(redacted_text, text_usable=validation.usable)
            st.session_state.redacted_text = redacted_text
            st.session_state.redaction_report = redaction_result.report
            st.session_state.completeness_audit = completeness_audit
            st.session_state.validation_result = validation
            st.session_state.pop("analysis_result", None)
            st.session_state.pop("validation_warnings", None)
            st.success("OCR-текст подготовлен. Ниже появится обезличенный текст, валидация и проверка комплектности.")
            st.rerun()


def main() -> None:
    """Run the Streamlit application."""

    import streamlit as st

    st.set_page_config(page_title="AI-аудит договора аренды", page_icon="📄", layout="wide")
    st.title("📄 AI-аудит договора аренды на иврите")
    st.caption("Закрытый MVP: текст → обезличивание → проверка пригодности → Gemini Structured Output → проверка источников → отчёт на русском.")

    st.warning("Прототип не является юридической консультацией и не заменяет проверку адвоката.")

    _render_image_redaction_test()
    _render_manual_ocr_test_mode()

    st.divider()
    st.header("Step 5 — Analyze contract text")
    st.caption("В Gemini отправляется только показанный обезличенный текст. Streamlit остаётся временным закрытым test stand.")

    api_key = st.text_input(
        "Gemini API-ключ — только для закрытого теста",
        type="password",
        key="api_key_input",
        help="Ключ не должен попадать в GitHub. Приложение не выводит его в ошибки или отчёты.",
    )

    with st.expander("Advanced settings", expanded=False):
        manual_model = st.text_input(
            "Manual Gemini model ID",
            key="manual_model_id",
            value=DEFAULT_GEMINI_MODEL,
            placeholder="например: gemini-3.5-flash",
        )
    model = manual_model.strip() or DEFAULT_GEMINI_MODEL

    contract_text = st.text_area(
        "Вставь полный текст договора на иврите",
        key="contract_text_input",
        height=360,
        placeholder="Вставь сюда полный текст договора или используй Temporary Gemini OCR после маскировки страниц.",
    )

    col1, col2 = st.columns(2)
    with col1:
        redact_clicked = st.button("Обезличить и проверить", type="primary")
    with col2:
        if st.button("Очистить договор, OCR-текст и ключ"):
            _clear_sensitive_state()
            st.rerun()

    if redact_clicked:
        if not contract_text.strip():
            st.error("Вставь текст договора перед проверкой.")
        else:
            redaction_result = redact_personal_data_with_report(contract_text)
            redacted_text = redaction_result.redacted_text
            validation = validate_contract_text(redacted_text)
            completeness_audit = audit_completeness(redacted_text, text_usable=validation.usable)
            st.session_state.redacted_text = redacted_text
            st.session_state.redaction_report = redaction_result.report
            st.session_state.completeness_audit = completeness_audit
            st.session_state.validation_result = validation
            st.session_state.pop("analysis_result", None)
            st.session_state.pop("validation_warnings", None)

    redacted_text = st.session_state.get("redacted_text", "")
    redaction_report = st.session_state.get("redaction_report")
    completeness_audit = st.session_state.get("completeness_audit")
    validation = st.session_state.get("validation_result")

    if redacted_text:
        if redaction_report:
            _render_redaction_report(redaction_report)
        with st.expander("Обезличенный текст, который будет отправлен в Gemini", expanded=False):
            st.text_area("Redacted source", value=redacted_text, height=260, disabled=True, label_visibility="collapsed")
    if validation:
        _render_validation_status(validation)
    if completeness_audit:
        st.header("Step 6 — Check completeness")
        _render_completeness_audit(completeness_audit)

    can_analyze = bool(validation and validation.usable and api_key.strip())
    st.header("Step 7 — Run analysis")
    if st.button("Запустить анализ", disabled=not can_analyze):
        if not redacted_text or not validation or not validation.usable:
            st.error("Сначала обезличь текст и пройди валидацию.")
        elif not api_key.strip():
            st.error("Для закрытого теста нужен Gemini API-ключ.")
        else:
            try:
                with st.spinner("Gemini анализирует обезличенный договор..."):
                    result = analyze_contract_with_gemini(redacted_text=redacted_text, api_key=api_key, model=model)
                    validated = validate_model_evidence(result, redacted_text)
                st.session_state.analysis_result = validated.result.model_dump(mode="json")
                st.session_state.validation_warnings = validated.warnings
            except (GeminiAuthenticationError, GeminiConfigurationError):
                st.error("Не удалось авторизоваться в Gemini API. Проверь API-ключ.")
            except GeminiRateLimitError:
                st.error("Достигнут лимит запросов Gemini API.")
            except GeminiResponseError as exc:
                error_text = str(exc).lower()
                if "safety" in error_text or "refusal" in error_text:
                    st.error("Gemini отказался обработать запрос. Анализ не завершён.")
                elif "network" in error_text or "timeout" in error_text or "connection" in error_text:
                    st.error("Не удалось связаться с Gemini API. Попробуй позже.")
                else:
                    st.error("Gemini вернул ответ, который не соответствует ожидаемой структуре. Анализ не завершён.")

    stored_result = st.session_state.get("analysis_result")
    if stored_result:
        st.header("Step 8 — View report")
        result = ContractAuditResult.model_validate(stored_result)
        warnings = st.session_state.get("validation_warnings", [])
        _render_analysis(EvidenceValidationResult(result=result, warnings=warnings))


if __name__ == "__main__":
    main()
