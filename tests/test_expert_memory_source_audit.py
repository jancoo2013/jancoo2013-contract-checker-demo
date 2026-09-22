"""Adversarial checks for the offline, non-authoritative source audit packet."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from research.question_engine.expert_memory.validate_source_audit_packet import (
    BASE, read, validate,
)


class SourceAuditPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = read(BASE / "source_audit_packet_v1.json")
        cls.cases = read(BASE / "expert_cases_v1.json")

    def rejects(self, edit, message: str) -> None:
        data = deepcopy(self.packet)
        edit(data)
        with self.assertRaisesRegex(ValueError, message):
            validate(data, self.cases)

    def test_six_leads_and_five_unverified_cases_validate(self) -> None:
        validate(self.packet, self.cases)
        self.assertEqual(len(self.packet["sources"]), 6)
        self.assertEqual(len(self.packet["case_links"]), 5)
        self.assertTrue(all(x["review"] ==
            "NEEDS_PRIMARY_SOURCE_AND_SPECIALIST_REVIEW"
            for x in self.packet["claims"]))

    def test_all_original_case_ids_are_linked(self) -> None:
        expected = {x["case_id"] for x in self.cases["cases"]}
        actual = {x["case_id"] for x in self.packet["case_links"]}
        self.assertEqual(expected, actual)

    def test_duplicate_official_source_is_rejected(self) -> None:
        self.rejects(lambda d: d["sources"].append(deepcopy(d["sources"][0])),
                     "duplicate or invalid id")

    def test_unknown_source_in_claim_is_rejected(self) -> None:
        self.rejects(lambda d: d["claims"][0].update(source_id="invented_law"),
                     "claim: unknown source")

    def test_unknown_claim_in_case_link_is_rejected(self) -> None:
        self.rejects(lambda d: d["case_links"][0]["claim_ids"].append("fabricated"),
                     "unknown, duplicated or missing references")

    def test_missing_case_link_is_rejected(self) -> None:
        self.rejects(lambda d: d["case_links"].pop(), "missing ExpertCase coverage")

    def test_cross_case_duplicate_link_is_rejected(self) -> None:
        self.rejects(lambda d: d["case_links"][1].update(
            case_id=d["case_links"][0]["case_id"]), "duplicate case link")

    def test_search_index_snippet_cannot_become_full_primary_text(self) -> None:
        self.rejects(lambda d: d["sources"][3].update(
            access_level="PRIMARY_TEXT_READ"), "source authority/access mismatch")

    def test_government_proposal_cannot_become_enacted_law(self) -> None:
        self.rejects(lambda d: d["sources"][2].update(
            kind="ENACTED_HISTORICAL"), "source authority/access mismatch")

    def test_proposal_cannot_be_used_as_case_authority(self) -> None:
        self.rejects(lambda d: d["case_links"][0]["claim_ids"].append(
            "proposed_2026_guarantors"), "cannot treat metadata or proposal")

    def test_claim_cannot_be_promoted_to_expert_verified(self) -> None:
        self.rejects(lambda d: d["claims"][0].update(
            review="EXPERT_VERIFIED"), "promoted without independent verification")

    def test_claim_needs_explicit_unsupported_extrapolation(self) -> None:
        self.rejects(lambda d: d["claims"][0].update(
            does_not_support=""), "missing does_not_support")

    def test_unresolved_future_amendment_cannot_disappear(self) -> None:
        self.rejects(lambda d: d["unresolved"][0].update(
            source_ids=["knesset_2017_amendment"]),
                     "index/legislation gaps must remain explicit")

    def test_non_official_network_source_is_rejected(self) -> None:
        self.rejects(lambda d: d["sources"][0].update(
            url="https://not-official.example.com/statute"),
                     "unapproved source URL")

    def test_future_publication_is_rejected(self) -> None:
        self.rejects(lambda d: d["sources"][0].update(
            source_date="2027-01-01"), "publication date is in the future")

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dup.json"
            path.write_text('{"schema_version": 1, "schema_version": 2}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON field"):
                read(path)


if __name__ == "__main__":
    unittest.main()
