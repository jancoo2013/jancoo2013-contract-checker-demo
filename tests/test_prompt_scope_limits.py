"""Prompt tests for partial-document, template, and real-contract scope handling."""

from __future__ import annotations

import unittest

from contract_checker.prompt_builder import SYSTEM_PROMPT_RU, build_contract_audit_prompt


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

    def test_real_contract_prompt_requires_cross_clause_resolution(self) -> None:
        self.assertIn("обязательно сделай второй проход", SYSTEM_PROMPT_RU)
        self.assertIn("Для каждого отдельного обеспечения анализируй механизм целиком", SYSTEM_PROMPT_RU)
        self.assertIn("Широкое определение «существенного/фундаментального нарушения»", SYSTEM_PROMPT_RU)
        self.assertIn("AS-IS", SYSTEM_PROMPT_RU)
        self.assertIn("предварительный осмотр/протокол дефектов", SYSTEM_PROMPT_RU)
        self.assertIn("ограничивает право зачёта/удержания", SYSTEM_PROMPT_RU)

    def test_real_contract_prompt_blocks_wishlist_and_invented_numbers(self) -> None:
        self.assertIn("missing_clauses — не список желательных улучшений", SYSTEM_PROMPT_RU)
        self.assertIn("Отсутствие опции продления, страховки строения", SYSTEM_PROMPT_RU)
        self.assertIn("Не придумывай числовые лимиты", SYSTEM_PROMPT_RU)
        self.assertIn("не является риском само по себе", SYSTEM_PROMPT_RU)
        self.assertNotIn(
            "Сравнивай условия отдельно с: (a) типовой структурой договора аренды жилья в Израиле",
            SYSTEM_PROMPT_RU,
        )

    def test_prompt_includes_deterministic_question_engine_review_inventory(self) -> None:
        messages = build_contract_audit_prompt(
            "--- СТРАНИЦА 1 ---\nהסכם שכירות המשכיר השוכר דמי שכירות תיקונים"
        )
        user_prompt = next(item["content"] for item in messages if item["role"] == "user")
        self.assertIn("ОБЯЗАТЕЛЬНЫЙ QUESTION ENGINE REVIEW INVENTORY", user_prompt)
        for question_id in (
            "security.realization_chain",
            "early_exit.replacement_route",
            "financial_sanctions.holdover_compensation",
            "condition.repair_mechanics",
            "condition.return_condition",
            "termination.cross_clause_interaction",
        ):
            self.assertIn(question_id, user_prompt)


if __name__ == "__main__":
    unittest.main()
