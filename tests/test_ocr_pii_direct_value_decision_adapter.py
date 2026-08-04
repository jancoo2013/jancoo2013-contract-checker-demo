import copy
import unittest

from research.hebrew_contract_ocr.pii_candidate_evidence import validate_candidate
from research.hebrew_contract_ocr.pii_direct_patterns import (
    DirectValueMatch,
    find_direct_value_matches,
)
from research.hebrew_contract_ocr.pii_direct_value_decision_adapter import (
    adapt_direct_value_match_to_candidate,
)
from research.hebrew_contract_ocr.pii_evidence_decisions import DETECTOR_VERSION, REVIEW_REASON


def geometry(x0=10, y0=10, x1=80, y1=30):
    return {"type": "bbox", "coordinates": [x0, y0, x1, y1]}


def adapt(match, source_geometry=None):
    return adapt_direct_value_match_to_candidate(
        match,
        "candidate-001",
        "direct-value-001",
        source_geometry or geometry(),
        100,
        80,
    )


class PiiDirectValueDecisionAdapterTests(unittest.TestCase):
    def test_detected_match_becomes_class_bound_auto_mask(self):
        match = find_direct_value_matches("tenant@example.test")[0]
        candidate = adapt(match)

        self.assertEqual("email", candidate["proposed_class"])
        self.assertEqual("auto_mask", candidate["disposition"])
        self.assertEqual(DETECTOR_VERSION, candidate["detector_version"])
        self.assertEqual(
            {
                "evidence_id": "direct-value-001",
                "family": "direct_value",
                "detector_id": "direct-email-v0",
                "geometry": geometry(),
            },
            candidate["evidence"][0],
        )
        self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_approved_direct_classes_preserve_closed_binding(self):
        cases = (
            ("bank_identifier", "direct-israeli-iban-v0"),
            ("email", "direct-email-v0"),
            ("phone", "direct-israeli-phone-v0"),
            ("israeli_id", "direct-israeli-id-v0"),
        )
        for pii_class, detector_id in cases:
            with self.subTest(pii_class=pii_class):
                candidate = adapt(DirectValueMatch(pii_class, 2, 8, detector_id))
                self.assertEqual(pii_class, candidate["proposed_class"])
                self.assertEqual("auto_mask", candidate["disposition"])
                self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_class_mismatched_detector_fails_closed_to_review(self):
        candidate = adapt(DirectValueMatch("email", 2, 8, "direct-israeli-phone-v0"))

        self.assertEqual("email", candidate["proposed_class"])
        self.assertEqual("local_review", candidate["disposition"])
        self.assertEqual(REVIEW_REASON, candidate["ambiguity_reason"])
        self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_unapproved_detector_fails_closed_to_review(self):
        candidate = adapt(DirectValueMatch("phone", 2, 8, "unapproved-digits-v0"))

        self.assertEqual("local_review", candidate["disposition"])
        self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_geometry_must_be_exact_and_in_bounds(self):
        match = DirectValueMatch("phone", 2, 8, "direct-israeli-phone-v0")
        with self.assertRaisesRegex(ValueError, "positive in-bounds"):
            adapt(match, geometry(10, 10, 101, 30))

    def test_invalid_match_and_identifiers_are_rejected(self):
        with self.assertRaisesRegex(TypeError, "match must be a DirectValueMatch"):
            adapt("not-a-match")

        match = DirectValueMatch("phone", 2, 8, "direct-israeli-phone-v0")
        with self.assertRaisesRegex(TypeError, "evidence_id must be a string"):
            adapt_direct_value_match_to_candidate(
                match,
                "candidate-001",
                None,
                geometry(),
                100,
                80,
            )
        with self.assertRaisesRegex(ValueError, "invalid candidate_id"):
            adapt_direct_value_match_to_candidate(
                match,
                "bad candidate id",
                "direct-value-001",
                geometry(),
                100,
                80,
            )

    def test_offsets_must_be_integer_and_non_boolean(self):
        for start, end in ((True, 8), (2, False), (2.0, 8), (2, 8.0)):
            with self.subTest(start=start, end=end), self.assertRaisesRegex(
                ValueError, "match offsets must be integers"
            ):
                adapt(DirectValueMatch("phone", start, end, "direct-israeli-phone-v0"))

    def test_offsets_must_form_ordered_non_negative_non_empty_span(self):
        for start, end in ((-5, -1), (-1, 8), (8, 8), (20, 10)):
            with self.subTest(start=start, end=end), self.assertRaisesRegex(
                ValueError, "ordered non-negative non-empty span"
            ):
                adapt(DirectValueMatch("phone", start, end, "direct-israeli-phone-v0"))

    def test_candidate_is_value_free(self):
        synthetic_value = "tenant@example.test"
        match = find_direct_value_matches(synthetic_value)[0]
        candidate = adapt(match)

        self.assertNotIn(synthetic_value, repr(candidate))
        self.assertNotIn("start", candidate["evidence"][0])
        self.assertNotIn("end", candidate["evidence"][0])

    def test_calls_are_deterministic_and_defensively_copy_geometry(self):
        match = DirectValueMatch("phone", 2, 8, "direct-israeli-phone-v0")
        source_geometry = geometry()
        original = copy.deepcopy(source_geometry)

        first = adapt(match, source_geometry)
        self.assertEqual(first, adapt(match, source_geometry))
        first["geometry"]["coordinates"][0] = 0
        first["evidence"][0]["geometry"]["coordinates"][0] = 1

        self.assertEqual(original, source_geometry)
        self.assertEqual(10, adapt(match, source_geometry)["geometry"]["coordinates"][0])


if __name__ == "__main__":
    unittest.main()
