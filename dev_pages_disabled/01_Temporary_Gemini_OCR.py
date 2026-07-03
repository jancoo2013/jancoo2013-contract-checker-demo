"""Compatibility page for the moved Temporary Gemini OCR flow.

This file is intentionally outside Streamlit's auto-discovered pages/ folder so
it does not appear in the normal MVP sidebar. Keep it here as a developer
reference for the old standalone OCR page.
"""

from __future__ import annotations

import streamlit as st


st.set_page_config(page_title="Temporary Gemini OCR moved", page_icon="🔎", layout="wide")
st.title("Temporary Gemini OCR")
st.info(
    "Temporary Gemini OCR теперь встроен в основную страницу приложения. "
    "Открой главный экран и пройди поток сверху вниз: Step 1 → Step 5 → анализ."
)
st.caption(
    "Этот sidebar-page оставлен только как короткая подсказка для старых ссылок. "
    "Обычный тестовый поток больше не требует перехода в боковое меню."
)
