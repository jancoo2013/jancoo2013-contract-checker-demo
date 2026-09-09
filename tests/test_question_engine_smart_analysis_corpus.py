"""Focused integrity tests for the sanitized smart-analysis corpus v1."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

# Oracle v2 correction in progress.

CORPUS_PATH = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "question_engine"
    / "smart_analysis_corpus_v1.json"
)


class SmartAnalysisCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        cls.cases = cls.corpus["cases"]

    def test_schema_and_case_identity(self) -> None:
        self.assertEqual(self.corpus["schema_version"], 1)
        self.assertGreaterEqual(len(self.cases), 12)
        self.assertLessEqual(len(self.cases), 15)
        case_ids = [case["case_id"] for case in self.cases]
        self.assertEqual(len(case_ids), len(set(case_ids)))

    def test_every_case_has_bounded_sanitized_oracle_shape(self) -> None:
        expected_keys = {
            "presence",
            "value_status",
            "evidence_status",
            "source_status",
            "finding_outcome",
            "mechanism_ids",
            "must_link_refs",
        }
        allowed_basis = {
            "synthetic_from_observed_pattern",
            "synthetic_boundary_case",
        }
        for case in self.cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertIn(case["basis"], allowed_basis)
                self.assertTrue(case["target_question_ids"])
                self.assertTrue(case["clauses"])
                self.assertEqual(set(case["expected"]), expected_keys)
                for question_id in case["target_question_ids"]:
                    self.assertRegex(
                        question_id,
                        r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$",
                    )

                refs = [clause["ref"] for clause in case["clauses"]]
                self.assertEqual(len(refs), len(set(refs)))
                self.assertTrue(set(case["expected"]["must_link_refs"]).issubset(refs))

                mechanism_ids = case["expected"]["mechanism_ids"]
                self.assertEqual(len(mechanism_ids), len(set(mechanism_ids)))

    def test_resolution_outcomes_cover_confirmed_narrowed_and_cleared(self) -> None:
        outcomes = {
            case["expected"]["finding_outcome"]
            for case in self.cases
            if case["expected"]["finding_outcome"] is not None
        }
        self.assertTrue({"CONFIRMED", "NARROWED", "CLEARED"}.issubset(outcomes))

    def test_blank_lifecycle_pair_is_explicit(self) -> None:
        blank_cases = {
            case["case_id"]: case
            for case in self.cases
            if case["expected"]["value_status"] == "BLANK"
        }
        template = blank_cases["template_blank_security_amount"]
        executed = blank_cases["executed_blank_security_amount"]
        self.assertEqual(template["lifecycle"], "TEMPLATE")
        self.assertEqual(executed["lifecycle"], "EXECUTED")
        self.assertEqual(template["clauses"], executed["clauses"])

    def test_handwriting_is_never_reconstructed(self) -> None:
        handwriting = [
            case
            for case in self.cases
            if any(
                "[HANDWRITING_REDACTED]" in clause["text_he"]
                for clause in case["clauses"]
            )
        ]
        self.assertTrue(handwriting)
        for case in handwriting:
            self.assertEqual(
                case["expected"]["evidence_status"],
                "HANDWRITING_DEPENDENCY",
            )
            self.assertEqual(case["expected"]["value_status"], "UNKNOWN")

    def test_corpus_contains_required_semantic_stress_cases(self) -> None:
        by_id = {case["case_id"]: case for case in self.cases}

        self.assertEqual(
            len(
                by_id["multiple_security_instruments_keep_identity"]["expected"][
                    "mechanism_ids"
                ]
            ),
            2,
        )
        self.assertEqual(
            by_id["missing_security_instrument_dependency"]["expected"][
                "evidence_status"
            ],
            "MISSING_DEPENDENCY",
        )
        self.assertEqual(
            by_id["contradictory_party_reference_in_security_clause"]["expected"][
                "source_status"
            ],
            "CONTRADICTORY",
        )
        self.assertEqual(
            by_id["early_exit_route_absent_is_material"]["expected"]["presence"],
            "ABSENT",
        )
        self.assertGreaterEqual(
            len(
                by_id["security_mechanism_split_across_distant_clauses"][
                    "expected"
                ]["must_link_refs"]
            ),
            3,
        )

    def test_fixture_contains_no_obvious_contact_or_identity_payload(self) -> None:
        serialized = json.dumps(self.corpus, ensure_ascii=False)
        self.assertNotIn("@", serialized)
        self.assertNotRegex(serialized, r"\b\d{9}\b")
        self.assertNotIn("תעודת זהות", serialized)
        self.assertNotIn("מספר טלפון", serialized)


if __name__ == "__main__":
    unittest.main()
