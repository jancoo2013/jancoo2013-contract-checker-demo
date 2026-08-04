import copy
from dataclasses import replace
import unittest

from research.hebrew_contract_ocr.pii_candidate_evidence import validate_candidate
from research.hebrew_contract_ocr.pii_direct_patterns import (
    DirectValueMatch,
    find_direct_value_matches,
)
from research.hebrew_contract_ocr.pii_evidence_decisions import DETECTOR_VERSION, REVIEW_REASON
from research.hebrew_contract_ocr.pii_marker_value_decision_adapter import (
    adapt_marker_value_relation_to_candidate,
)
from research.hebrew_contract_ocr.pii_marker_value_relations import (
    MarkerValueRelation,
    find_marker_value_relations,
)


VALID_ID = "123456782"
VALID_PHONE = "050-123-4567"
VALID_EMAIL = "tenant@example.test"
VALID_IBAN = "IL88 1234 5678 9012 3456 789"


def geometry(x0=40, y0=10, x1=90, y1=30):
    return {"type": "bbox", "coordinates": [x0, y0, x1, y1]}


def marker_geometry():
    return {"type": "bbox", "coordinates": [10, 10, 35, 30]}


def detected_pair(marker="טלפון", value=VALID_PHONE):
    text = f"{marker}: {value}"
    return find_marker_value_relations(text)[0], find_direct_value_matches(text)[0]


def adapt(relation, direct_match, value_box=None, marker_box=None):
    return adapt_marker_value_relation_to_candidate(
        relation,
        direct_match,
        "candidate-001",
        "marker-001",
        "direct-value-001",
        "relation-001",
        value_box or geometry(),
        100,
        80,
        marker_box,
    )


class PiiMarkerValueDecisionAdapterTests(unittest.TestCase):
    def test_detected_relation_becomes_class_bound_auto_mask(self):
        relation, direct_match = detected_pair()
        candidate = adapt(relation, direct_match, marker_box=marker_geometry())

        self.assertEqual("phone", candidate["proposed_class"])
        self.assertEqual("auto_mask", candidate["disposition"])
        self.assertEqual(DETECTOR_VERSION, candidate["detector_version"])
        self.assertEqual(
            ["marker", "direct_value", "relation"],
            [record["family"] for record in candidate["evidence"]],
        )
        self.assertEqual(
            {
                "relation_type": "marker_to_value",
                "source_evidence_id": "marker-001",
                "target_evidence_id": "direct-value-001",
            },
            candidate["evidence"][2]["relation"],
        )
        self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_all_approved_marker_value_classes_auto_mask(self):
        cases = (
            ("ת.ז.", VALID_ID, "israeli_id"),
            ("טלפון", VALID_PHONE, "phone"),
            ("אימייל", VALID_EMAIL, "email"),
            ("מספר IBAN", VALID_IBAN, "bank_identifier"),
        )
        for marker, value, pii_class in cases:
            with self.subTest(pii_class=pii_class):
                relation, direct_match = detected_pair(marker, value)
                candidate = adapt(relation, direct_match)
                self.assertEqual(pii_class, candidate["proposed_class"])
                self.assertEqual("auto_mask", candidate["disposition"])
                self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_relation_must_reference_the_exact_direct_match(self):
        relation, direct_match = detected_pair()
        mismatches = (
            replace(direct_match, pii_class="email"),
            replace(direct_match, start=direct_match.start + 1),
            replace(direct_match, end=direct_match.end - 1),
            replace(direct_match, detector_id="direct-email-v0"),
        )
        for mismatch in mismatches:
            with self.subTest(mismatch=mismatch), self.assertRaisesRegex(
                ValueError, "reference direct_match exactly"
            ):
                adapt(relation, mismatch)

    def test_invalid_source_offsets_are_rejected(self):
        relation, direct_match = detected_pair()
        invalid_relations = (
            replace(relation, marker_start=-1),
            replace(relation, marker_end=relation.marker_start),
            replace(relation, marker_end=relation.value_start + 1),
            replace(relation, value_end=relation.value_start),
            replace(relation, value_start=True),
        )
        for invalid_relation in invalid_relations:
            with self.subTest(relation=invalid_relation), self.assertRaisesRegex(
                ValueError, "offsets"
            ):
                adapt(invalid_relation, direct_match)

        with self.assertRaisesRegex(ValueError, "offsets"):
            adapt(relation, replace(direct_match, start=-1))

    def test_unapproved_relation_semantics_fail_closed_to_review(self):
        relation, direct_match = detected_pair()
        cases = (
            replace(relation, marker_detector_id="marker-unapproved-v0"),
            replace(relation, relation_detector_id="relation-unapproved-v0"),
            replace(
                relation,
                direct_value_detector_id="direct-unapproved-v0",
            ),
        )
        matches = (
            direct_match,
            direct_match,
            replace(direct_match, detector_id="direct-unapproved-v0"),
        )
        for unapproved_relation, supplied_match in zip(cases, matches):
            with self.subTest(relation=unapproved_relation):
                candidate = adapt(unapproved_relation, supplied_match)
                self.assertEqual("local_review", candidate["disposition"])
                self.assertEqual(REVIEW_REASON, candidate["ambiguity_reason"])
                self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_detector_class_mismatch_fails_closed_to_review(self):
        relation, direct_match = detected_pair()
        relation = replace(
            relation,
            pii_class="email",
            marker_detector_id="marker-email-v0",
            direct_value_detector_id="direct-israeli-phone-v0",
        )
        direct_match = replace(direct_match, pii_class="email")

        candidate = adapt(relation, direct_match)

        self.assertEqual("email", candidate["proposed_class"])
        self.assertEqual("local_review", candidate["disposition"])
        self.assertIsNone(validate_candidate(candidate, 100, 80))

    def test_invalid_types_identifiers_and_geometry_are_rejected(self):
        relation, direct_match = detected_pair()
        with self.assertRaisesRegex(TypeError, "MarkerValueRelation"):
            adapt("not-a-relation", direct_match)
        with self.assertRaisesRegex(TypeError, "DirectValueMatch"):
            adapt(relation, "not-a-match")
        with self.assertRaisesRegex(TypeError, "marker_evidence_id must be a string"):
            adapt_marker_value_relation_to_candidate(
                relation,
                direct_match,
                "candidate-001",
                None,
                "direct-value-001",
                "relation-001",
                geometry(),
                100,
                80,
            )
        with self.assertRaisesRegex(ValueError, "positive in-bounds"):
            adapt(relation, direct_match, geometry(40, 10, 101, 30))

    def test_candidate_is_value_free(self):
        relation, direct_match = detected_pair(value=VALID_EMAIL, marker="אימייל")
        candidate = adapt(relation, direct_match)

        self.assertNotIn(VALID_EMAIL, repr(candidate))
        for record in candidate["evidence"]:
            self.assertNotIn("start", record)
            self.assertNotIn("end", record)

    def test_calls_are_deterministic_and_defensively_copy_geometries(self):
        relation, direct_match = detected_pair()
        value_box = geometry()
        marker_box = marker_geometry()
        original_value = copy.deepcopy(value_box)
        original_marker = copy.deepcopy(marker_box)

        first = adapt(relation, direct_match, value_box, marker_box)
        self.assertEqual(first, adapt(relation, direct_match, value_box, marker_box))
        first["geometry"]["coordinates"][0] = 0
        first["evidence"][0]["geometry"]["coordinates"][0] = 0
        first["evidence"][1]["geometry"]["coordinates"][0] = 0

        self.assertEqual(original_value, value_box)
        self.assertEqual(original_marker, marker_box)


if __name__ == "__main__":
    unittest.main()
