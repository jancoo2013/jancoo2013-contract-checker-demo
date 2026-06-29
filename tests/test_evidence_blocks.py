"""Tests for evidence-block based source validation."""

from __future__ import annotations

import unittest

from contract_checker.evidence_blocks import build_evidence_blocks, evidence_block_map, format_evidence_blocks_for_prompt
from contract_checker.output_validator import validate_model_evidence
from contract_checker.prompt_builder import SYSTEM_PROMPT_RU, build_contract_audit_prompt
from contract_checker.schemas import ClauseAnalysis, ContractAuditResult, DocumentQuality, RiskItem


SOURCE_TEXT = """הסכם שכירות בלתי מוגנת

דמי שכירות יהיו 3,500 ש"ח לחודש.

במקרה של הפרה יסודית תינתן הודעה בכתב ותקופת תיקון של 14 ימים.
"""


def _result_with_evidence(
    risk_ids: list[str] | None = None,
    clause_ids: list[str] | None = None,
    quote: str = "",
) -> ContractAuditResult:
    return ContractAuditResult(
        risk_profile="issues_to_clarify",
        risk_profile_summary_ru="Есть вопросы для уточнения.",
        document_quality=DocumentQuality(usable=True, completeness="medium", problems=[]),
        clauses=[
            ClauseAnalysis(
                clause_id="rent",
                page=None,
                source_quote_he=quote,
                evidence_block_ids=clause_ids or [],
                explanation_ru="Арендная плата указана.",
                category="payments",
                risk_level="normal",
                tenant_obligation=None,
                landlord_obligation=None,
                financial_effect='3,500 ש"ח',
                confidence=0.9,
            )
        ],
        risks=[
            RiskItem(
                title_ru="Срок исправления",
                level="yellow",
                page=None,
                source_quote_he=quote,
                evidence_block_ids=risk_ids or [],
                explanation_ru="Нужно уточнить срок 14 дней.",
                requested_change_ru="Сохранить 14 дней на исправление.",
            )
        ],
        missing_clauses=[],
        unclear_fragments=[],
        questions_to_agent=[],
        proposed_changes=[],
    )


class EvidenceBlockBuilderTests(unittest.TestCase):
    def test_text_without_page_separators_gets_stable_page_one_ids(self) -> None:
        blocks = build_evidence_blocks(SOURCE_TEXT)

        self.assertEqual([block.block_id for block in blocks], ["P1-B01", "P1-B02", "P1-B03"])
        self.assertEqual(blocks[1].page, 1)
        self.assertEqual(blocks[1].text, 'דמי שכירות יהיו 3,500 ש"ח לחודש.')

    def test_page_separators_create_page_specific_ids(self) -> None:
        text = "עמוד ראשון\n\n--- СТРАНИЦА 2 ---\nעמוד שני\n\nעוד סעיף"
        blocks = build_evidence_blocks(text)

        self.assertEqual([block.block_id for block in blocks], ["P1-B01", "P2-B01", "P2-B02"])
        self.assertEqual(blocks[1].text, "עמוד שני")

    def test_format_and_map_preserve_exact_hebrew_text(self) -> None:
        blocks = build_evidence_blocks(SOURCE_TEXT)
        formatted = format_evidence_blocks_for_prompt(blocks)
        mapped = evidence_block_map(blocks)

        self.assertIn("[P1-B02]", formatted)
        self.assertIn('דמי שכירות יהיו 3,500 ש"ח לחודש.', formatted)
        self.assertEqual(mapped["P1-B03"].text, "במקרה של הפרה יסודית תינתן הודעה בכתב ותקופת תיקון של 14 ימים.")


