"""Tests for the Question Engine schema foundation."""

from __future__ import annotations

import unittest
from typing import get_args

import contract_checker.question_engine.schema as schema_module
from contract_checker.question_engine import (
    AnswerState,
    EvidenceLayer,
    QuestionDefinition,
    QuestionInventory,
)


class QuestionEngineSchemaTests(unittest.TestCase):
    def test_canonical_answer_states_are_exact_and_stable(self) -> None:
        self.assertEqual(
            get_args(AnswerState),
            (
                "FOUND",
                "NOT_FOUND",
                "AMBIGUOUS",
                "HANDWRITING_DEPENDENCY",
                "CLAUSE_PRESENT_VALUE_BLANK",
            ),
        )

    def test_evidence_layers_keep_source_rule_and_explanation_separate(self) -> None:
        self.assertEqual(
            get_args(EvidenceLayer),
            ("CONTRACT_FACT", "STATUTORY_RULE", "PRODUCT_EXPLANATION"),
        )

    def test_nested_question_definition_round_trips_without_source_text(self) -> None:
        inventory = QuestionInventory.model_validate(
            {
                "schema_version": 1,
                "questions": [
                    {
                        "question_id": "example-question",
                        "topic_id": "example-topic",
                        "answer_fields": [
                            {"field_id": "amount", "value_type": "MONEY"}
                        ],
                        "evidence_targets": [
                            {
                                "target_id": "printed-clause",
                                "layer": "CONTRACT_FACT",
                            }
                        ],
                        "conditional_follow_ups": [
                            {
                                "question_id": "example-follow-up",
                                "when_states": [
                                    "AMBIGUOUS",
                                    "HANDWRITING_DEPENDENCY",
                                ],
                            }
                        ],
                        "statutory_rule_ids": ["reserved-rule"],
                        "remediation_ids": ["reserved-remediation"],
                    }
                ],
            }
        )

        dumped = inventory.model_dump()
        self.assertEqual(dumped["questions"][0]["kind"], "CORE")
        self.assertEqual(
            dumped["questions"][0]["conditional_follow_ups"][0]["when_states"],
            ["AMBIGUOUS", "HANDWRITING_DEPENDENCY"],
        )
        self.assertNotIn("source_text", repr(dumped))
        self.assertNotIn("source_quote", repr(dumped))

    def test_invalid_literals_and_extra_fields_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            QuestionDefinition.model_validate(
                {
                    "question_id": "example-question",
                    "topic_id": "example-topic",
                    "kind": "MODEL_OWNED",
                }
            )

        with self.assertRaises(ValueError):
            QuestionInventory.model_validate(
                {
                    "schema_version": 1,
                    "questions": [],
                    "source_text": "must never be part of the inventory schema",
                }
            )

    def test_mutable_defaults_are_isolated(self) -> None:
        first = QuestionInventory()
        second = QuestionInventory()

        first.questions.append(
            QuestionDefinition(question_id="one", topic_id="topic")
        )

        self.assertEqual(len(first.questions), 1)
        self.assertEqual(second.questions, [])

    def test_foundation_does_not_publish_a_populated_inventory(self) -> None:
        self.assertFalse(hasattr(schema_module, "QUESTION_INVENTORY"))


if __name__ == "__main__":
    unittest.main()
