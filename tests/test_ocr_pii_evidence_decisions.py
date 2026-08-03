import copy
import unittest

from research.hebrew_contract_ocr.pii_candidate_evidence import validate_candidate
from research.hebrew_contract_ocr.pii_evidence_decisions import (
    DETECTOR_VERSION,
    REVIEW_REASON,
    combine_evidence_into_candidate,
)


def geometry(x0=10, y0=10, x1=80, y1=30):
    return {"type": "bbox", "coordinates": [x0, y0, x1, y1]}


def evidence(evidence_id, family, detector_id=None, **extra):
    defaults = {
        "direct_value": "direct-israeli-phone-v0",
        "marker": "marker-phone-v0",
        "visual_sensitive_region": "visual-evidence-filled-field-v0",
        "relation": "marker-to-visual-v0",
        "weak_layout_context": "synthetic-layout-v0",
    }
    return {
        "evidence_id": evidence_id,
        "family": family,
        "detector_id": detector_id or defaults.get(family, "synthetic-detector-v0"),
        **extra,
    }


def relation(evidence_id, relation_type, source_id, target_id):
    return evidence(
        evidence_id,
        "relation",
        detector_id=(
            "marker-to-direct-value-v0"
            if relation_type == "marker_to_value"
            else "marker-to-visual-v0"
        ),
        relation={
            "relation_type": relation_type,
            "source_evidence_id": source_id,
            "target_evidence_id": target_id,
        },
    )


def combine(records, proposed_class="phone"):
    return combine_evidence_into_candidate(
        "candidate-001",
        proposed_class,
        geometry(),
        records,
        100,
        80,
    )


