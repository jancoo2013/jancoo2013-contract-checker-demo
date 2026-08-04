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
from research.hebrew_contract_ocr.pii_evidence_decisions import DETECTOR_VERSION


def geometry(x0=10, y0=10, x1=80, y1=30):
    return {"type": "bbox", "coordinates": [x0, y0, x1, y1]}


VALID_ID = "123456782"
VALID_IBAN = "IL88 1234 5678 9012 3456 789"


def adapt(match, source_text, source_geometry=None):
    return adapt_direct_value_match_to_candidate(
        match,
        source_text,
        "candidate-001",
        "direct-value-001",
        source_geometry or geometry(),
        100,
        80,
    )


class PiiDirectValueDecisionAdapterTests(unittest.TestCase):
    def test_detected_match_becomes_class_bound_auto_mask(self):
        source_text = "tenant@example.test"
        match = find_direct_value_matches(source_text)[0]
        candidate = adapt(match, source_text)

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
            (VALID_IBAN, "bank_identifier", "direct-israeli-iban-v0"),
            ("tenant@example.test", "email", "direct-email-v0"),
            ("050-123-4567", "phone", "direct-israeli-phone-v0"),
            (VALID_ID, "israeli_id", "direct-israeli-id-v0"),
        )
        for source_text, pii_class, detector_id in cases:
            with self.subTest(pii_class=pii_class):
                match = find_direct_value_matches(source_text)[0]
                self.assertEqual(DirectValueMatch(pii_class, 0, len(source_text), detector_id), match)
                candidate = adapt(match, source_text)
                self.assertEqual(pii_class, candidate["proposed_class"])
                self.assertEqual("auto_mask", candidate["disposition"])
                self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_forged_well_formed_matches_fail_closed(self):
        source_text = "tenant@example.test"
        exact = find_direct_value_matches(source_text)[0]
        forged_matches = (
            DirectValueMatch(exact.pii_class, exact.start + 1, exact.end, exact.detector_id),
            DirectValueMatch("phone", exact.start, exact.end, "direct-israeli-phone-v0"),
            DirectValueMatch(exact.pii_class, exact.start, exact.end, "unapproved-digits-v0"),
        )
        for forged in forged_matches:
            with self.subTest(forged=forged), self.assertRaisesRegex(
                ValueError, "exactly match an approved finder result"
            ):
                adapt(forged, source_text)

    def test_geometry_must_be_exact_and_in_bounds(self):
        source_text = "050-123-4567"
        match = find_direct_value_matches(source_text)[0]
        with self.assertRaisesRegex(ValueError, "positive in-bounds"):
            adapt(match, source_text, geometry(10, 10, 101, 30))

    def test_invalid_match_and_identifiers_are_rejected(self):
        with self.assertRaisesRegex(TypeError, "match must be a DirectValueMatch"):
            adapt("not-a-match", "050-123-4567")

        source_text = "050-123-4567"
        match = find_direct_value_matches(source_text)[0]
        with self.assertRaisesRegex(TypeError, "evidence_id must be a string"):
            adapt_direct_value_match_to_candidate(
                match,
                source_text,
                "candidate-001",
                None,
                geometry(),
                100,
                80,
            )
        with self.assertRaisesRegex(ValueError, "invalid candidate_id"):
            adapt_direct_value_match_to_candidate(
                match,
                source_text,
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
                adapt(
                    DirectValueMatch("phone", start, end, "direct-israeli-phone-v0"),
                    "050-123-4567",
                )

    def test_offsets_must_form_ordered_non_negative_non_empty_span(self):
        for start, end in ((-5, -1), (-1, 8), (8, 8), (20, 10)):
            with self.subTest(start=start, end=end), self.assertRaisesRegex(
                ValueError, "ordered non-negative non-empty span"
            ):
                adapt(
                    DirectValueMatch("phone", start, end, "direct-israeli-phone-v0"),
                    "050-123-4567",
                )

    def test_source_text_must_be_local_finder_input(self):
        match = find_direct_value_matches("tenant@example.test")[0]
        for source_text in (None, b"tenant@example.test", ["tenant@example.test"]):
            with self.subTest(source_text=source_text), self.assertRaisesRegex(
                TypeError, "text must be a string"
            ):
                adapt(match, source_text)

    def test_candidate_is_value_free(self):
        synthetic_value = "tenant@example.test"
        match = find_direct_value_matches(synthetic_value)[0]
        candidate = adapt(match, synthetic_value)

        self.assertNotIn(synthetic_value, repr(candidate))
        self.assertNotIn("source_text", candidate)
        self.assertNotIn("start", candidate["evidence"][0])
        self.assertNotIn("end", candidate["evidence"][0])

    def test_calls_are_deterministic_and_defensively_copy_geometry(self):
        source_text = "050-123-4567"
        match = find_direct_value_matches(source_text)[0]
        source_geometry = geometry()
        original = copy.deepcopy(source_geometry)

        first = adapt(match, source_text, source_geometry)
        self.assertEqual(first, adapt(match, source_text, source_geometry))
        first["geometry"]["coordinates"][0] = 0
        first["evidence"][0]["geometry"]["coordinates"][0] = 1

        self.assertEqual(original, source_geometry)
        self.assertEqual(
            10,
            adapt(match, source_text, source_geometry)["geometry"]["coordinates"][0],
        )


if __name__ == "__main__":
    unittest.main()
