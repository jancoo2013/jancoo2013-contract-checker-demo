"""Adversarial checks for the offline, non-authoritative source audit packet."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from research.question_engine.expert_memory.validate_source_audit_packet import (
    BASE, read, validate, validate_procedure_edition,
)
from research.question_engine.expert_memory.validate_security_cheque_judgments import (
    read as read_case_law, validate as validate_case_law,
)


class SourceAuditPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = read(BASE / "source_audit_packet_v1.json")
        cls.cases = read(BASE / "expert_cases_v1.json")
        cls.procedure = read(BASE / "authority_cheque_procedure_2025_06_29_v1.json")
        cls.overlay = read(BASE.parents[2] / "docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2026_V1.json")

    def rejects(self, edit, message: str) -> None:
        data = deepcopy(self.packet)
        edit(data)
        with self.assertRaisesRegex(ValueError, message):
            validate(data, self.cases, self.overlay)

    def test_seven_leads_and_five_unverified_cases_validate(self) -> None:
        validate(self.packet, self.cases, self.overlay)
        self.assertEqual(len(self.packet["sources"]), 7)
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
        self.rejects(lambda d: d["sources"][4].update(
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

    def test_enacted_amendment_is_source_only(self) -> None:
        self.assertEqual(self.overlay["amending_law"]["publication_issue"], 3510)
        self.assertFalse(self.overlay["usage"]["production_runtime_wired"])

    def test_enacted_claim_can_be_linked_as_non_authoritative_context(self) -> None:
        data = deepcopy(self.packet)
        self.assertEqual(data["case_links"][0]["relation"],
                         "LEGAL_CONTEXT_NOT_CASE_ORACLE")
        data["case_links"][0]["claim_ids"].append(
            "enacted_2026_other_guarantee_providers")
        validate(data, self.cases, self.overlay)

    def test_enacted_source_cannot_be_promoted_to_original_read(self) -> None:
        self.rejects(lambda d: d["sources"][3].update(
            access_level="PRIMARY_TEXT_READ"),
                     "source authority/access mismatch")

    def test_enacted_claim_cannot_be_relabelled_historical(self) -> None:
        self.rejects(lambda d: d["claims"][5].update(
            support="DIRECT_HISTORICAL_TEXT"),
                     "unsupported source authority or review level")

    def test_malformed_commencement_metadata_is_rejected(self) -> None:
        bad = deepcopy(self.overlay)
        bad["commencement"]["effective_from"] = "not-a-date"
        with self.assertRaisesRegex(ValueError, "invalid date"):
            validate(self.packet, self.cases, bad)

    def test_original_official_download_cannot_be_claimed_without_evidence(self) -> None:
        bad = deepcopy(self.overlay)
        bad["amending_law"]["original_official_pdf_fetch"] = "VERIFIED_BYTES"
        with self.assertRaisesRegex(ValueError, "Gazette locator or access"):
            validate(self.packet, self.cases, bad)

    def test_mismatched_official_pdf_is_rejected(self) -> None:
        bad = deepcopy(self.overlay)
        bad["amending_law"]["official_publication_pdf"] = (
            "https://fs.knesset.gov.il/not-the-enacted-law.pdf")
        with self.assertRaisesRegex(ValueError, "provenance mismatch"):
            validate(self.packet, self.cases, bad)

    def test_procedure_index_only(self) -> None:
        validate_procedure_edition(self.procedure, self.packet)

    def test_procedure_is_not_full_text(self) -> None:
        value = deepcopy(self.procedure)
        value["full_pdf_retrieved"] = True
        with self.assertRaises(ValueError):
            validate_procedure_edition(value, self.packet)

    def test_procedure_gaps_must_remain(self) -> None:
        value = deepcopy(self.procedure)
        value["unverified_questions"].pop()
        with self.assertRaises(ValueError):
            validate_procedure_edition(value, self.packet)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dup.json"
            path.write_text('{"schema_version": 1, "schema_version": 2}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON field"):
                read(path)


class FiveJudgmentResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cohort = read_case_law()

    def rejects(self, edit, message: str) -> None:
        data = deepcopy(self.cohort)
        edit(data)
        with self.assertRaisesRegex(ValueError, message):
            validate_case_law(data)

    def test_five_real_dockets_with_boundaries(self) -> None:
        validate_case_law(self.cohort)
        self.assertEqual(len(self.cohort["cases"]), 5)
        self.assertEqual(sum(c["statutory_era"] == "POST_2017"
                             for c in self.cohort["cases"]), 2)
        self.assertFalse(self.cohort["gold_eligible"])

    def test_no_train_or_gold_upgrade(self) -> None:
        self.rejects(lambda d: d.update(training_eligible=True),
                     "promoted beyond research")
        self.rejects(lambda d: d.update(gold_eligible=True),
                     "promoted beyond research")

    def test_partial_judgment_cannot_acquire_an_invented_final_result(self) -> None:
        self.rejects(lambda d: d["cases"][3].update(
            disposition="SECURITY_NOTE_CLAIM_DISMISSED"),
            "unseen disposition promoted")

    def test_search_excerpt_cannot_be_relabelled_official_full_text(self) -> None:
        self.rejects(lambda d: d["cases"][1].update(
            access="OFFICIAL_FULL_COURT_FILE"),
            "source access or unseen disposition promoted")

    def test_historical_case_not_post_reform(self) -> None:
        self.rejects(lambda d: d["cases"][4].update(
            statutory_era="POST_2017"), "statutory-era mismatch")

    def test_court_facts_are_not_observed_model_failures(self) -> None:
        self.rejects(lambda d: d["cases"][0].update(
            error_origin="OBSERVED_MODEL_FAILURE"), "origin overstated")

    def test_unofficial_mirror_must_stay_on_pinned_host(self) -> None:
        self.rejects(lambda d: d["cases"][0].update(
            source_url="https://example.com/court.pdf"),
            "unapproved or malformed case-law mirror")

    def test_cannot_omit_original_court_file_review_gap(self) -> None:
        self.rejects(lambda d: d.update(gaps=[]), "gaps must be explicit")

    def test_no_unattributed_legal_holding(self) -> None:
        self.rejects(lambda d: d["cases"][0]["judicial_evidence"][0].update(
            locator=""), "missing traceable judicial evidence")

    def test_cannot_silently_replace_one_judgment(self) -> None:
        self.rejects(lambda d: d["cases"][4].update(
            docket="35226-02-20"), "duplicate/unknown docket")


if __name__ == "__main__":
    unittest.main()