class EvidencePromptTests(unittest.TestCase):
    def test_prompt_uses_evidence_blocks_and_instructions(self) -> None:
        messages = build_contract_audit_prompt(SOURCE_TEXT)
        combined = "\n".join(message["content"] for message in messages)

        self.assertIn("ОБЕЗЛИЧЕННЫЕ EVIDENCE BLOCKS", combined)
        self.assertIn("[P1-B01]", combined)
        self.assertIn("evidence_block_ids", combined)
        self.assertIn("Не генерируй и не переписывай дословные ивритские цитаты", SYSTEM_PROMPT_RU)
        self.assertIn("Не возвращай verdict или verdict_reason_ru", SYSTEM_PROMPT_RU)
        self.assertIn("Не придумывай ID блоков", SYSTEM_PROMPT_RU)


class EvidenceSchemaTests(unittest.TestCase):
    def test_schema_accepts_evidence_ids_without_source_quote(self) -> None:
        result = ContractAuditResult(
            risk_profile="issues_to_clarify",
            risk_profile_summary_ru="Есть вопросы для уточнения.",
            document_quality=DocumentQuality(usable=True, completeness="medium", problems=[]),
            clauses=[
                ClauseAnalysis(
                    clause_id="rent",
                    evidence_block_ids=["P1-B02"],
                    explanation_ru="Арендная плата указана.",
                    category="payments",
                    risk_level="normal",
                    confidence=0.9,
                )
            ],
            risks=[
                RiskItem(
                    title_ru="Срок исправления",
                    level="yellow",
                    evidence_block_ids=["P1-B03"],
                    explanation_ru="Нужно уточнить срок 14 дней.",
                )
            ],
        )

        self.assertEqual(result.clauses[0].source_quote_he, "")
        self.assertEqual(result.risks[0].source_quote_he, "")
        self.assertEqual(result.risks[0].evidence_block_ids, ["P1-B03"])


class EvidenceValidatorTests(unittest.TestCase):
    def test_valid_evidence_ids_populate_exact_source_text(self) -> None:
        result = _result_with_evidence(risk_ids=["P1-B03"], clause_ids=["P1-B02"])
        validated = validate_model_evidence(result, SOURCE_TEXT)

        self.assertEqual(validated.warnings, [])
        self.assertEqual(len(validated.result.risks), 1)
        self.assertEqual(
            validated.result.risks[0].source_quote_he,
            "במקרה של הפרה יסודית תינתן הודעה בכתב ותקופת תיקון של 14 ימים.",
        )
        self.assertEqual(validated.result.clauses[0].source_quote_he, 'דמי שכירות יהיו 3,500 ש"ח לחודש.')

    def test_invalid_evidence_ids_warn_and_remove_risk(self) -> None:
        result = _result_with_evidence(risk_ids=["P9-B99"], clause_ids=["P1-B02"])
        validated = validate_model_evidence(result, SOURCE_TEXT)

        self.assertEqual(validated.result.risks, [])
        self.assertTrue(any("invalid evidence block ID" in warning for warning in validated.warnings))

    def test_bad_clause_evidence_is_downgraded(self) -> None:
        result = _result_with_evidence(risk_ids=["P1-B03"], clause_ids=["P9-B99"])
        validated = validate_model_evidence(result, SOURCE_TEXT)

        self.assertEqual(validated.result.clauses[0].risk_level, "unclear")
        self.assertTrue(any("invalid evidence block ID" in warning for warning in validated.warnings))

    def test_missing_evidence_ids_without_fallback_remove_risk(self) -> None:
        result = _result_with_evidence()
        validated = validate_model_evidence(result, SOURCE_TEXT)

        self.assertEqual(validated.result.risks, [])
        self.assertTrue(any("missing evidence_block_ids" in warning for warning in validated.warnings))

    def test_old_quote_fallback_is_transitional_and_warned(self) -> None:
        quote = "במקרה של הפרה יסודית תינתן הודעה בכתב ותקופת תיקון של 14 ימים."
        result = _result_with_evidence(quote=quote)
        validated = validate_model_evidence(result, SOURCE_TEXT)

        self.assertEqual(len(validated.result.risks), 1)
        self.assertTrue(any("old quote fallback used" in warning for warning in validated.warnings))


if __name__ == "__main__":
    unittest.main()
