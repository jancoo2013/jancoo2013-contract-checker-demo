"""Tests for PDF text-template extraction helpers."""

from __future__ import annotations

import unittest

from contract_checker.pdf_text import (
    PDF_TEXT_STATUS_EMPTY_OR_SCANNED,
    PDF_TEXT_STATUS_TEXT,
    assemble_pdf_page_texts,
    build_pdf_page_header,
    classify_pdf_text,
    count_hebrew_chars,
)


class PDFTextHelperTests(unittest.TestCase):
    def test_count_hebrew_chars(self) -> None:
        self.assertEqual(count_hebrew_chars("abc חוזה 123"), 4)

    def test_build_pdf_page_header(self) -> None:
        self.assertEqual(
            build_pdf_page_header(page_number=2, filename="lease.pdf"),
            "--- PDF PAGE 2: lease.pdf ---",
        )

    def test_assemble_pdf_page_texts_adds_page_headers(self) -> None:
        text = assemble_pdf_page_texts(
            filename="lease.pdf",
            page_texts=["first page", "second page"],
        )

        self.assertIn("--- PDF PAGE 1: lease.pdf ---", text)
        self.assertIn("--- PDF PAGE 2: lease.pdf ---", text)
        self.assertIn("first page", text)
        self.assertIn("second page", text)

    def test_classify_short_or_non_hebrew_text_as_scanned_or_empty(self) -> None:
        status, problems = classify_pdf_text(text="short", page_count=1)

        self.assertEqual(status, PDF_TEXT_STATUS_EMPTY_OR_SCANNED)
        self.assertTrue(problems)

    def test_classify_sufficient_hebrew_text_as_text_pdf(self) -> None:
        hebrew_text = "חוזה שכירות בלתי מוגנת " * 20
        status, problems = classify_pdf_text(text=hebrew_text, page_count=1)

        self.assertEqual(status, PDF_TEXT_STATUS_TEXT)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
