"""Focused tests for bounded Question Engine inventories."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from contract_checker.question_engine.inventory import (
    EARLY_EXIT_CORE_INVENTORY_V1,
    ECONOMIC_CORE_INVENTORY_V1,
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

    def test_golden_fixture_contains_early_exit_and_transfer_grounding(self) -> None:
        root = Path(__file__).resolve().parents[1]
        fixture_path = (
            root
            / "research"
            / "question_engine"
            / "golden_contracts"
            / "contract_001_he.txt"
        )
        fixture = fixture_path.read_text(encoding="utf-8")

        self.assertIn("אם יפנה השוכר את הדירה לפני תום התקופה הקצובה", fixture)
        self.assertIn("השוכר אינו רשאי להעביר זכויותיו לפי הסכם זה", fixture)

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


if __name__ == "__main__":
    unittest.main()
