import copy
from dataclasses import replace
import unittest

from research.hebrew_contract_ocr.pii_candidate_evidence import validate_candidate
from research.hebrew_contract_ocr.pii_evidence_decisions import DETECTOR_VERSION, REVIEW_REASON
from research.hebrew_contract_ocr.pii_visual_decision_adapter import (
    adapt_visual_region_to_candidate,
)
from research.hebrew_contract_ocr.pii_visual_sensitive_regions import (
    VisualSensitiveRegion,
    record_visual_sensitive_region,
)


def region(visual_kind="filled_field"):
    return record_visual_sensitive_region(visual_kind, [30, 10, 80, 35], 100, 80)


def marker(detector_id="marker-phone-v0", evidence_id="marker-001"):
    return {
        "evidence_id": evidence_id,
        "family": "marker",
        "detector_id": detector_id,
        "geometry": {"type": "bbox", "coordinates": [5, 10, 25, 35]},
    }


def adapt(observation, marker_evidence=None, relation_id=None):
    return adapt_visual_region_to_candidate(
        observation,
        "candidate-001",
        "visual-001",
        100,
        80,
        marker_evidence,
        relation_id,
    )


class PiiVisualDecisionAdapterTests(unittest.TestCase):
    def test_generic_visual_kinds_inherit_approved_marker_class(self):
        cases = (
            ("filled_field", "marker-phone-v0", "phone"),
            ("filled_field", "marker-email-v0", "email"),
            ("handwriting", "marker-israeli-id-v0", "israeli_id"),
            ("handwriting", "marker-israeli-iban-v0", "bank_identifier"),
        )
        for visual_kind, detector_id, expected_class in cases:
            with self.subTest(visual_kind=visual_kind, detector_id=detector_id):
                candidate = adapt(region(visual_kind), marker(detector_id), "relation-001")
                self.assertEqual(expected_class, candidate["proposed_class"])
                self.assertEqual("auto_mask", candidate["disposition"])
                self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_fixed_visual_kinds_keep_their_closed_class(self):
        for visual_kind in ("signature", "initials", "stamp"):
            with self.subTest(visual_kind=visual_kind):
                candidate = adapt(region(visual_kind))
                self.assertEqual(visual_kind, candidate["proposed_class"])
                self.assertEqual("local_review", candidate["disposition"])
                self.assertEqual(REVIEW_REASON, candidate["ambiguity_reason"])
                self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_incompatible_marker_cannot_reclassify_fixed_visual_kind(self):
        candidate = adapt(region("signature"), marker(), "relation-001")

        self.assertEqual("signature", candidate["proposed_class"])
        self.assertEqual("local_review", candidate["disposition"])
        self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_missing_or_unapproved_marker_stays_local_review(self):
        cases = (
            (None, None),
            (marker("marker-unapproved-v0"), "relation-001"),
        )
        for marker_evidence, relation_id in cases:
            with self.subTest(marker_evidence=marker_evidence):
                candidate = adapt(region("handwriting"), marker_evidence, relation_id)
                self.assertEqual("other_likely_pii", candidate["proposed_class"])
                self.assertEqual("local_review", candidate["disposition"])
                self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_linked_evidence_uses_exact_region_geometry(self):
        candidate = adapt(region(), marker(), "relation-001")

        self.assertEqual(DETECTOR_VERSION, candidate["detector_version"])
        self.assertEqual(
            ["marker", "visual_sensitive_region", "relation"],
            [record["family"] for record in candidate["evidence"]],
        )
        self.assertEqual(candidate["geometry"], candidate["evidence"][1]["geometry"])
        self.assertEqual(
            {
                "relation_type": "marker_to_visual",
                "source_evidence_id": "marker-001",
                "target_evidence_id": "visual-001",
            },
            candidate["evidence"][2]["relation"],
        )

    def test_forged_region_fails_closed(self):
        valid = region("signature")
        cases = (
            replace(valid, detector_id="visual-evidence-phone-v0"),
            replace(valid, x0=-1),
            replace(valid, x1=101),
            VisualSensitiveRegion("unknown", 30, 10, 80, 35, "visual-evidence-signature-v0"),
        )
        for forged in cases:
            with self.subTest(forged=forged), self.assertRaises((TypeError, ValueError)):
                adapt(forged)

    def test_invalid_marker_and_relation_inputs_are_rejected(self):
        with self.assertRaisesRegex(TypeError, "marker_evidence"):
            adapt(region(), "not-a-marker", "relation-001")
        with self.assertRaisesRegex(ValueError, "requires marker_evidence"):
            adapt(region(), None, "relation-001")
        with self.assertRaisesRegex(TypeError, "relation_evidence_id"):
            adapt(region(), marker(), None)
        with self.assertRaisesRegex(ValueError, "endpoints do not match"):
            adapt(region(), {**marker(), "family": "direct_value"}, "relation-001")

    def test_invalid_identifiers_geometry_and_bounds_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid candidate_id"):
            adapt_visual_region_to_candidate(region(), "bad id", "visual-001", 100, 80)
        with self.assertRaisesRegex(ValueError, "invalid evidence_id"):
            adapt_visual_region_to_candidate(region(), "candidate-001", "bad id", 100, 80)
        with self.assertRaisesRegex(ValueError, "positive in-bounds"):
            adapt_visual_region_to_candidate(region(), "candidate-001", "visual-001", 70, 80)
        with self.assertRaisesRegex(TypeError, "VisualSensitiveRegion"):
            adapt("not-a-region")

    def test_output_is_value_free_deterministic_and_defensively_copied(self):
        observation = region("filled_field")
        marker_evidence = marker()
        original_marker = copy.deepcopy(marker_evidence)

        first = adapt(observation, marker_evidence, "relation-001")
        self.assertEqual(first, adapt(observation, marker_evidence, "relation-001"))
        first["geometry"]["coordinates"][0] = 0
        first["evidence"][0]["geometry"]["coordinates"][0] = 0
        first["evidence"][1]["geometry"]["coordinates"][0] = 0

        self.assertEqual(original_marker, marker_evidence)
        for forbidden in ("raw_text", "normalized_value", "image_bytes", "pixels", "hash"):
            self.assertNotIn(forbidden, repr(first))


if __name__ == "__main__":
    unittest.main()
