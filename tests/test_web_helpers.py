"""Tests for Russian display label helpers."""

from __future__ import annotations

import unittest

from contract_checker.web_helpers import (
    handwriting_status_label,
    severity_label,
    source_label,
    status_label,
)


class WebHelperLabelTests(unittest.TestCase):
    def test_required_status_labels_are_russian(self) -> None:
        self.assertEqual(status_label("confirmed"), "подтверждено")
        self.assertEqual(status_label("suspected"), "требует внимания")
        self.assertEqual(status_label("inconsistent"), "противоречие")
        self.assertEqual(status_label("manual_review"), "ручная проверка")

    def test_required_severity_labels_are_russian(self) -> None:
        self.assertEqual(severity_label("low"), "низкая")
        self.assertEqual(severity_label("medium"), "средняя")
        self.assertEqual(severity_label("high"), "высокая")

    def test_required_source_labels_are_russian(self) -> None:
        self.assertEqual(source_label("printed"), "печатный текст")
        self.assertEqual(source_label("handwritten"), "рукописное поле")
        self.assertEqual(source_label("mixed"), "смешанный источник")
        self.assertEqual(source_label("unknown"), "неизвестно")

    def test_required_handwriting_status_labels_are_russian(self) -> None:
        self.assertEqual(handwriting_status_label("none"), "рукопись не обнаружена")
        self.assertEqual(handwriting_status_label("detected"), "обнаружена рукопись")
        self.assertEqual(handwriting_status_label("candidate_supplied"), "есть гипотеза по рукописи")
        self.assertEqual(handwriting_status_label("unreadable"), "рукопись не читается")


if __name__ == "__main__":
    unittest.main()
