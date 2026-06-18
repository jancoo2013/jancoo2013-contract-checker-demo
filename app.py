"""Russian-first Streamlit app for text-based AI contract audit."""

from __future__ import annotations

from typing import Any

from contract_checker.gemini_engine import (
    DEFAULT_GEMINI_MODEL,
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiRateLimitError,
    GeminiResponseError,
    analyze_contract_with_gemini,
)
from contract_checker.output_validator import EvidenceValidationResult, validate_model_evidence
from contract_checker.redaction import redact_personal_data
from contract_checker.schemas import ContractAuditResult
from contract_checker.validator import ContractTextValidationResult, validate_contract_text


def _model_to_dict(result: ContractAuditResult) -> dict[str, Any]:
    return result.model_dump(mode="json")


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
            st.markdown(f"**Цитата:** {risk.source_quote_he}")
            st.markdown(risk.explanation_ru)
            if risk.requested_change_ru:
                st.markdown(f"**Что просить изменить:** {risk.requested_change_ru}")


def _render_analysis(validated: EvidenceValidationResult) -> None:
    import streamlit as st

    result = validated.result
    st.header("Итог анализа")
    st.metric("Вердикт", result.verdict)
    st.write(result.verdict_reason_ru)

    if validated.warnings:
        with st.expander("Предупреждения проверки цитат", expanded=True):
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

    st.subheader("Статус валидации текста")
    if validation.usable:
        st.success("Текст пригоден для AI-анализа после обезличивания.")
    else:
        st.error("Текст пока непригоден для AI-анализа.")
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
    for problem in validation.problems:
        st.warning(problem)


def _clear_sensitive_state() -> None:
    import streamlit as st

    for key in (
        "contract_text_input",
        "api_key_input",
        "redacted_text",
        "validation_result",
        "analysis_result",
        "validation_warnings",
        "manual_model_id",
    ):
        st.session_state.pop(key, None)


def _clear_image_redaction_state() -> None:
    import streamlit as st

    for key in (
        "image_redaction_results",
        "image_manual_masks",
    ):
        st.session_state.pop(key, None)
    for key in list(st.session_state.keys()):
        if str(key).startswith("image_redaction_uploads_"):
            st.session_state.pop(key, None)
        if str(key).startswith("image_redaction_last_click_"):
            st.session_state.pop(key, None)
        if str(key).startswith("image_redaction_ignored_click_after_undo_"):
            st.session_state.pop(key, None)


