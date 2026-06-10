"""Russian-first Streamlit app for text-based AI contract audit."""

from __future__ import annotations

import json
import os
from typing import Any

from contract_checker.openai_engine import DEFAULT_OPENAI_MODEL, ContractAnalysisError, analyze_contract_with_openai
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


def main() -> None:
    """Run the Streamlit application."""

    import streamlit as st

    st.set_page_config(page_title="AI-аудит договора аренды", page_icon="📄", layout="wide")
    st.title("📄 AI-аудит договора аренды на иврите")
    st.caption("Закрытый MVP: текст → обезличивание → проверка пригодности → OpenAI Structured Output → проверка цитат → отчёт на русском.")

    st.warning("Прототип не является юридической консультацией и не заменяет проверку адвоката.")
    st.info(
        "API-ключ вводится по модели BYOK только для закрытого теста. Текст договора отправляется в OpenAI "
        "только после показанного обезличивания. Не храните договор и ключ в сессии дольше необходимого."
    )

    api_key = st.text_input(
        "OpenAI API-ключ — только для закрытого теста",
        type="password",
        key="api_key_input",
        help="Ключ не должен попадать в GitHub. Приложение не выводит его в ошибки или отчёты.",
    )

    default_model = os.getenv("OPENAI_CONTRACT_MODEL", DEFAULT_OPENAI_MODEL)
    model_options = [default_model, "gpt-5.4-mini", "gpt-5.4", "gpt-5.2"]
    deduped_options = list(dict.fromkeys(model_options))
    selected_model = st.selectbox("Модель OpenAI", deduped_options, index=0)
    with st.expander("Advanced settings", expanded=False):
        manual_model = st.text_input("Manual model ID", key="manual_model_id", placeholder="например: gpt-5.4-mini")
    model = manual_model.strip() or selected_model

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
        with st.expander("Обезличенный текст, который будет отправлен в OpenAI", expanded=True):
            st.text_area("Redacted source", value=redacted_text, height=260, disabled=True, label_visibility="collapsed")
    if validation:
        _render_validation_status(validation)

    can_analyze = bool(validation and validation.usable and api_key.strip())
    if st.button("Запустить анализ", disabled=not can_analyze):
        if not redacted_text or not validation or not validation.usable:
            st.error("Сначала обезличь текст и пройди валидацию.")
        elif not api_key.strip():
            st.error("Для закрытого теста нужен OpenAI API-ключ.")
        else:
            try:
                with st.spinner("OpenAI анализирует обезличенный договор..."):
                    result = analyze_contract_with_openai(redacted_text=redacted_text, api_key=api_key, model=model)
                    validated = validate_model_evidence(result, redacted_text)
                st.session_state.analysis_result = validated.result.model_dump(mode="json")
                st.session_state.validation_warnings = validated.warnings
            except ContractAnalysisError as exc:
                st.error(str(exc))

    stored_result = st.session_state.get("analysis_result")
    if stored_result:
        result = ContractAuditResult.model_validate(stored_result)
        warnings = st.session_state.get("validation_warnings", [])
        _render_analysis(EvidenceValidationResult(result=result, warnings=warnings))

    with st.expander("Deprecated/unused OCR direction", expanded=False):
        st.write(
            "Google/Azure OCR, Tesseract и загрузка фото скрыты из основного сценария. "
            "В этом задании MVP принимает только готовый текст договора на иврите."
        )
        st.code(json.dumps({"ocr": "deprecated_unused_in_this_mvp"}, ensure_ascii=False), language="json")


if __name__ == "__main__":
    main()
