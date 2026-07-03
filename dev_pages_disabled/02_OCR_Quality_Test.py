"""Manual OCR quality test page for synthetic or pasted page-separated OCR text.

This developer-only page is intentionally outside Streamlit's auto-discovered
pages/ folder so it does not appear in the normal MVP sidebar.
"""

from __future__ import annotations

import streamlit as st

from contract_checker.ocr_quality import assess_ocr_pages_quality, assess_ocr_quality


SAMPLE_OCR = """--- PAGE 1: synthetic_good_page.png ---
הסכם שכירות בלתי מוגנת
המשכיר משכיר לשוכר דירה למטרת מגורים בלבד.
דמי שכירות ישולמו בכל חודש בסך 5000 ש"ח.
השוכר ישלם ארנונה, חשמל, מים וועד הבית.
השוכר יפקיד פיקדון ויחתום על נספח וערבות לפי הצורך.
בסיום התקופה יחול פינוי הדירה וחתימה על פרוטוקול מסירה.

--- PAGE 2: synthetic_bad_page.png ---
abc xyz qwe N n 7 page noise lorem ipsum
"""


def _report_to_dict(report: object) -> dict[str, object]:
    if hasattr(report, "to_dict"):
        return report.to_dict()
    return dict(report)  # type: ignore[arg-type]


def _render_overall_status(report: object) -> None:
    data = _report_to_dict(report)
    status = data.get("status")
    score = data.get("score")
    markers = data.get("lease_marker_hits")
    if status == "good":
        st.success(f"Overall OCR quality: good. Score {score}, markers {markers}.")
    elif status == "warning":
        st.warning(f"Overall OCR quality: warning. Score {score}, markers {markers}.")
    else:
        st.error(f"Overall OCR quality: poor. Score {score}, markers {markers}.")

    with st.expander("Advanced: overall OCR quality details", expanded=False):
        st.write(data)


def _render_page_status(page_reports: list[object]) -> None:
    if not page_reports:
        st.info("Page-level OCR quality is available only when the text contains page headers like `--- PAGE 1: page_1.png ---`.")
        return

    page_dicts = [_report_to_dict(report) for report in page_reports]
    poor_pages = [page for page in page_dicts if page.get("status") == "poor"]
    warning_pages = [page for page in page_dicts if page.get("status") == "warning"]

    if poor_pages:
        page_numbers = ", ".join(str(page.get("page_number")) for page in poor_pages)
        st.error(f"Pages to reshoot: {page_numbers}.")
        for page in poor_pages:
            st.warning(str(page.get("reshoot_hint_ru") or "Пересними страницу крупнее, ровнее и ярче."))
    elif warning_pages:
        page_numbers = ", ".join(str(page.get("page_number")) for page in warning_pages)
        st.warning(f"Pages with warnings: {page_numbers}. Reshooting may improve analysis quality.")
    else:
        st.success("Page-level OCR quality: no critical problems found.")

    with st.expander("Advanced: OCR quality by page", expanded=False):
        st.write(page_dicts)


st.set_page_config(page_title="Developer OCR Quality Test", page_icon="🧪", layout="wide")
st.title("🧪 Developer-only OCR quality test")
st.caption(
    "Developer diagnostic helper for synthetic OCR text. It is not part of the normal MVP flow, does not run Gemini OCR, "
    "does not analyze legal content, and does not send text to external APIs."
)

expected_pages = st.number_input(
    "Expected pages",
    min_value=1,
    max_value=100,
    value=2,
    help="Used to detect missing page sections in page-separated OCR text.",
)

ocr_text = st.text_area(
    "Paste page-separated OCR text",
    value=SAMPLE_OCR,
    height=420,
    help="Use headers like `--- PAGE 1: page_1.png ---` to test page-level quality.",
)

if st.button("Assess OCR quality", type="primary", disabled=not bool(ocr_text.strip())):
    overall_report = assess_ocr_quality(ocr_text, expected_pages=int(expected_pages))
    page_reports = assess_ocr_pages_quality(ocr_text, expected_pages=int(expected_pages))

    _render_overall_status(overall_report)
    _render_page_status(page_reports)

    st.info(
        "Use this page to test dirty OCR, missing pages, and reshoot hints before testing real camera reshoots. "
        "It is a diagnostic page only."
    )
