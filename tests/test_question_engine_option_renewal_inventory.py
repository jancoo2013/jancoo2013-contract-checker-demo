"""Focused tests for the option / renewal Question Engine inventory slice."""

from __future__ import annotations

from pathlib import Path
import unittest

from contract_checker.question_engine.inventory import OPTION_RENEWAL_CORE_INVENTORY_V1
from contract_checker.question_engine.schema import QuestionInventory


_EXPECTED_OPTION_RENEWAL_QUESTION_IDS = (
    "option.right_structure",
    "option.period",
    "option.economics",
    "option.activation",
    "option.prerequisites",
    "option.external_dependencies",
    "option.cross_clause_interaction",
)


class OptionRenewalCoreInventoryTests(unittest.TestCase):
    def test_inventory_has_exact_bounded_question_set(self) -> None:
        inventory = OPTION_RENEWAL_CORE_INVENTORY_V1

        self.assertIsInstance(inventory, QuestionInventory)
        self.assertEqual(inventory.schema_version, 1)
        self.assertEqual(
            tuple(question.question_id for question in inventory.questions),
            _EXPECTED_OPTION_RENEWAL_QUESTION_IDS,
        )
        self.assertEqual(
            {question.domain for question in inventory.questions},
            {"option_renewal"},
        )

    def test_right_structure_does_not_assume_unilateral_option(self) -> None:
        right_structure = next(
            question
            for question in OPTION_RENEWAL_CORE_INVENTORY_V1.questions
            if question.question_id == "option.right_structure"
        )

        self.assertEqual(
            right_structure.answer_fields,
            (
                "renewal_mechanism_present",
                "right_holder",
                "mechanism_type",
                "unilateral_wording",
                "landlord_consent_required",
            ),
        )
        self.assertNotIn("unilateral_option_exists", right_structure.answer_fields)

    def test_activation_and_economics_remain_separate(self) -> None:
        questions = {
            question.question_id: question
            for question in OPTION_RENEWAL_CORE_INVENTORY_V1.questions
        }

        self.assertEqual(
            questions["option.activation"].answer_fields,
            (
                "activation_actor",
                "activation_notice_required",
                "notice_form",
                "notice_deadline",
                "notice_period",
            ),
        )
        self.assertEqual(
            questions["option.economics"].answer_fields,
            (
                "renewal_rent_amount",
                "renewal_rent_formula",
                "renewal_increase_cap",
                "external_value_dependency",
            ),
        )

    def test_prerequisites_keep_security_and_performance_separate(self) -> None:
        prerequisites = next(
            question
            for question in OPTION_RENEWAL_CORE_INVENTORY_V1.questions
            if question.question_id == "option.prerequisites"
        )

        self.assertEqual(
            prerequisites.answer_fields,
            (
                "performance_condition",
                "security_extension_required",
                "payment_instruments_required",
                "other_prerequisites",
            ),
        )

    def test_external_dependency_records_presence_without_guessing_content(self) -> None:
        dependency = next(
            question
            for question in OPTION_RENEWAL_CORE_INVENTORY_V1.questions
            if question.question_id == "option.external_dependencies"
        )

        self.assertEqual(
            dependency.answer_fields,
            (
                "referenced_addendum",
                "external_writing_required",
                "referenced_document_present",
                "unresolved_dependency",
            ),
        )
        self.assertNotIn("inferred_addendum_contents", dependency.answer_fields)

    def test_golden_fixture_contains_option_ambiguity_grounding(self) -> None:
        root = Path(__file__).resolve().parents[1]
        fixture_path = (
            root
            / "research"
            / "question_engine"
            / "golden_contracts"
            / "contract_001_he.txt"
        )

        fixture = fixture_path.read_text(encoding="utf-8")

        self.assertIn("ניתנת לשוכר אופציה", fixture)
        self.assertIn("[BLANK_IN_SOURCE] חודשים מראש", fixture)
        self.assertIn("בכפוף להסכמת המשכיר לכך", fixture)

    def test_cross_clause_interaction_preserves_ambiguity(self) -> None:
        interaction = next(
            question
            for question in OPTION_RENEWAL_CORE_INVENTORY_V1.questions
            if question.question_id == "option.cross_clause_interaction"
        )

        self.assertEqual(
            interaction.answer_fields,
            (
                "linked_consent_rule",
                "linked_notice_rule",
                "linked_economic_rule",
                "linked_prerequisites",
                "linked_security_rule",
                "interaction_ambiguity",
            ),
        )

    def test_inventory_stays_pre_signing_and_contract_fact_focused(self) -> None:
        joined = "\n".join(
            f"{question.question_id} {question.purpose}"
            for question in OPTION_RENEWAL_CORE_INVENTORY_V1.questions
        ).lower()

        for forbidden in (
            "court will enforce",
            "lawsuit filed",
            "renewal dispute already occurred",
            "tenant already exercised",
            "landlord already refused",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, joined)


if __name__ == "__main__":
    unittest.main()
