"""Focused integrity tests for smart-analysis corpus oracle v2."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from contract_checker.question_engine import (
    DocumentLifecycle,
    EvidenceStatus,
    FindingOutcome,
    PresenceStatus,
    SourceStatus,
    ValueStatus,
)
from contract_checker.question_engine.inventory import (
    CONDITION_DEFECTS_CORE_INVENTORY_V1,
    EARLY_EXIT_CORE_INVENTORY_V1,
    ECONOMIC_CORE_INVENTORY_V1,
    FINANCIAL_SANCTIONS_CORE_INVENTORY_V1,
    OPTION_RENEWAL_CORE_INVENTORY_V1,
    TERMINATION_CURE_CORE_INVENTORY_V1,
)


CORPUS_PATH = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "question_engine"
    / "smart_analysis_corpus_v1.json"
)
INVENTORIES = (
    ECONOMIC_CORE_INVENTORY_V1,
    EARLY_EXIT_CORE_INVENTORY_V1,
    FINANCIAL_SANCTIONS_CORE_INVENTORY_V1,
    CONDITION_DEFECTS_CORE_INVENTORY_V1,
    TERMINATION_CURE_CORE_INVENTORY_V1,
    OPTION_RENEWAL_CORE_INVENTORY_V1,
)
STATE_KEYS = {"presence", "value", "evidence", "source"}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class SmartAnalysisCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        cls.cases = cls.corpus["cases"]
        cls.questions = {
            question.question_id: question
            for inventory in INVENTORIES
            for question in inventory.questions
        }
        cls.defaults = cls.corpus["state_defaults"]

    @staticmethod
    def _input_refs(case: dict[str, object]) -> set[str]:
        refs = {item["ref"] for item in case["clauses"]}
        refs.update(item["ref"] for item in case.get("documents", ()))
        refs.update(item["ref"] for item in case.get("redactions", ()))
        refs.add("@scope")
        return refs

    @staticmethod
    def _assertions(case: dict[str, object], question_id: str, field: str) -> list[dict[str, object]]:
        return [
            item
            for item in case["assertions"]
            if item["question_id"] == question_id and item["field"] == field
        ]

    def _effective_state(self, assertion: dict[str, object]) -> dict[str, str]:
        state = dict(self.defaults)
        state.update(assertion.get("state", {}))
        return state

    def test_schema_case_identity_and_size(self) -> None:
        self.assertEqual(self.corpus["schema_version"], 2)
        self.assertEqual(len(self.cases), 16)
        self.assertEqual(set(self.defaults), STATE_KEYS)
        case_ids = [case["case_id"] for case in self.cases]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertTrue(all(ID_PATTERN.fullmatch(case_id) for case_id in case_ids))

    def test_assertion_targets_exist_and_match_inventory_domain(self) -> None:
        for case in self.cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertTrue(case["assertions"])
                for assertion in case["assertions"]:
                    question_id = assertion["question_id"]
                    self.assertIn(question_id, self.questions)
                    self.assertEqual(self.questions[question_id].domain, case["domain"])
                    self.assertIn(assertion["field"], self.questions[question_id].answer_fields)

    def test_sparse_assertions_are_subject_specific_and_state_valid(self) -> None:
        allowed = {
            "presence": {item.value for item in PresenceStatus},
            "value": {item.value for item in ValueStatus},
            "evidence": {item.value for item in EvidenceStatus},
            "source": {item.value for item in SourceStatus},
        }
        allowed_lifecycle = {item.value for item in DocumentLifecycle}
        for case in self.cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertIn(case["lifecycle"], allowed_lifecycle)
                refs = self._input_refs(case)
                keys = set()
                for assertion in case["assertions"]:
                    mechanism_id = assertion.get("mechanism_id")
                    if mechanism_id is not None:
                        self.assertRegex(mechanism_id, ID_PATTERN)
                    key = (assertion["question_id"], mechanism_id, assertion["field"])
                    self.assertNotIn(key, keys)
                    keys.add(key)
                    state = self._effective_state(assertion)
                    self.assertEqual(set(state), STATE_KEYS)
                    for axis, values in allowed.items():
                        self.assertIn(state[axis], values)
                    self.assertTrue(set(assertion["refs"]).issubset(refs))

    def test_absent_assertions_require_declared_complete_scope(self) -> None:
        for case in self.cases:
            complete_for = set(case.get("complete_for", ()))
            for assertion in case["assertions"]:
                if self._effective_state(assertion)["presence"] == PresenceStatus.ABSENT.value:
                    self.assertIn(assertion["question_id"], complete_for)
                    self.assertIn("@scope", assertion["refs"])

    def test_resolution_has_explicit_candidate_and_supported_refs(self) -> None:
        allowed_outcomes = {item.value for item in FindingOutcome}
        outcomes = set()
        for case in self.cases:
            resolution = case.get("resolution")
            candidate = case.get("candidate")
            if resolution is None:
                self.assertIsNone(candidate)
                continue
            self.assertIsNotNone(candidate)
            refs = self._input_refs(case)
            self.assertRegex(candidate["candidate_kind"], ID_PATTERN)
            self.assertTrue(candidate["claim"].strip())
            self.assertTrue(set(candidate["subject_refs"]).issubset(refs))
            self.assertIn(resolution["outcome"], allowed_outcomes)
            self.assertTrue(set(resolution["reviewed_refs"]).issubset(refs))
            outcomes.add(resolution["outcome"])
        self.assertTrue({"CONFIRMED", "NARROWED", "CLEARED"}.issubset(outcomes))

    def test_package_and_handwriting_signals_are_not_fake_hebrew_clauses(self) -> None:
        redaction_cases = 0
        document_cases = 0
        for case in self.cases:
            redaction_cases += bool(case.get("redactions"))
            document_cases += bool(case.get("documents"))
            for clause in case["clauses"]:
                text = clause["text_he"]
                self.assertNotIn("HANDWRITING_REDACTED", text)
                self.assertNotIn("לא צורף", text)
                self.assertNotIn("MISSING", text)
        self.assertGreaterEqual(redaction_cases, 1)
        self.assertGreaterEqual(document_cases, 3)

    def test_blank_lifecycle_pair_keeps_same_wording_but_distinct_meaning(self) -> None:
        by_id = {case["case_id"]: case for case in self.cases}
        template = by_id["template_blank_security_amount"]
        executed = by_id["executed_blank_security_amount"]
        self.assertEqual(template["clauses"], executed["clauses"])
        self.assertEqual(template["lifecycle"], "TEMPLATE")
        self.assertEqual(executed["lifecycle"], "EXECUTED")
        self.assertNotIn("resolution", template)
        self.assertEqual(executed["resolution"]["outcome"], "CONFIRMED")

    def test_multi_instrument_identity_and_scoped_notice_are_scored(self) -> None:
        by_id = {case["case_id"]: case for case in self.cases}
        identity = by_id["multiple_security_instruments_keep_identity"]
        amounts = self._assertions(identity, "security.instrument_amounts", "instrument_amounts")
        self.assertEqual(
            {item["mechanism_id"]: item["expected"] for item in amounts},
            {"security_1": 10000, "security_2": 30000},
        )
        linked = by_id["security_mechanism_split_with_distractors"]
        notice = self._assertions(linked, "security.realization_chain", "notice_required")
        self.assertEqual(
            {item["mechanism_id"]: item["expected"] for item in notice},
            {"security_1": True, "security_2": False},
        )

    def test_corrected_contradiction_and_early_exit_oracles(self) -> None:
        by_id = {case["case_id"]: case for case in self.cases}
        conflict = by_id["exclusive_completion_authority_conflict"]
        role = self._assertions(conflict, "security.completion_authority", "completion_authority_role")[0]
        self.assertEqual(self._effective_state(role)["source"], "CONTRADICTORY")
        early_exit = by_id["early_exit_route_absent_is_material"]
        liability = self._assertions(early_exit, "early_exit.continuing_liability", "continuing_rent_liability")[0]
        route = self._assertions(early_exit, "early_exit.replacement_route", "replacement_route_present")[0]
        self.assertEqual(self._effective_state(liability)["presence"], "PRESENT")
        self.assertTrue(liability["expected"])
        self.assertEqual(self._effective_state(route)["presence"], "ABSENT")
        self.assertFalse(route["expected"])

    def test_linking_case_has_distractors_and_does_not_reward_all_refs(self) -> None:
        by_id = {case["case_id"]: case for case in self.cases}
        case = by_id["security_mechanism_split_with_distractors"]
        clause_refs = {item["ref"] for item in case["clauses"]}
        used_refs = {ref for assertion in case["assertions"] for ref in assertion["refs"]}
        self.assertTrue(used_refs < clause_refs)
        self.assertGreaterEqual(len(clause_refs - used_refs), 3)

    def test_fixture_contains_no_obvious_contact_or_identity_payload(self) -> None:
        serialized = json.dumps(self.corpus, ensure_ascii=False)
        self.assertNotIn("@example", serialized)
        self.assertNotRegex(serialized, r"\b\d{9}\b")
        self.assertNotIn("תעודת זהות", serialized)
        self.assertNotIn("מספר טלפון", serialized)


if __name__ == "__main__":
    unittest.main()
