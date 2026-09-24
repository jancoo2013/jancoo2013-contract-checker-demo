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
from research.question_engine.expert_memory.validate_real_contract_inventory import (
    read as read_real_inventory, validate as validate_real_inventory,
)
from research.question_engine.expert_memory.validate_real_contract_coverage import (
    ROOT as COVERAGE_ROOT, SOURCE_PATHS as COVERAGE_SOURCES,
    DATA as COVERAGE_DATA, read as read_real_coverage,
    validate as validate_real_coverage,
)
from research.question_engine.expert_memory.validate_real_contract_template_split import (
    DATA as SPLIT_DATA, read as read_template_split,
    validate as validate_template_split,
)
from research.question_engine.expert_memory.validate_contract_001_deep_review import (
    DATA as DEEP_DATA, GOLD as DEEP_GOLD, META as DEEP_META,
    SPLIT as DEEP_SPLIT, read as read_deep,
    validate as validate_deep,
)
from research.question_engine.expert_memory.validate_contract_001_statutory_crosschecks import (
    DATA as STAT_DATA, GOLD as STAT_GOLD, OVERLAY as STAT_OVERLAY,
    read as read_stat, validate as validate_stat,
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


class PrivateLeaseInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = read_real_inventory()

    def rejects(self, edit, message: str) -> None:
        data = deepcopy(self.inventory)
        edit(data)
        with self.assertRaisesRegex(ValueError, message):
            validate_real_inventory(data)

    def test_sanitized_seven_groups(self) -> None:
        validate_real_inventory(self.inventory)
        self.assertEqual(len(self.inventory["contracts"]), 7)
        self.assertFalse(self.inventory["raw_sha256_values_persisted"])

    def test_reject_private_filename_field(self) -> None:
        self.rejects(lambda d: d["contracts"][0].update(
            original_filename="never_commit.pdf"),
            "unexpected private original identifier")

    def test_reject_false_original_to_gold_link(self) -> None:
        self.rejects(lambda d: d["prior_sanitized_assets"].update(
            fixture_to_private_pdf_match="VERIFIED"), "linkage promoted")

    def test_reject_expert_coverage_without_analysis(self) -> None:
        self.rejects(lambda d: d["contracts"][0].update(
            mechanism_coverage="COMPLETE"), "promoted without verification")

    def test_reject_exaggerated_duplicate_count(self) -> None:
        self.rejects(lambda d: d.update(
            confirmed_byte_identical_extra_copy_count=5),
            "local duplicate evidence mismatch")

    def test_reject_persistent_source_hashes(self) -> None:
        self.rejects(lambda d: d["privacy_gate"].update(
            original_file_hashes_committed=True),
            "private source data may not be committed")


class SanitizedRealContractCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = read_real_coverage(COVERAGE_DATA)
        cls.evidence = {k: COVERAGE_ROOT / v for k, v
                        in COVERAGE_SOURCES.items()}
        cls.matrix = read_real_coverage(cls.evidence["aggregate_matrix"])
        cls.inventory = read_real_coverage(cls.evidence["private_inventory"])
        cls.meta = read_real_coverage(cls.evidence["golden_metadata"])
        cls.gold_text = cls.evidence["golden_fixture"].read_text(encoding="utf-8")

    def rejects(self, edit, pattern: str) -> None:
        changed = deepcopy(self.data)
        edit(changed)
        with self.assertRaisesRegex(ValueError, pattern):
            validate_real_coverage(changed, self.matrix, self.inventory,
                                   self.meta, self.gold_text)

    def test_coverage_sources_stay_separate(self) -> None:
        validate_real_coverage(self.data, self.matrix, self.inventory,
                               self.meta, self.gold_text)
        self.assertEqual(len(self.data["mechanisms"]), 13)
        self.assertEqual(len(self.data["private_groups"]), 7)

    def test_golden_original_link_is_unknown(self) -> None:
        self.rejects(lambda d: d["linkage"].update(
            golden_to_inventory="RC07"), "source identity inferred")

    def test_aggregate_frequency_not_a_new_document_oracle(self) -> None:
        self.rejects(lambda d: d["mechanisms"][0].update(
            aggregate_seen=7), "aggregate research re-attributed")

    def test_absent_evidence_is_not_confirmed_absence(self) -> None:
        self.rejects(lambda d: next(x for x in d["mechanisms"]
            if x["id"] == "shared_meter_accounting").update(
            golden_status="EVIDENCED_IN_SANITIZED_FIXTURE"),
            "unreviewed golden fixture claim")

    def test_claim_requires_real_printed_clause(self) -> None:
        self.rejects(lambda d: d["mechanisms"][0].update(
            golden_clause_ids=["25"]), "unreviewed golden fixture claim")

    def test_cross_clause_check_requires_locators(self) -> None:
        self.rejects(lambda d: d["golden_cross_clause_checks"][0].update(
            clauses=["3", "25"]), "cross-clause question lacks")

    def test_unread_private_contract_cannot_be_promoted(self) -> None:
        self.rejects(lambda d: d["private_groups"][0].update(
            coverage="EVIDENCED"), "private contract coverage")

    def test_holdout_not_selected_from_unverified_templates(self) -> None:
        self.rejects(lambda d: d["private_groups"][0].update(
            cohort="HOLDOUT"), "private contract coverage")

    def test_no_gold_or_external_real_contract_runs(self) -> None:
        self.rejects(lambda d: d["policy"].update(eligible_gold=True),
                     "Gold or evaluation boundary relaxed")


class RealContractTemplateSplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = read_template_split(SPLIT_DATA)
        cls.inventory = read_template_split(
            BASE / "real_contract_inventory_v1.json")
        cls.coverage = read_template_split(
            BASE / "real_contract_coverage_v1.json")
        cls.gold_meta = read_template_split(
            BASE.parents[2] /
            "research/question_engine/golden_contracts/contract_001.meta.json")

    def rejects(self, edit, pattern: str) -> None:
        changed = deepcopy(self.data)
        edit(changed)
        with self.assertRaisesRegex(ValueError, pattern):
            validate_template_split(changed, self.inventory, self.coverage,
                                    self.gold_meta)

    def test_confirmed_families_and_disjoint_cohorts(self) -> None:
        validate_template_split(self.data, self.inventory, self.coverage,
                                self.gold_meta)
        self.assertEqual(len(self.data["families"]), 4)
        self.assertEqual(self.data["cohort_boundary"]["development_families"],
                         ["TF_A", "TF_B"])
        self.assertEqual(
            self.data["cohort_boundary"]["independent_test_families"],
            ["TF_C", "TF_D"])

    def test_reject_cross_family_duplicate(self) -> None:
        self.rejects(lambda d: d["families"][2]["groups"].append("RC04"),
                     "confirmed family or cohort assignment changed")

    def test_reject_holdout_leakage(self) -> None:
        self.rejects(lambda d: d["cohort_boundary"][
            "development_families"].append("TF_C"),
            "family-disjoint cohort boundary violated")

    def test_reject_unproven_golden_link(self) -> None:
        self.rejects(lambda d: d["golden_fixture"].update(
            linked_family="TF_D"), "unverified Golden Fixture identity")

    def test_reject_attributed_prior_research(self) -> None:
        self.rejects(lambda d: d["prior_two_contract_research"].update(
            original_groups=["RC02", "RC05"]),
            "prior two-contract originals wrongly attributed")

    def test_reject_private_identifier_or_sidecar_evidence(self) -> None:
        self.rejects(lambda d: d["privacy"].update(
            sidecar_report_used_as_evidence=True),
            "private source data or provider use promoted")


class Contract001DeepReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.review = read_deep(DEEP_DATA)
        cls.printed = DEEP_GOLD.read_text(encoding="utf-8")
        cls.meta = read_deep(DEEP_META)
        cls.split = read_deep(DEEP_SPLIT)

    def rejects(self, edit, fragment: str) -> None:
        changed = deepcopy(self.review)
        edit(changed)
        with self.assertRaisesRegex(ValueError, fragment):
            validate_deep(changed, self.printed, self.meta, self.split)

    def test_fifteen_human_style_mechanisms_source_anchored(self) -> None:
        validate_deep(self.review, self.printed, self.meta, self.split)
        self.assertEqual(len(self.review["mechanisms"]), 15)
        self.assertGreaterEqual(
            sum(len(x["quotes"]) for x in self.review["mechanisms"]), 55)
        self.assertEqual(self.review["private_original_link"],
                         "UNKNOWN_EXCEPT_RC07_EXCLUDED")

    def test_critical_pass_adds_requested_cross_clause_mechanisms(self) -> None:
        by_id = {x["id"]: x for x in self.review["mechanisms"]}
        self.assertEqual(
            set(by_id["property_inventory_handover_return"]["clauses"]),
            {"3", "9", "12", "14"})
        self.assertEqual(
            set(by_id["arnona_signature_deadline"]["clauses"]),
            {"3", "5", "6"})
        self.assertEqual(
            set(by_id["agreed_occupants_general_and_specific"]["clauses"]),
            {"7", "24"})

    def test_early_exit_holdover_and_security_are_not_collapsed(self) -> None:
        by_id = {x["id"]: x for x in self.review["mechanisms"]}
        self.assertIn("Ранний выезд по §8 отличается",
                      by_id["early_exit_transfer_and_remaining_rent"]
                      ["second_pass"])
        self.assertIn("§17 относится к задержке освобождения",
                      by_id["moveout_condition_holdover_security"]
                      ["second_pass"])
        self.assertIn("Реализация чека по §11",
                      by_id["security_cheque_not_bank_guarantee"]
                      ["second_pass"])

    def test_repair_setoff_retains_all_written_preconditions(self) -> None:
        repair = next(x for x in self.review["mechanisms"]
                      if x["id"] == "repair_setoff_vs_default")
        quotes = {q["quote"] for q in repair["quotes"]}
        self.assertIn("אשר החובה לתקנם תהא עליו כמשכיר", quotes)
        self.assertIn("תוך זמן סביר מיום דרישת השוכר", quotes)
        self.assertIn("לקזז את ההוצאה מדמי השכירות", quotes)

    def test_missing_8b_is_only_an_original_comparison_gate(self) -> None:
        check = self.review["integrity_checks"][0]
        self.assertEqual(check["status"], "ORIGINAL_COMPARISON_REQUIRED")
        self.assertIn("8. א.", self.printed)
        self.assertNotIn("8. ב.", self.printed)
        self.assertIn("особенностью бланка", check["avoid"])

    def test_reject_invented_hebrew_quote(self) -> None:
        self.rejects(lambda d: d["mechanisms"][0]["quotes"][0].update(
            quote="משפט שלא מופיע בחוזה המקורי"),
            "fabricated or misattributed Hebrew")

    def test_reject_quote_assigned_to_wrong_clause(self) -> None:
        self.rejects(lambda d: d["mechanisms"][0]["quotes"][0].update(
            clause="17"), "fabricated or misattributed Hebrew")

    def test_reject_editorial_blank_marker_as_quote(self) -> None:
        self.rejects(lambda d: d["mechanisms"][0]["quotes"][0].update(
            quote="[BLANK_OR_MISSING_VALUE_IN_SOURCE]"),
            "fabricated or misattributed Hebrew")

    def test_reject_omitted_party_payment_mechanism(self) -> None:
        self.rejects(lambda d: d["mechanisms"].__setitem__(
            slice(None), [x for x in d["mechanisms"]
                          if x["id"] != "individual_payer_collective_tenant"]),
            "missing or duplicate human-style")

    def test_liability_mechanism_requires_flat_defect_clause(self) -> None:
        def remove_clause_12(data: dict) -> None:
            item = next(x for x in data["mechanisms"]
                        if x["id"] == "tenant_goods_and_third_party_loss")
            item["clauses"].remove("12")
            item["quotes"] = [q for q in item["quotes"]
                              if q["clause"] != "12"]
        self.rejects(remove_clause_12, "invalid clause links")

    def test_reject_premature_golden_family_link(self) -> None:
        self.rejects(lambda d: d.update(
            private_original_link="TF_A"), "unverified review promoted")

    def test_reject_unreviewed_legal_gold(self) -> None:
        self.rejects(lambda d: d.update(
            scope="VERIFIED_LEGAL_GOLD"), "unverified review promoted")

    def test_reject_missing_second_pass(self) -> None:
        self.rejects(lambda d: d["mechanisms"][4].update(
            second_pass=""), "missing independent reasoning")

    def test_reject_dropped_clause_sequence_check(self) -> None:
        self.rejects(lambda d: d.update(integrity_checks=[]),
                     "missing clause-sequence integrity check")

    def test_reject_suppressed_missing_appendix(self) -> None:
        self.rejects(lambda d: d["mechanisms"][5].update(
            gaps=[]), "lack of explicit uncertainty")

    def test_reject_dropped_legal_uncertainty_boundary(self) -> None:
        self.rejects(lambda d: d["scope_limits"].remove(
            "No assumption of live statutory enforceability or case outcome"),
            "missing evidence boundary")


class Contract001StatutoryCrosscheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = read_stat(STAT_DATA)
        cls.gold = STAT_GOLD.read_text(encoding="utf-8")
        cls.overlay = read_stat(STAT_OVERLAY)

    def rejects(self, edit, error: str) -> None:
        data = deepcopy(self.data)
        edit(data)
        with self.assertRaisesRegex(ValueError, error):
            validate_stat(data, self.gold, self.overlay)

    def test_three_dated_research_hypotheses(self) -> None:
        validate_stat(self.data, self.gold, self.overlay)
        self.assertEqual(len(self.data["checks"]), 3)
        self.assertFalse(self.data["use"]["expert_case_gold"])

    def test_no_autofilled_option_notice(self) -> None:
        self.rejects(lambda d: d["checks"][0]["failure_modes"].remove(
            "AUTOFILL_60_DAYS_INTO_BLANK"), "adversarial error coverage")

    def test_urgent_repair_exception_cannot_disappear(self) -> None:
        self.rejects(lambda d: d["checks"][1]["failure_modes"].remove(
            "DENY_EMERGENCY_SELF_HELP_FOR_LACK_OF_PRIOR_DEMAND"),
            "adversarial error coverage")

    def test_cheque_not_exempt_from_all_security_rules(self) -> None:
        self.rejects(lambda d: d["checks"][2]["failure_modes"].remove(
            "EXEMPT_CHEQUE_FROM_ALL_25י_SUBSECTIONS"),
            "adversarial error coverage")

    def test_reject_early_2026_effective_date(self) -> None:
        self.rejects(lambda d: d["source_registry"]["law_2026"].update(
            effective_from="2026-03-31"), "effective date changed")

    def test_reject_fabricated_contract_quote(self) -> None:
        self.rejects(lambda d: d["checks"][0]["contract_quotes"][0].update(
            text="לא מופיע בחוזה"), "fabricated or redacted quote")

    def test_reject_premature_expert_gold(self) -> None:
        self.rejects(lambda d: d["use"].update(expert_case_gold=True),
                     "promoted to runtime")

    def test_reject_lost_statutory_scope_gate(self) -> None:
        self.rejects(lambda d: d["global_gates"].remove(
            "RESIDENTIAL_SCOPE_AND_25טו_EXCLUSIONS"),
            "applicability gate lost")

    def test_reject_substituted_statutory_section(self) -> None:
        self.rejects(lambda d: d["checks"][0]["legal_sources"][0][
            "sections"].__setitem__(0, "NOT_A_STATUTE_SECTION"),
            "unverified legal source")

    def test_reject_duplicate_statutory_section(self) -> None:
        self.rejects(lambda d: d["checks"][1]["legal_sources"][0][
            "sections"].__setitem__(0, "9(a)"),
            "unverified legal source")

    def test_reject_duplicate_legal_source(self) -> None:
        self.rejects(lambda d: d["checks"][2]["legal_sources"].append(
            deepcopy(d["checks"][2]["legal_sources"][0])),
            "unverified legal source")


if __name__ == "__main__":
    unittest.main()
