"""Regression checks for ExpertCase provenance and split integrity."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import unittest

from research.question_engine.expert_memory import validate_expert_cases as memory


HERE = Path(__file__).resolve().parents[1]
SCHEMA = HERE / "research/question_engine/expert_memory/expert_case_v1.schema.json"


class ExpertMemoryProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset, _ = memory.read_json(memory.SEED_PATH)
        cls.source, cls.raw_source = memory.read_json(memory.ROOT / memory.SOURCE_PATH)

    def invalid(self, mutation, message: str) -> None:
        dataset = deepcopy(self.dataset)
        mutation(dataset)
        with self.assertRaisesRegex(ValueError, message):
            memory.validate(dataset, self.source, self.raw_source)

    def test_five_unverified_synthetic_cases_validate(self) -> None:
        memory.validate(self.dataset, self.source, self.raw_source)
        self.assertEqual(len(self.dataset["cases"]), 5)
        self.assertEqual(
            {c["split"] for c in self.dataset["cases"]},
            {"train", "evaluation"},
        )
        self.assertTrue(all(
            c["error_origin"] == "CONSTRUCTED_WRONG_READING"
            and c["review"]["status"] == "UNVERIFIED"
            for c in self.dataset["cases"]
        ))

    def test_schema_matches_seed_envelope(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertEqual(set(self.dataset), set(schema["required"]))
        self.assertEqual(
            set(self.dataset["cases"][0]),
            set(schema["$defs"]["case"]["required"]),
        )

    def test_invented_clause_reference_is_rejected(self) -> None:
        self.invalid(lambda d: d["cases"][0]["corrected_reading"]["refs"].append("c999"),
                     "invented or misplaced")

    def test_tampered_sanitized_source_is_rejected(self) -> None:
        self.invalid(lambda d: d["cases"][0]["spans"][0].update(text_he="invented"),
                     "source spans differ")

    def test_cross_instrument_amount_migration_is_rejected(self) -> None:
        def mutate(d):
            facts = d["cases"][3]["facts"]
            cheque = next(f for f in facts
                          if f.get("mechanism_id") == "security_1"
                          and f["field"] == "instrument_amounts")
            cheque["expected"] = 30000
            cheque["refs"] = ["c4"]
        self.invalid(mutate, "fact value, mechanism or source refs differ")

    def test_boolean_provenance_cannot_be_replaced_by_zero(self) -> None:
        self.invalid(lambda d: d["cases"][0]["facts"][1].update(expected=0),
                     "fact value, mechanism or source refs differ")

    def test_cross_instrument_return_rule_link_is_rejected(self) -> None:
        def mutate(d):
            link = next(l for l in d["cases"][4]["links"]
                        if l["mechanism_id"] == "security_1"
                        and l["kind"] == "RETURN_RULE")
            link["to_ref"] = "c31"
        self.invalid(mutate, "unsupported or cross-instrument link")

    def test_duplicate_case_and_mechanism_ids_are_rejected(self) -> None:
        self.invalid(lambda d: d["cases"].append(deepcopy(d["cases"][0])),
                     "duplicate ExpertCase id")
        self.invalid(lambda d: d["cases"][3]["mechanisms"].append(
            deepcopy(d["cases"][3]["mechanisms"][0])), "duplicate/invalid mechanism id")

    def test_missing_or_duplicate_evidence_is_rejected(self) -> None:
        self.invalid(lambda d: d["cases"][0]["facts"][0].update(refs=[]),
                     "empty or invalid evidence refs|fact value")
        self.invalid(lambda d: d["cases"][1]["discriminator"]["refs"].append("c9"),
                     "duplicate evidence refs")

    def test_expert_promotion_without_independent_review_is_rejected(self) -> None:
        def mutate(d):
            d["cases"][0]["review"] = {
                "status": "EXPERT_VERIFIED",
                "reviewer_ref": "model_output",
                "review_evidence_refs": ["invented_attestation"],
            }
        self.invalid(mutate, "cannot claim independent expert review")

    def test_constructed_example_cannot_claim_observed_model_error(self) -> None:
        self.invalid(lambda d: d["cases"][0].update(error_origin="OBSERVED_MODEL_ERROR"),
                     "cannot claim an observed model error")

    def test_template_family_leakage_is_rejected(self) -> None:
        self.invalid(lambda d: d["cases"][1].update(split="evaluation"),
                     "template family leaks")

    def test_duplicate_source_case_across_splits_is_rejected(self) -> None:
        def mutate(d):
            d["cases"][3]["source_case_id"] = d["cases"][0]["source_case_id"]
        self.invalid(mutate, "missing or reused source case")

    def test_discriminator_must_show_disambiguating_clause(self) -> None:
        self.invalid(lambda d: d["cases"][1]["discriminator"].update(refs=["c1"]),
                     "discriminator omits a cross-clause link")

    def test_stale_source_revision_is_rejected(self) -> None:
        self.invalid(lambda d: d.update(source_git_blob_sha="0" * 40),
                     "source corpus revision changed")

    def test_no_obvious_pii_in_seed(self) -> None:
        serialized = json.dumps(self.dataset, ensure_ascii=False)
        self.assertIsNone(re.search(r"\b\d{9}\b", serialized))
        self.assertNotIn("@example.com", serialized)


class SecurityOntologyCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cards = json.loads(
            (HERE / "research/question_engine/expert_memory/security_ontology_cards_v0_1.json")
            .read_text(encoding="utf-8")
        )
        cls.provenance = json.loads(
            (HERE / "research/question_engine/expert_memory/security_ontology_card_provenance_v0_1.json")
            .read_text(encoding="utf-8")
        )
        cls.overlay = json.loads(
            (HERE / "docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2026_V1.json")
            .read_text(encoding="utf-8")
        )
        cls.by_id = {card["id"]: card for card in cls.cards["cards"]}

    def test_2026_overlay_records_in_force_phase_without_runtime_promotion(self) -> None:
        self.assertEqual(self.overlay["commencement"]["effective_from"], "2026-09-30")
        self.assertEqual(self.overlay["status"], "ENACTED_GAZETTE_NOT_EXPERT_REVIEWED")
        self.assertEqual(self.overlay["usage"]["current_phase"], "IN_FORCE_FROM_2026-09-30")
        self.assertFalse(self.overlay["usage"]["production_runtime_wired"])
        self.assertFalse(self.overlay["usage"]["expert_verified"])

    def test_institutional_guarantee_uses_exact_statutory_provider_classes(self) -> None:
        card = self.by_id["INSTITUTIONAL_GUARANTEE"]
        issuer_slot = card["slots"]["issuer_class_and_license"]
        provider_classes = self.overlay["normalized_changes"]["section_25y_a"]["provider_classes"]
        self.assertEqual(
            provider_classes,
            [
                "licensed_credit_provider",
                "licensed_deposit_and_credit_provider",
                "licensed_financially_stable_payment_service_provider",
                "insurer",
            ],
        )
        for provider_class in provider_classes:
            self.assertIn(provider_class, issuer_slot)

    def test_cap_unknown_and_instrument_boundaries_are_explicit(self) -> None:
        card = self.by_id["INSTITUTIONAL_GUARANTEE"]
        rules = "\n".join(card["validation_rules"])
        boundaries = "\n".join(card["do_not_confuse"])
        self.assertIn("`SECURITY`", rules)
        self.assertIn("2026-09-30", rules)
        self.assertIn("UNRESOLVED_CAP_APPLICABILITY", rules)
        self.assertIn("PERSONAL_GUARANTEE", boundaries)
        self.assertIn("SECURITY_CHECK", boundaries)
        self.assertIn("PROMISSORY_NOTE", boundaries)

    def test_statutory_driven_card_has_versioned_provenance(self) -> None:
        sources = self.provenance["sources"]["INSTITUTIONAL_GUARANTEE"]
        self.assertEqual(len(sources), 1)
        self.assertEqual(
            sources[0]["path"],
            "docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2026_V1.json",
        )
        self.assertIn("25י(b)", sources[0]["locators"])
        self.assertIn("§37", sources[0]["locators"])


if __name__ == "__main__":
    unittest.main()