class PiiEvidenceDecisionTests(unittest.TestCase):
    def assert_valid_disposition(self, records, expected, proposed_class="phone"):
        candidate = combine(records, proposed_class)
        self.assertEqual(expected, candidate["disposition"])
        self.assertIsNone(validate_candidate(candidate, 100, 80))
        return candidate

    def test_direct_value_becomes_auto_mask(self):
        candidate = self.assert_valid_disposition(
            [evidence("value-1", "direct_value", geometry=geometry())],
            "auto_mask",
        )
        self.assertIsNone(candidate["ambiguity_reason"])

    def test_marker_to_value_relation_becomes_auto_mask(self):
        records = [
            evidence("marker-1", "marker"),
            evidence("value-1", "direct_value", geometry=geometry()),
            relation("relation-1", "marker_to_value", "marker-1", "value-1"),
        ]
        self.assert_valid_disposition(records, "auto_mask")

    def test_marker_to_visual_relation_becomes_auto_mask(self):
        records = [
            evidence("marker-1", "marker"),
            evidence("visual-1", "visual_sensitive_region", geometry=geometry()),
            relation("relation-1", "marker_to_visual", "marker-1", "visual-1"),
        ]
        self.assert_valid_disposition(records, "auto_mask", "phone")

    def test_class_mismatched_direct_value_requires_local_review(self):
        records = [evidence("value-1", "direct_value", geometry=geometry())]
        self.assert_valid_disposition(records, "local_review", "email")

    def test_phone_marker_linked_to_signature_requires_local_review(self):
        records = [
            evidence("marker-1", "marker"),
            evidence(
                "visual-1",
                "visual_sensitive_region",
                detector_id="visual-evidence-signature-v0",
                geometry=geometry(),
            ),
            relation("relation-1", "marker_to_visual", "marker-1", "visual-1"),
        ]
        self.assert_valid_disposition(records, "local_review", "phone")

    def test_unapproved_direct_detector_requires_local_review(self):
        records = [
            evidence(
                "value-1",
                "direct_value",
                detector_id="unapproved-digits-v0",
                geometry=geometry(),
            )
        ]
        self.assert_valid_disposition(records, "local_review", "other_likely_pii")

    def test_weak_layout_never_becomes_auto_mask(self):
        records = [
            evidence("page-position", "weak_layout_context"),
            evidence("page-role", "weak_layout_context"),
            evidence("alignment", "weak_layout_context"),
        ]
        candidate = self.assert_valid_disposition(records, "local_review")
        self.assertEqual(REVIEW_REASON, candidate["ambiguity_reason"])

    def test_unlinked_marker_and_visual_require_local_review(self):
        for records in (
            [evidence("marker-1", "marker")],
            [evidence("visual-1", "visual_sensitive_region", geometry=geometry())],
            [
                evidence("marker-1", "marker"),
                evidence("visual-1", "visual_sensitive_region", geometry=geometry()),
            ],
        ):
            with self.subTest(records=records):
                self.assert_valid_disposition(records, "local_review")

    def test_empty_evidence_is_preserved(self):
        candidate = self.assert_valid_disposition([], "preserve")
        self.assertIsNone(candidate["ambiguity_reason"])

    def test_strong_evidence_wins_over_weak_context(self):
        records = [
            evidence("weak-1", "weak_layout_context"),
            evidence("value-1", "direct_value", geometry=geometry()),
        ]
        self.assert_valid_disposition(records, "auto_mask")

    def test_strong_evidence_without_exact_geometry_requires_review(self):
        cases = (
            [evidence("value-1", "direct_value")],
            [evidence("value-1", "direct_value", geometry=geometry(10, 10, 90, 30))],
            [
                evidence("value-1", "direct_value", geometry=geometry()),
                evidence("value-2", "direct_value", geometry=geometry(10, 40, 80, 60)),
            ],
        )
        for records in cases:
            with self.subTest(records=records):
                self.assert_valid_disposition(records, "local_review")

    def test_schema_invalid_evidence_is_rejected(self):
        invalid_cases = (
            [evidence("relation-1", "relation", relation={})],
            [
                evidence("marker-1", "marker"),
                relation("relation-1", "marker_to_visual", "marker-1", "missing-1"),
            ],
            [evidence("value-1", "direct_value", raw_value="synthetic-secret")],
        )
        for records in invalid_cases:
            with self.subTest(records=records), self.assertRaises(ValueError):
                combine(records)

    def test_invalid_candidate_fields_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown proposed_class"):
            combine([], "generic_digits")
        with self.assertRaisesRegex(ValueError, "positive in-bounds"):
            combine_evidence_into_candidate(
                "candidate-001", "phone", geometry(10, 10, 101, 20), [], 100, 80
            )
        with self.assertRaisesRegex(ValueError, "positive integers"):
            combine_evidence_into_candidate(
                "candidate-001", "phone", geometry(), [], True, 80
            )

    def test_output_has_exact_schema_and_detector_version(self):
        candidate = combine([])
        self.assertEqual(
            {
                "schema_version",
                "candidate_id",
                "proposed_class",
                "geometry",
                "disposition",
                "detector_version",
                "evidence",
                "ambiguity_reason",
            },
            set(candidate),
        )
        self.assertEqual(DETECTOR_VERSION, candidate["detector_version"])

    def test_calls_are_deterministic_and_defensively_copy_inputs(self):
        source_geometry = geometry()
        records = [evidence("weak-1", "weak_layout_context", geometry=geometry())]
        original_geometry = copy.deepcopy(source_geometry)
        original_records = copy.deepcopy(records)

        first = combine_evidence_into_candidate(
            "candidate-001", "phone", source_geometry, records, 100, 80
        )
        self.assertEqual(
            first,
            combine_evidence_into_candidate(
                "candidate-001", "phone", source_geometry, records, 100, 80
            ),
        )
        first["geometry"]["coordinates"][0] = 0
        first["evidence"][0]["geometry"]["coordinates"][0] = 0
        self.assertEqual(original_geometry, source_geometry)
        self.assertEqual(original_records, records)


if __name__ == "__main__":
    unittest.main()