def _render_image_redaction_status(
    has_masks: bool,
    has_auto_markers: bool,
    safe_to_export: bool,
    has_manual_masks: bool = False,
) -> None:
    import streamlit as st

    if has_masks:
        st.success("Строки закрыты")
    elif not has_auto_markers:
        st.warning("Маркеры не найдены")
    if not safe_to_export:
        st.error("Результат небезопасен для отправки")
        if has_manual_masks and not has_auto_markers:
            st.info(
                "Строки замаскированы вручную. Для теста геометрии — OK. "
                "Для автоматической отправки во внешний OCR — пока небезопасно."
            )
        else:
            st.info("Страница пока не считается безопасно обезличенной. Она не будет отправлена во внешние сервисы.")


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
        process_page_for_redaction,
        redact_detected_rows,
    )

    st.divider()
    st.header("ТЕСТ: маскирование личных данных на фото")
    st.warning(
        "Закрытый технический тест. Загружай только собственные тестовые документы. "
        "Фото пока поступают на сервер Streamlit и не отправляются во внешние API."
    )
    st.caption(
        "Автоматическое распознавание Hebrew-маркеров пока экспериментальное: без OCR-модели, "
        "Tesseract, Google Vision или Gemini для изображений. Ручные координаты нужны только для проверки маскирования строк."
    )

    upload_generation = st.session_state.setdefault("image_redaction_upload_generation", 0)
    upload_key = f"image_redaction_uploads_{upload_generation}"
    uploaded_images = st.file_uploader(
        "Загрузи страницы договора как JPG/JPEG/PNG",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=upload_key,
    )

    st.info(
        "Автоматический поиск личных данных пока не включён. "
        "В этом тесте строки закрываются кликом по изображению."
    )

    col_find, col_clear = st.columns(2)
    with col_find:
        find_clicked = st.button(
            "Подготовить страницы к маскированию",
            disabled=not uploaded_images,
        )
    with col_clear:
        if st.button("Удалить загруженные изображения из сессии"):
            _clear_image_redaction_state()
            st.session_state.image_redaction_upload_generation = upload_generation + 1
            st.rerun()

    if find_clicked:
        results = {}
        for index, uploaded_file in enumerate(uploaded_images):
            page_key = f"{index}:{uploaded_file.name}"
            results[page_key] = process_page_for_redaction(uploaded_file)
        st.session_state.image_redaction_results = results
        st.session_state.setdefault("image_manual_masks", {})

    results = st.session_state.get("image_redaction_results", {})
    manual_masks = st.session_state.setdefault("image_manual_masks", {})

    for index, uploaded_file in enumerate(uploaded_images or []):
        page_key = f"{index}:{uploaded_file.name}"
        result = results.get(page_key)
        with st.expander(f"Страница {index + 1}: {uploaded_file.name}", expanded=True):
            raw_bytes = uploaded_file.getvalue()
            original_image = None
            try:
                original_image = Image.open(BytesIO(raw_bytes))
                original_image.load()
                st.write(f"Размер изображения: {original_image.width} × {original_image.height} px")
            except Exception as exc:
                st.error(f"Не удалось показать оригинал: {exc}")

            if original_image is not None:
                st.info("Кликни по строке с личными данными — приложение закроет всю строку.")
                automatic_markers = result.markers if result and result.success else []
                page_manual_masks = manual_masks.setdefault(page_key, [])
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
                                original_image.width,
                                original_image.height,
                                marker=marker,
                            )
                        )
                combined = automatic_markers + manual_detections
                working_image = redact_detected_rows(original_image, combined) if combined else original_image

                st.subheader("Быстрое маскирование строки")
                st.info(
                    "Для теста не нужно точно выделять имя или номер. "
                    "Достаточно указать строку: приложение закроет её целиком."
                )
                max_x = max(1, original_image.width)
                max_y = max(1, original_image.height)
                row_height = st.slider(
                    "Высота маски строки",
                    min_value=20,
                    max_value=140,
                    value=48,
                    step=1,
                    key=f"{page_key}:row-height",
                )

                last_click_state_key = f"image_redaction_last_click_{page_key}"
                ignored_click_state_key = f"image_redaction_ignored_click_after_undo_{page_key}"
                if streamlit_image_coordinates is None:
                    st.warning(
                        "Интерактивный клик по изображению временно недоступен. "
                        "Используй ручной ввод Y-координаты."
                    )
                    caption = "Рабочее изображение: текущий предпросмотр с масками" if combined else "Рабочее изображение"
                    st.image(working_image, caption=caption, use_container_width=True)
                else:
                    caption = "Рабочее изображение: текущий предпросмотр с масками" if combined else "Рабочее изображение"
                    st.caption(caption)
                    click_value = streamlit_image_coordinates(working_image, key=f"{page_key}:click-row")
                    if click_value and click_value.get("y") is not None:
                        click_coordinates = (int(click_value.get("x", -1)), int(click_value["y"]))
                        ignored_click = st.session_state.get(ignored_click_state_key)
                        last_processed_click = st.session_state.get(last_click_state_key)
                        if ignored_click == click_coordinates:
                            st.session_state[last_click_state_key] = click_coordinates
                        elif last_processed_click != click_coordinates:
                            st.session_state.pop(ignored_click_state_key, None)
                            try:
                                row_bbox = create_row_mask_from_y(
                                    original_image.width,
                                    original_image.height,
                                    click_coordinates[1],
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
                                st.session_state[last_click_state_key] = click_coordinates
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
                        y2 = st.number_input("y2", min_value=0, max_value=max_y, value=min(max_y, 60), key=f"{page_key}:y2")
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
                        st.rerun()

                undo_col, reset_col = st.columns([1, 3])
                has_page_masks = bool(page_manual_masks)
                if undo_col.button(
                    "←",
                    key=f"{page_key}:undo-last-mask",
                    help="Откатить последний шаг",
                    disabled=not has_page_masks,
                ):
                    page_manual_masks.pop()
                    if page_manual_masks:
                        manual_masks[page_key] = page_manual_masks
                    else:
                        manual_masks.pop(page_key, None)
                    st.session_state.image_manual_masks = manual_masks
                    last_processed_click = st.session_state.get(last_click_state_key)
                    if last_processed_click is not None:
                        st.session_state[ignored_click_state_key] = last_processed_click
                    st.rerun()
                if reset_col.button(
                    "Отменить изменения",
                    key=f"{page_key}:reset-page-masks",
                    disabled=not has_page_masks,
                ):
                    manual_masks.pop(page_key, None)
                    st.session_state.image_manual_masks = manual_masks
                    last_processed_click = st.session_state.get(last_click_state_key)
                    if last_processed_click is not None:
                        st.session_state[ignored_click_state_key] = last_processed_click
                    st.rerun()

                st.subheader("Текущие маски")
                if page_manual_masks:
                    for mask_index, mask in enumerate(list(page_manual_masks)):
                        mask_label = "строка по Y" if mask.get("marker") == "manual_row" else "прямоугольник"
                        cols = st.columns([5, 1])
                        cols[0].write(
                            f"{mask_index + 1}. {mask_label}: "
                            f"{(mask['x1'], mask['y1'], mask['x2'], mask['y2'])}"
                        )
                        if cols[1].button("Удалить", key=f"{page_key}:remove:{mask_index}"):
                            page_manual_masks.pop(mask_index)
                            if page_manual_masks:
                                manual_masks[page_key] = page_manual_masks
                            else:
                                manual_masks.pop(page_key, None)
                            st.session_state.image_manual_masks = manual_masks
                            last_processed_click = st.session_state.get(last_click_state_key)
                            if last_processed_click is not None:
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
                    for marker in combined
                ]
                if detections_for_table:
                    st.dataframe(detections_for_table, use_container_width=True)
                else:
                    st.info("Список масок пуст. Персональные значения не извлекаются и не показываются.")

                if result and not result.success:
                    st.error(result.error or "Неизвестная ошибка обработки изображения.")

                safe_to_export = bool(result and result.safe_to_export)
                _render_image_redaction_status(
                    bool(combined),
                    bool(automatic_markers),
                    safe_to_export,
                    has_manual_masks=bool(manual_detections),
                )


