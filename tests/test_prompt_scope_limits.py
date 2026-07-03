"""Prompt tests for partial-document and blank-template scope handling."""

from __future__ import annotations

import unittest

from contract_checker.prompt_builder import SYSTEM_PROMPT_RU


class PromptScopeLimitTests(unittest.TestCase):
    def test_partial_documents_are_scope_limitations_not_missing_red_clauses(self) -> None:
        self.assertIn("Если загружена только часть договора или одна страница", SYSTEM_PROMPT_RU)
        self.assertIn("ограничение объёма проверки", SYSTEM_PROMPT_RU)
        self.assertIn("не помещай финансовые условия", SYSTEM_PROMPT_RU.lower())
        self.assertIn("missing_clauses", SYSTEM_PROMPT_RU)
        self.assertIn("importance red", SYSTEM_PROMPT_RU)
        self.assertIn("questions_to_agent", SYSTEM_PROMPT_RU)

    def test_blank_variable_fields_are_not_document_quality_problems(self) -> None:
        self.assertIn("Незаполненность формы не добавляй в document_quality.problems", SYSTEM_PROMPT_RU)
        self.assertIn("плохой OCR", SYSTEM_PROMPT_RU)
        self.assertIn("обрезанные/повреждённые страницы", SYSTEM_PROMPT_RU)

    def test_proposed_changes_are_not_based_on_single_missing_page_scope(self) -> None:
        self.assertIn("proposed_changes", SYSTEM_PROMPT_RU)
        self.assertIn("не должны предлагать добавить пункт только потому", SYSTEM_PROMPT_RU)
        self.assertIn("не виден на одной загруженной странице", SYSTEM_PROMPT_RU)


if __name__ == "__main__":
    unittest.main()
