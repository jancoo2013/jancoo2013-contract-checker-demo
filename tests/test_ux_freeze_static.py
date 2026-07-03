"""Static checks that keep the MVP UX freeze from drifting."""

from __future__ import annotations

from pathlib import Path
import unittest


UX_FREEZE_PATH = Path("docs/mvp_ux_freeze.md")
LEGACY_SIDEBAR_PAGES = (
    Path("pages/01_Temporary_Gemini_OCR.py"),
    Path("pages/02_OCR_Quality_Test.py"),
)


class UXFreezeStaticTests(unittest.TestCase):
    def _ux_freeze_text(self) -> str:
        self.assertTrue(UX_FREEZE_PATH.exists(), "docs/mvp_ux_freeze.md must exist")
        return UX_FREEZE_PATH.read_text(encoding="utf-8")

    def test_ux_freeze_document_exists_and_defines_four_section_flow(self) -> None:
        source = self._ux_freeze_text()

        required = (
            "1. Upload",
            "2. Mask & review",
            "3. OCR",
            "4. Analysis & report",
            "1. Загрузка договора",
            "2. Закрой личные данные",
            "3. Распознать текст",
            "4. Анализ и отчёт",
        )
        for text in required:
            self.assertIn(text, source)

    def test_ux_freeze_keeps_app_py_as_ui_glue(self) -> None:
        source = self._ux_freeze_text()

        self.assertIn("Do not add intelligence to `app.py`", source)
        self.assertIn("Keep `app.py` as Streamlit UI/session glue", source)
        self.assertIn("small modules under `contract_checker/`", source)

    def test_ux_freeze_preserves_single_ocr_action_and_no_prepare_step(self) -> None:
        source = self._ux_freeze_text()

        self.assertIn("Распознать замаскированные страницы", source)
        self.assertIn("The user should not have to perform a separate visible step", source)
        self.assertIn("manually create prepared OCR pages", source)

    def test_ux_freeze_requires_basic_path_without_advanced_sections(self) -> None:
        source = self._ux_freeze_text()

        self.assertIn("without opening any Advanced section", source)
        self.assertIn("If a tester must open Advanced to complete this path", source)

    def test_legacy_sidebar_pages_are_not_in_streamlit_pages_directory(self) -> None:
        for page_path in LEGACY_SIDEBAR_PAGES:
            self.assertFalse(
                page_path.exists(),
                f"Legacy/developer page should not appear in Streamlit sidebar: {page_path}",
            )


if __name__ == "__main__":
    unittest.main()