def main() -> None:
    """Run the Streamlit application."""

    import streamlit as st

    st.set_page_config(page_title="AI-аудит договора аренды", page_icon="📄", layout="wide")
    st.title("📄 AI-аудит договора аренды на иврите")
    st.caption("Закрытый MVP: текст → обезличивание → проверка пригодности → Gemini Structured Output → проверка цитат → отчёт на русском.")

    st.warning("Прототип не является юридической консультацией и не заменяет проверку адвоката.")
    st.info(
        "API-ключ Gemini вводится по модели BYOK только для закрытого теста. В Gemini отправляется "
        "только показанный обезличенный текст. Не храните договор и ключ в сессии дольше необходимого."
    )

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
        placeholder="Вставь сюда полный текст договора. Фото/OCR в этом MVP не используются.",
    )

    col1, col2 = st.columns(2)
    with col1:
        redact_clicked = st.button("Обезличить и проверить", type="primary")
    with col2:
        if st.button("Очистить договор и ключ"):
            _clear_sensitive_state()
            st.rerun()

    if redact_clicked:
        if not contract_text.strip():
            st.error("Вставь текст договора перед проверкой.")
        else:
            redacted_text = redact_personal_data(contract_text)
            validation = validate_contract_text(redacted_text)
            st.session_state.redacted_text = redacted_text
            st.session_state.validation_result = validation
            st.session_state.pop("analysis_result", None)
            st.session_state.pop("validation_warnings", None)

    redacted_text = st.session_state.get("redacted_text", "")
    validation = st.session_state.get("validation_result")

    if redacted_text:
        with st.expander("Обезличенный текст, который будет отправлен в Gemini", expanded=True):
            st.text_area("Redacted source", value=redacted_text, height=260, disabled=True, label_visibility="collapsed")
    if validation:
        _render_validation_status(validation)

    can_analyze = bool(validation and validation.usable and api_key.strip())
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
        result = ContractAuditResult.model_validate(stored_result)
        warnings = st.session_state.get("validation_warnings", [])
        _render_analysis(EvidenceValidationResult(result=result, warnings=warnings))

    _render_image_redaction_test()


if __name__ == "__main__":
    main()
