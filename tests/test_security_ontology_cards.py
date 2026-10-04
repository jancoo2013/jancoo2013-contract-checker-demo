"""Regression checks for SECURITY ontology cards and the 2026 guarantee overlay."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CARDS_PATH = ROOT / "research/question_engine/expert_memory/security_ontology_cards_v0_1.json"
PROVENANCE_PATH = ROOT / "research/question_engine/expert_memory/security_ontology_card_provenance_v0_1.json"
OVERLAY_PATH = ROOT / "docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2026_V1.json"


class SecurityOntologyCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cards = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
        cls.provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
        cls.overlay = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))
        cls.by_id = {card["id"]: card for card in cls.cards["cards"]}

    def test_2026_overlay_is_marked_in_force_without_runtime_promotion(self) -> None:
        self.assertEqual(self.overlay["commencement"]["effective_from"], "2026-09-30")
        self.assertEqual(self.overlay["status"], "IN_FORCE_GAZETTE_NOT_EXPERT_REVIEWED")
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
