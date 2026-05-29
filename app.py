"""Public Streamlit demo for deterministic contract checks."""

from __future__ import annotations

from contract_checker.pipeline import analyze_contract_text
from contract_checker.report import result_to_markdown
from contract_checker.web_helpers import result_summary, sample_contract_text, status_badge


def main() -> None:
    """Run the Streamlit application."""

    import streamlit as st

    st.set_page_config(page_title="Contract Checker Demo", page_icon="📄", layout="wide")
    st.title("📄 Contract Checker Demo")
    st.caption(
        "A public-safe demo that uses deterministic text checks only. "
        "It does not use OCR, LLMs, paid APIs, secrets, or real contract photos."
    )

    st.info(
        "Paste contract text below or load the synthetic sample. "
        "This demo is not legal advice. Have a qualified professional review important contracts."
    )

    if "contract_text" not in st.session_state:
        st.session_state.contract_text = ""

    if st.button("Load synthetic sample contract"):
        st.session_state.contract_text = sample_contract_text()

    contract_text = st.text_area(
        "Contract text",
        key="contract_text",
        height=280,
        placeholder="Paste public-safe contract text here...",
    )

    if not contract_text.strip():
        st.warning("Add contract text to run the demo checks.")
        return

    result = analyze_contract_text(contract_text)
    summary = result_summary(result)

    st.subheader("Summary")
    cols = st.columns(4)
    for column, (label, value) in zip(cols, summary.items(), strict=True):
        column.metric(label, value)

    st.subheader("Findings")
    for finding in result.findings:
        with st.expander(f"{status_badge(finding.status)} — {finding.title}", expanded=True):
            st.write(finding.detail)
            st.write(f"**Recommendation:** {finding.recommendation}")

    st.subheader("Export")
    report_markdown = result_to_markdown(result)
    st.download_button(
        "Download Markdown report",
        data=report_markdown,
        file_name="contract-check-report.md",
        mime="text/markdown",
    )
    st.markdown(report_markdown)


if __name__ == "__main__":
    main()
