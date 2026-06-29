"""Tests for the text-based AI contract audit MVP."""

from __future__ import annotations

import unittest

from contract_checker.output_validator import validate_model_evidence
from contract_checker.prompt_builder import SYSTEM_PROMPT_RU
from contract_checker.redaction import redact_personal_data
from contract_checker.schemas import ClauseAnalysis, ContractAuditResult, DocumentQuality, RiskItem
from contract_checker.validator import validate_contract_text


SAMPLE_CONTRACT = """
הסכם שכירות בלתי מוגנת
שם המשכיר: דוד כהן, ת.ז. 123456789, טלפון 050-123-4567, כתובת: הרצל 10 תל אביב
שם השוכר: משה לוי, מספר זהות 987654321, אימייל test@example.com
1. המשכיר משכיר לשוכר דירה למטרת מגורים בלבד.
2. תקופת השכירות תהיה מיום 15/01/25 ועד ליום 14/01/26.
3. דמי שכירות יהיו 3,500 ש"ח לחודש וישולמו בכל 1 לחודש.
4. השוכר יפקיד פיקדון בסך 7,000 ש"ח להבטחת התחייבויותיו.
5. השוכר ישלם חשמל, מים, ארנונה וועד בית לפי צריכה.
6. המשכיר יהיה אחראי לתיקון ליקויים מהותיים שאינם נגרמו על ידי השוכר.
7. השוכר רשאי להביא שוכר חלופי בכפוף להסכמת המשכיר שלא תסורב מטעמים בלתי סבירים.
8. במקרה של הפרה יסודית תינתן הודעה בכתב ותקופת תיקון של 14 ימים.
בנק לאומי חשבון 123456 סניף 800
"""


def _sample_result(quote: str) -> ContractAuditResult:
    return ContractAuditResult(
        risk_profile="issues_to_clarify",
        risk_profile_summary_ru="Есть проверяемые условия и вопросы для уточнения.",
        document_quality=DocumentQuality(usable=True, completeness="medium", problems=[]),
        clauses=[
            ClauseAnalysis(
                clause_id="rent",
                page=None,
                source_quote_he='דמי שכירות יהיו 3,500 ש"ח לחודש',
                explanation_ru="Арендная плата указана ясно.",
                category="payments",
                risk_level="normal",
                tenant_obligation="Платить аренду.",
                landlord_obligation=None,
                financial_effect='3,500 ש"ח в месяц',
                confidence=0.9,
            )
        ],
        risks=[
            RiskItem(
                title_ru="Проверяемый риск",
                level="yellow",
                page=None,
                source_quote_he=quote,
                explanation_ru="Нужно уточнить 14 дней.",
                requested_change_ru="Сохранить 14 дней на исправление.",
            )
        ],
        missing_clauses=[],
        unclear_fragments=[],
        questions_to_agent=[],
        proposed_changes=[],
    )


class RedactionTests(unittest.TestCase):
    def test_ids_phones_emails_and_bank_data_are_redacted_but_terms_remain(self) -> None:
        redacted = redact_personal_data(SAMPLE_CONTRACT)

        self.assertIn("[ID УДАЛЁН]", redacted)
        self.assertIn("[ТЕЛЕФОН УДАЛЁН]", redacted)
        self.assertIn("[EMAIL УДАЛЁН]", redacted)
        self.assertIn("[БАНКОВСКИЕ ДАННЫЕ УДАЛЕНЫ]", redacted)
        self.assertNotIn("123456789", redacted)
        self.assertNotIn("050-123-4567", redacted)
        self.assertNotIn("test@example.com", redacted)
        self.assertIn('3,500 ש"ח', redacted)
        self.assertIn("15/01/25", redacted)


class ValidatorTests(unittest.TestCase):
    def test_validator_accepts_realistic_redacted_hebrew_rental_contract(self) -> None:
        redacted = redact_personal_data(SAMPLE_CONTRACT)
        result = validate_contract_text(redacted)

        self.assertTrue(result.usable, result.problems)
        self.assertGreaterEqual(result.indicator_count, 4)

    def test_validator_rejects_random_or_very_short_text(self) -> None:
        self.assertFalse(validate_contract_text("abc xyz 123 lorem ipsum" * 3).usable)
        self.assertFalse(validate_contract_text("חוזה שכירות").usable)


class SchemaTests(unittest.TestCase):
    def test_schema_rejects_unknown_fields(self) -> None:
        with self.assertRaises(Exception):
            DocumentQuality(usable=True, completeness="high", problems=[], unknown="boom")  # type: ignore[call-arg]

    def test_contract_audit_result_accepts_risk_profile_shell(self) -> None:
        result = _sample_result("תקופת תיקון של 14 ימים")

        self.assertEqual(result.risk_profile, "issues_to_clarify")
        self.assertEqual(result.risk_profile_summary_ru, "Есть проверяемые условия и вопросы для уточнения.")
        self.assertNotIn("verdict", result.model_dump())
        self.assertNotIn("verdict_reason_ru", result.model_dump())

    def test_old_verdict_fields_are_not_part_of_schema(self) -> None:
        payload = _sample_result("תקופת תיקון של 14 ימים").model_dump()
        payload["verdict"] = "Можно обсуждать"
        payload["verdict_reason_ru"] = "Старое поле."

        with self.assertRaises(Exception):
            ContractAuditResult.model_validate(payload)


class EvidenceValidatorTests(unittest.TestCase):
    def test_evidence_validator_accepts_exact_quotes(self) -> None:
        redacted = redact_personal_data(SAMPLE_CONTRACT)
        result = _sample_result("תקופת תיקון של 14 ימים")
        validated = validate_model_evidence(result, redacted)

        self.assertEqual(len(validated.result.risks), 1)
        self.assertEqual(validated.warnings, [])

    def test_evidence_validator_rejects_fabricated_quotes(self) -> None:
        redacted = redact_personal_data(SAMPLE_CONTRACT)
        result = _sample_result("ציטוט שלא קיים בחוזה")
        validated = validate_model_evidence(result, redacted)

        self.assertEqual(validated.result.risks, [])
        self.assertTrue(validated.warnings)


class PromptTests(unittest.TestCase):
    def test_prompt_defines_red_and_yellow_levels(self) -> None:
        self.assertIn("red:", SYSTEM_PROMPT_RU)
        self.assertIn("yellow:", SYSTEM_PROMPT_RU)
        self.assertIn("существенной финансовой потере", SYSTEM_PROMPT_RU)

    def test_replacement_tenant_requirement_is_not_automatically_red(self) -> None:
        self.assertIn("не является автоматически красным риском", SYSTEM_PROMPT_RU)
        self.assertIn("практически делает выход невозможным", SYSTEM_PROMPT_RU)

    def test_prompt_requests_risk_profile_instead_of_legal_verdict(self) -> None:
        self.assertIn("risk_profile", SYSTEM_PROMPT_RU)
        self.assertIn("risk_profile_summary_ru", SYSTEM_PROMPT_RU)
        self.assertIn("Не возвращай verdict или verdict_reason_ru", SYSTEM_PROMPT_RU)
        self.assertIn("Не прогнозируй исход суда или спора", SYSTEM_PROMPT_RU)
        self.assertIn("Не утверждай с уверенностью", SYSTEM_PROMPT_RU)
        self.assertIn("может создавать риск", SYSTEM_PROMPT_RU)


class ImportTests(unittest.TestCase):
    def test_app_and_helpers_import_without_api_key(self) -> None:
        import app  # noqa: F401
        import contract_checker.gemini_engine  # noqa: F401

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
