"""Focused tests for bounded Question Engine inventories."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from contract_checker.question_engine.inventory import (
    CONDITION_DEFECTS_CORE_INVENTORY_V1,
    EARLY_EXIT_CORE_INVENTORY_V1,
    ECONOMIC_CORE_INVENTORY_V1,
    FINANCIAL_SANCTIONS_CORE_INVENTORY_V1,
    TERMINATION_CURE_CORE_INVENTORY_V1,
)
from contract_checker.question_engine.schema import QuestionInventory


_EXPECTED_ECONOMIC_QUESTION_IDS = (
    "economic.monthly_rent",
    "security.instrument_inventory",
    "security.instrument_relationship",
    "security.instrument_amounts",
    "security.instrument_blanks",
    "security.instrument_control",
    "security.completion_authority",
    "security.instrument_linkage",
    "security.realization_chain",
    "security.recovery_overlap",
    "security.option_continuity",
    "security.return_mechanics",
    "security.guarantor_scope",
)

_EXPECTED_EARLY_EXIT_QUESTION_IDS = (
    "early_exit.continuing_liability",
    "early_exit.replacement_route",
    "early_exit.approval_standard",
    "early_exit.assignment_subletting_interaction",
    "early_exit.release_consequences",
)

_EXPECTED_FINANCIAL_SANCTIONS_QUESTION_IDS = (
    "financial_sanctions.late_payment",
    "financial_sanctions.holdover_compensation",
    "financial_sanctions.fixed_agreed_damages",
    "financial_sanctions.other_contractual_sanctions",
    "financial_sanctions.overlap",
)

_EXPECTED_CONDITION_DEFECTS_QUESTION_IDS = (
    "condition.entry_baseline",
    "condition.as_is_acknowledgment",
    "condition.pre_existing_defects",
    "condition.damage_allocation",
    "condition.repair_mechanics",
    "condition.return_condition",
    "condition.evidence_dependencies",
)

_EXPECTED_TERMINATION_CURE_QUESTION_IDS = (
    "termination.breach_triggers",
    "termination.fundamental_breach_definition",
    "termination.notice_cure",
    "termination.cancellation_mechanics",
    "termination.vacancy_demand",
    "termination.cross_clause_interaction",
)


class EconomicCoreInventoryTests(unittest.TestCase):
    def test_inventory_has_exact_bounded_question_set(self) -> None:
        inventory = ECONOMIC_CORE_INVENTORY_V1

        self.assertIsInstance(inventory, QuestionInventory)
        self.assertEqual(inventory.schema_version, 1)
        self.assertEqual(
            tuple(question.question_id for question in inventory.questions),
            _EXPECTED_ECONOMIC_QUESTION_IDS,
        )

    def test_inventory_is_limited_to_economic_and_security_domains(self) -> None:
        self.assertEqual(
            {question.domain for question in ECONOMIC_CORE_INVENTORY_V1.questions},
            {"economic", "security"},
        )

    def test_realization_chain_keeps_material_steps_separate(self) -> None:
        realization = next(
            question
            for question in ECONOMIC_CORE_INVENTORY_V1.questions
            if question.question_id == "security.realization_chain"
        )

        self.assertEqual(
            realization.answer_fields,
            (
                "realization_grounds",
                "amount_basis",
                "notice_required",
                "notice_period",
                "cure_available",
                "cure_period",
            ),
        )

    def test_inventory_preserves_distinct_instrument_and_overlap_questions(self) -> None:
        question_ids = {
            question.question_id for question in ECONOMIC_CORE_INVENTORY_V1.questions
        }

        self.assertIn("security.instrument_inventory", question_ids)
        self.assertIn("security.instrument_relationship", question_ids)
        self.assertIn("security.instrument_control", question_ids)
        self.assertIn("security.recovery_overlap", question_ids)
        self.assertNotIn("security.generic_deposit", question_ids)

    def test_instrument_control_covers_payee_and_transfer_restriction(self) -> None:
        control = next(
            question
            for question in ECONOMIC_CORE_INVENTORY_V1.questions
            if question.question_id == "security.instrument_control"
        )

        self.assertEqual(
            control.answer_fields,
            ("instrument_payees", "transfer_restrictions"),
        )

    def test_golden_fixture_metadata_contains_security_grounding(self) -> None:
        root = Path(__file__).resolve().parents[1]
        metadata_path = (
            root
            / "research"
            / "question_engine"
            / "golden_contracts"
            / "contract_001.meta.json"
        )

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertIn("security amount", metadata["preserved_legal_values"])
        self.assertTrue(
            any(
                "Clause 11" in note and "security check" in note
                for note in metadata["source_fidelity_notes"]
            )
        )

    def test_inventory_does_not_encode_post_dispute_runtime_questions(self) -> None:
        joined = "\n".join(
            f"{question.question_id} {question.purpose}"
            for question in ECONOMIC_CORE_INVENTORY_V1.questions
        ).lower()

        for forbidden in (
            "lawsuit filed",
            "execution warning received",
            "keys returned later",
            "apartment re-let",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, joined)


class EarlyExitCoreInventoryTests(unittest.TestCase):
    def test_inventory_has_exact_bounded_question_set(self) -> None:
        inventory = EARLY_EXIT_CORE_INVENTORY_V1

        self.assertIsInstance(inventory, QuestionInventory)
        self.assertEqual(inventory.schema_version, 1)
        self.assertEqual(
            tuple(question.question_id for question in inventory.questions),
            _EXPECTED_EARLY_EXIT_QUESTION_IDS,
        )
        self.assertEqual(
            {question.domain for question in inventory.questions},
            {"early_exit"},
        )

    def test_cross_clause_components_remain_separate_questions(self) -> None:
        question_ids = {
            question.question_id for question in EARLY_EXIT_CORE_INVENTORY_V1.questions
        }

        self.assertIn("early_exit.continuing_liability", question_ids)
        self.assertIn("early_exit.replacement_route", question_ids)
        self.assertIn("early_exit.approval_standard", question_ids)
        self.assertIn("early_exit.assignment_subletting_interaction", question_ids)
        self.assertIn("early_exit.release_consequences", question_ids)
        self.assertNotIn("early_exit.allowed", question_ids)

    def test_approval_standard_and_release_consequences_stay_separate(self) -> None:
        questions = {
            question.question_id: question
            for question in EARLY_EXIT_CORE_INVENTORY_V1.questions
        }

        self.assertEqual(
            questions["early_exit.approval_standard"].answer_fields,
            (
                "landlord_approval_required",
                "approval_standard",
                "stated_refusal_grounds",
            ),
        )
        self.assertEqual(
            questions["early_exit.release_consequences"].answer_fields,
            (
                "release_trigger",
                "future_rent_release",
                "additional_payment_rule",
            ),
        )

    def test_inventory_stays_pre_signing(self) -> None:
        joined = "\n".join(
            f"{question.question_id} {question.purpose}"
            for question in EARLY_EXIT_CORE_INVENTORY_V1.questions
        ).lower()

        for forbidden in (
            "candidate already proposed",
            "keys returned later",
            "actual re-letting",
            "lawsuit filed",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, joined)


class FinancialSanctionsCoreInventoryTests(unittest.TestCase):
    def test_inventory_has_exact_bounded_question_set(self) -> None:
        inventory = FINANCIAL_SANCTIONS_CORE_INVENTORY_V1

        self.assertIsInstance(inventory, QuestionInventory)
        self.assertEqual(inventory.schema_version, 1)
        self.assertEqual(
            tuple(question.question_id for question in inventory.questions),
            _EXPECTED_FINANCIAL_SANCTIONS_QUESTION_IDS,
        )
        self.assertEqual(
            {question.domain for question in inventory.questions},
            {"financial_sanctions"},
        )

    def test_sanction_mechanisms_remain_separate_questions(self) -> None:
        question_ids = {
            question.question_id
            for question in FINANCIAL_SANCTIONS_CORE_INVENTORY_V1.questions
        }

        self.assertIn("financial_sanctions.late_payment", question_ids)
        self.assertIn("financial_sanctions.holdover_compensation", question_ids)
        self.assertIn("financial_sanctions.fixed_agreed_damages", question_ids)
        self.assertIn("financial_sanctions.other_contractual_sanctions", question_ids)
        self.assertIn("financial_sanctions.overlap", question_ids)
        self.assertNotIn("financial_sanctions.total_penalty", question_ids)

    def test_late_payment_keeps_principal_rate_period_and_indexation_separate(self) -> None:
        late_payment = next(
            question
            for question in FINANCIAL_SANCTIONS_CORE_INVENTORY_V1.questions
            if question.question_id == "financial_sanctions.late_payment"
        )

        self.assertEqual(
            late_payment.answer_fields,
            (
                "late_payment_trigger",
                "principal_reference",
                "interest_rate",
                "interest_period",
                "partial_period_rule",
                "indexation_formula",
                "accrual_start",
                "accrual_end",
            ),
        )

    def test_overlap_keeps_trigger_loss_and_interaction_separate(self) -> None:
        overlap = next(
            question
            for question in FINANCIAL_SANCTIONS_CORE_INVENTORY_V1.questions
            if question.question_id == "financial_sanctions.overlap"
        )

        self.assertEqual(
            overlap.answer_fields,
            (
                "overlapping_mechanisms",
                "shared_trigger",
                "shared_loss_head",
                "cumulative_language",
                "interaction_rule",
            ),
        )

    def test_golden_fixture_metadata_contains_financial_sanction_grounding(self) -> None:
        root = Path(__file__).resolve().parents[1]
        metadata_path = (
            root
            / "research"
            / "question_engine"
            / "golden_contracts"
            / "contract_001.meta.json"
        )

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        preserved_values = metadata["preserved_legal_values"]

        self.assertIn("late-interest percentage", preserved_values)
        self.assertIn("daily holdover amount", preserved_values)

    def test_inventory_does_not_encode_court_outcome_or_reduction_rule(self) -> None:
        joined = "\n".join(
            f"{question.question_id} {question.purpose}"
            for question in FINANCIAL_SANCTIONS_CORE_INVENTORY_V1.questions
        ).lower()

        for forbidden in (
            "court will reduce",
            "court would reduce",
            "unenforceable",
            "lawsuit filed",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, joined)


class ConditionDefectsCoreInventoryTests(unittest.TestCase):
    def test_inventory_has_exact_bounded_question_set(self) -> None:
        inventory = CONDITION_DEFECTS_CORE_INVENTORY_V1

        self.assertIsInstance(inventory, QuestionInventory)
        self.assertEqual(inventory.schema_version, 1)
        self.assertEqual(
            tuple(question.question_id for question in inventory.questions),
            _EXPECTED_CONDITION_DEFECTS_QUESTION_IDS,
        )
        self.assertEqual(
            {question.domain for question in inventory.questions},
            {"condition_defects"},
        )

    def test_as_is_and_pre_existing_defects_remain_separate_questions(self) -> None:
        question_ids = {
            question.question_id
            for question in CONDITION_DEFECTS_CORE_INVENTORY_V1.questions
        }

        self.assertIn("condition.entry_baseline", question_ids)
        self.assertIn("condition.as_is_acknowledgment", question_ids)
        self.assertIn("condition.pre_existing_defects", question_ids)
        self.assertIn("condition.damage_allocation", question_ids)
        self.assertNotIn("condition.good_or_bad", question_ids)

    def test_damage_allocation_preserves_ordinary_wear_exception(self) -> None:
        damage = next(
            question
            for question in CONDITION_DEFECTS_CORE_INVENTORY_V1.questions
            if question.question_id == "condition.damage_allocation"
        )

        self.assertEqual(
            damage.answer_fields,
            (
                "tenant_caused_damage_rule",
                "ordinary_wear_exception",
                "causation_standard",
                "repair_standard",
            ),
        )

    def test_repair_mechanics_keeps_notice_and_self_help_separate(self) -> None:
        repair = next(
            question
            for question in CONDITION_DEFECTS_CORE_INVENTORY_V1.questions
            if question.question_id == "condition.repair_mechanics"
        )

        self.assertEqual(
            repair.answer_fields,
            (
                "tenant_repair_scope",
                "landlord_repair_scope",
                "notice_required",
                "repair_deadline",
                "tenant_self_help_available",
                "reimbursement_or_setoff_rule",
            ),
        )

    def test_evidence_dependency_records_presence_without_guessing_content(self) -> None:
        dependency = next(
            question
            for question in CONDITION_DEFECTS_CORE_INVENTORY_V1.questions
            if question.question_id == "condition.evidence_dependencies"
        )

        self.assertEqual(
            dependency.answer_fields,
            (
                "condition_document_references",
                "defect_list_reference",
                "inventory_reference",
                "referenced_documents_present",
            ),
        )
        self.assertNotIn("inferred_document_contents", dependency.answer_fields)

    def test_sanitized_golden_fixture_contains_condition_grounding(self) -> None:
        root = Path(__file__).resolve().parents[1]
        fixture_path = (
            root
            / "research"
            / "question_engine"
            / "golden_contracts"
            / "contract_001_he.txt"
        )

        fixture = fixture_path.read_text(encoding="utf-8")

        self.assertIn("בלאי סביר", fixture)
        self.assertIn('נספח "ב"', fixture)
        self.assertIn("ראה ובדק את הדירה", fixture)

    def test_inventory_stays_pre_signing_and_contract_fact_focused(self) -> None:
        joined = "\n".join(
            f"{question.question_id} {question.purpose}"
            for question in CONDITION_DEFECTS_CORE_INVENTORY_V1.questions
        ).lower()

        for forbidden in (
            "post-move-out photographs",
            "expert report",
            "lawsuit filed",
            "court will decide",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, joined)


class TerminationCureCoreInventoryTests(unittest.TestCase):
    def test_inventory_has_exact_bounded_question_set(self) -> None:
        inventory = TERMINATION_CURE_CORE_INVENTORY_V1

        self.assertIsInstance(inventory, QuestionInventory)
        self.assertEqual(inventory.schema_version, 1)
        self.assertEqual(
            tuple(question.question_id for question in inventory.questions),
            _EXPECTED_TERMINATION_CURE_QUESTION_IDS,
        )
        self.assertEqual(
            {question.domain for question in inventory.questions},
            {"termination_cure"},
        )

    def test_fundamental_breach_notice_and_vacancy_remain_separate(self) -> None:
        question_ids = {
            question.question_id
            for question in TERMINATION_CURE_CORE_INVENTORY_V1.questions
        }

        self.assertIn("termination.breach_triggers", question_ids)
        self.assertIn("termination.fundamental_breach_definition", question_ids)
        self.assertIn("termination.notice_cure", question_ids)
        self.assertIn("termination.cancellation_mechanics", question_ids)
        self.assertIn("termination.vacancy_demand", question_ids)
        self.assertNotIn("termination.eviction_allowed", question_ids)

    def test_notice_cure_keeps_form_timing_and_exceptions_separate(self) -> None:
        notice_cure = next(
            question
            for question in TERMINATION_CURE_CORE_INVENTORY_V1.questions
            if question.question_id == "termination.notice_cure"
        )

        self.assertEqual(
            notice_cure.answer_fields,
            (
                "notice_required",
                "notice_form",
                "notice_period",
                "cure_available",
                "cure_period",
                "cure_exceptions",
            ),
        )

    def test_vacancy_question_preserves_contract_wording_without_procedure_field(self) -> None:
        vacancy = next(
            question
            for question in TERMINATION_CURE_CORE_INVENTORY_V1.questions
            if question.question_id == "termination.vacancy_demand"
        )

        self.assertEqual(
            vacancy.answer_fields,
            (
                "vacancy_demand_available",
                "vacancy_trigger",
                "vacancy_deadline",
                "immediate_vacancy_wording",
                "self_help_or_physical_removal_wording",
            ),
        )
        self.assertNotIn("physical_eviction_procedure", vacancy.answer_fields)

    def test_cross_clause_interaction_keeps_remedy_layers_distinct(self) -> None:
        interaction = next(
            question
            for question in TERMINATION_CURE_CORE_INVENTORY_V1.questions
            if question.question_id == "termination.cross_clause_interaction"
        )

        self.assertEqual(
            interaction.answer_fields,
            (
                "linked_breach_categories",
                "linked_notice_cure_rules",
                "linked_cancellation_rules",
                "linked_vacancy_rules",
                "interaction_ambiguity",
            ),
        )

    def test_sanitized_golden_fixture_contains_termination_grounding(self) -> None:
        root = Path(__file__).resolve().parents[1]
        fixture_path = (
            root
            / "research"
            / "question_engine"
            / "golden_contracts"
            / "contract_001_he.txt"
        )

        fixture = fixture_path.read_text(encoding="utf-8")

        self.assertIn("הפרה יסודית", fixture)
        self.assertIn("פינוי מיידי", fixture)
        self.assertIn("72 שעות", fixture)

    def test_inventory_stays_pre_signing_and_does_not_encode_eviction_procedure(self) -> None:
        joined = "\n".join(
            f"{question.question_id} {question.purpose}"
            for question in TERMINATION_CURE_CORE_INVENTORY_V1.questions
        ).lower()

        for forbidden in (
            "bailiff",
            "physical eviction procedure",
            "court order required",
            "lawsuit filed",
            "landlord may physically remove",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, joined)


if __name__ == "__main__":
    unittest.main()
