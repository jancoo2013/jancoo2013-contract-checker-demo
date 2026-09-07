"""Focused tests for the Question Engine schema foundation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from enum import Enum
import unittest

import contract_checker.question_engine as question_engine
from contract_checker.question_engine import AnswerState, QuestionInventory, QuestionSpec


def _question(**overrides: object) -> QuestionSpec:
    values: dict[str, object] = {
        "question_id": "economic.monthly_rent",
        "domain": "economic",
        "purpose": "Identify the stated monthly rent.",
        "answer_fields": ("amount", "currency"),
    }
    values.update(overrides)
    return QuestionSpec(**values)  # type: ignore[arg-type]


class AnswerStateTests(unittest.TestCase):
    def test_answer_state_is_string_enum_with_exact_members(self) -> None:
        self.assertTrue(issubclass(AnswerState, str))
        self.assertTrue(issubclass(AnswerState, Enum))
        self.assertEqual(
            [(member.name, member.value) for member in AnswerState],
            [
                ("FOUND", "FOUND"),
                ("NOT_FOUND", "NOT_FOUND"),
                ("AMBIGUOUS", "AMBIGUOUS"),
                ("HANDWRITING_DEPENDENCY", "HANDWRITING_DEPENDENCY"),
                (
                    "CLAUSE_PRESENT_VALUE_BLANK",
                    "CLAUSE_PRESENT_VALUE_BLANK",
                ),
            ],
        )


class QuestionSpecTests(unittest.TestCase):
    def test_fields_are_exact_and_values_are_immutable(self) -> None:
        question = _question(answer_fields=["amount", "currency"])

        self.assertEqual(
            [field.name for field in fields(QuestionSpec)],
            ["question_id", "domain", "purpose", "answer_fields"],
        )
        self.assertEqual(question.answer_fields, ("amount", "currency"))
        with self.assertRaises(FrozenInstanceError):
            question.domain = "other"  # type: ignore[misc]

    def test_malformed_dotted_question_ids_are_rejected(self) -> None:
        malformed_ids = (
            "economic",
            ".economic",
            "economic.",
            "economic..rent",
            "Economic.rent",
            "economic.monthly-rent",
            "economic._rent",
            "economic.monthly__rent",
            "economic.1rent",
        )

        for question_id in malformed_ids:
            with self.subTest(question_id=question_id):
                with self.assertRaisesRegex(ValueError, "dotted snake_case"):
                    _question(question_id=question_id)

    def test_empty_domain_and_purpose_are_rejected(self) -> None:
        for field_name in ("domain", "purpose"):
            for value in ("", "   "):
                with self.subTest(field_name=field_name, value=value):
                    with self.assertRaisesRegex(
                        ValueError, f"{field_name} must not be empty"
                    ):
                        _question(**{field_name: value})

    def test_empty_and_duplicate_answer_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "answer_fields must not be empty"):
            _question(answer_fields=())
        with self.assertRaisesRegex(ValueError, "must not contain duplicates"):
            _question(answer_fields=("amount", "amount"))

    def test_malformed_snake_case_answer_fields_are_rejected(self) -> None:
        malformed_fields = (
            "Amount",
            "monthly.amount",
            "monthly-amount",
            "_amount",
            "amount_",
            "monthly__amount",
            "1_amount",
        )

        for answer_field in malformed_fields:
            with self.subTest(answer_field=answer_field):
                with self.assertRaisesRegex(ValueError, "snake_case"):
                    _question(answer_fields=(answer_field,))


class QuestionInventoryTests(unittest.TestCase):
    def test_fields_are_exact_and_values_are_immutable(self) -> None:
        inventory = QuestionInventory(schema_version=1, questions=[_question()])

        self.assertEqual(
            [field.name for field in fields(QuestionInventory)],
            ["schema_version", "questions"],
        )
        self.assertIsInstance(inventory.questions, tuple)
        with self.assertRaises(FrozenInstanceError):
            inventory.schema_version = 2  # type: ignore[misc]

    def test_non_positive_and_unsupported_schema_versions_are_rejected(self) -> None:
        for schema_version in (0, -1, True, 2):
            with self.subTest(schema_version=schema_version):
                with self.assertRaisesRegex(ValueError, "schema_version"):
                    QuestionInventory(
                        schema_version=schema_version,  # type: ignore[arg-type]
                        questions=(_question(),),
                    )

    def test_empty_inventory_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "questions must not be empty"):
            QuestionInventory(schema_version=1, questions=())

    def test_duplicate_question_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate question IDs"):
            QuestionInventory(
                schema_version=1,
                questions=(_question(), _question()),
            )

    def test_public_exports_are_exact(self) -> None:
        self.assertEqual(
            question_engine.__all__,
            ("AnswerState", "QuestionInventory", "QuestionSpec"),
        )


if __name__ == "__main__":
    unittest.main()
