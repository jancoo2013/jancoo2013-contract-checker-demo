import copy
from dataclasses import fields
import unittest

from research.hebrew_contract_ocr.pii_candidate_evidence import validate_candidate
from research.hebrew_contract_ocr.pii_direct_patterns import (
    find_direct_value_matches,
    make_direct_value_evidence,
)
from research.hebrew_contract_ocr.pii_marker_value_relations import (
    MarkerValueRelation,
    find_marker_value_relations,
    make_marker_relation_evidence,
)


VALID_ID = "123456782"
VALID_PHONE = "050-123-4567"
VALID_EMAIL = "tenant@example.test"
VALID_IBAN = "IL88 1234 5678 9012 3456 789"


class PiiMarkerValueRelationTests(unittest.TestCase):
    def test_positive_relations_have_exact_offsets_and_detector_ids(self):
        cases = (
            ("ת.ז.", VALID_ID, "israeli_id", "marker-israeli-id-v0", "direct-israeli-id-v0"),
            ("טלפון", VALID_PHONE, "phone", "marker-phone-v0", "direct-israeli-phone-v0"),
            ("אימייל", VALID_EMAIL, "email", "marker-email-v0", "direct-email-v0"),
            ("מספר IBAN", VALID_IBAN, "bank_identifier", "marker-israeli-iban-v0", "direct-israeli-iban-v0"),
        )
        for marker, value, pii_class, marker_detector, value_detector in cases:
            with self.subTest(marker=marker):
                text = f"{marker}: {value}"
                relation = find_marker_value_relations(text)[0]
                self.assertEqual(pii_class, relation.pii_class)
                self.assertEqual((0, len(marker)), (relation.marker_start, relation.marker_end))
                self.assertEqual((len(marker) + 2, len(text)), (relation.value_start, relation.value_end))
                self.assertEqual(marker_detector, relation.marker_detector_id)
                self.assertEqual(value_detector, relation.direct_value_detector_id)
                self.assertEqual("marker-to-direct-value-v0", relation.relation_detector_id)

    def test_all_approved_marker_variants(self):
        cases = (
            (("ת.ז.", "ת.ז", 'ת"ז', "ת״ז", "מספר זהות"), VALID_ID, "israeli_id"),
            (("טלפון", "נייד"), VALID_PHONE, "phone"),
            (('דוא"ל', "דוא״ל", "אימייל", "EmAiL"), VALID_EMAIL, "email"),
            (("IBAN", "מספר iBaN"), VALID_IBAN, "bank_identifier"),
        )
        for markers, value, pii_class in cases:
            for marker in markers:
                with self.subTest(marker=marker):
                    relation = find_marker_value_relations(f"{marker} = {value}")[0]
                    self.assertEqual(pii_class, relation.pii_class)
                    self.assertEqual((0, len(marker)), (relation.marker_start, relation.marker_end))

    def test_incompatible_or_missing_signals_do_not_relate(self):
        self.assertEqual((), find_marker_value_relations(f"טלפון: {VALID_EMAIL}"))
        self.assertEqual((), find_marker_value_relations("טלפון: synthetic-placeholder"))
        self.assertEqual((), find_marker_value_relations(VALID_PHONE))

    def test_value_must_follow_marker_on_the_same_line(self):
        self.assertEqual((), find_marker_value_relations(f"{VALID_PHONE} טלפון"))
        self.assertEqual((), find_marker_value_relations(f"טלפון:\n{VALID_PHONE}"))
        self.assertEqual((), find_marker_value_relations(f"טלפון:\r\n{VALID_PHONE}"))

    def test_gap_is_bounded_and_contains_only_approved_characters(self):
        self.assertEqual(1, len(find_marker_value_relations(f"טלפון [=—] {VALID_PHONE}")))
        self.assertEqual((), find_marker_value_relations(f"טלפון{' ' * 17}{VALID_PHONE}"))
        self.assertEqual((), find_marker_value_relations(f"טלפון ערך {VALID_PHONE}"))
        self.assertEqual((), find_marker_value_relations(f"טלפון value {VALID_PHONE}"))

    def test_embedded_marker_substrings_are_rejected(self):
        for text in (
            f"Xטלפון: {VALID_PHONE}",
            f"טלפוןX: {VALID_PHONE}",
            f"myEMAIL: {VALID_EMAIL}",
            f"EMAIL2: {VALID_EMAIL}",
        ):
            with self.subTest(text=text):
                self.assertEqual((), find_marker_value_relations(text))

    def test_overlapping_marker_variants_keep_longest(self):
        text = f"ת.ז.: {VALID_ID}"
        relation = find_marker_value_relations(text)[0]
        self.assertEqual("ת.ז.", text[relation.marker_start : relation.marker_end])

    def test_nearest_compatible_marker_wins(self):
        text = f"טלפון: טלפון: {VALID_PHONE}"
        relation = find_marker_value_relations(text)[0]
        self.assertEqual(text.rindex("טלפון"), relation.marker_start)

    def test_multiple_pairs_return_deterministic_source_order(self):
        text = f"טלפון: {VALID_PHONE}; אימייל: {VALID_EMAIL}; ת.ז.: {VALID_ID}"
        relations = find_marker_value_relations(text)
        self.assertEqual(["phone", "email", "israeli_id"], [item.pii_class for item in relations])
        self.assertEqual(relations, find_marker_value_relations(text))

    def test_records_and_repr_are_value_free_and_immutable(self):
        text = f"טלפון: {VALID_PHONE}"
        relation = find_marker_value_relations(text)[0]
        self.assertEqual(
            {
                "pii_class", "marker_start", "marker_end", "value_start", "value_end",
                "marker_detector_id", "direct_value_detector_id", "relation_detector_id",
            },
            {field.name for field in fields(MarkerValueRelation)},
        )
        self.assertNotIn(VALID_PHONE, repr(relation))
        with self.assertRaises((AttributeError, TypeError)):
            relation.marker_start = 99

    def test_generated_evidence_is_schema_compatible(self):
        text = f"טלפון: {VALID_PHONE}"
        relation = find_marker_value_relations(text)[0]
        direct_match = find_direct_value_matches(text)[0]
        direct_record = make_direct_value_evidence(
            direct_match,
            "direct-value-001",
            {"type": "bbox", "coordinates": [40, 10, 90, 30]},
        )
        marker_record, relation_record = make_marker_relation_evidence(
            relation,
            "marker-001",
            "direct-value-001",
            "relation-001",
            {"type": "bbox", "coordinates": [10, 10, 35, 30]},
        )
        candidate = {
            "schema_version": 1,
            "candidate_id": "synthetic-candidate-001",
            "proposed_class": "phone",
            "geometry": {"type": "bbox", "coordinates": [10, 10, 90, 30]},
            "disposition": "auto_mask",
            "detector_version": "synthetic-relation-candidate-v0",
            "evidence": [marker_record, direct_record, relation_record],
            "ambiguity_reason": None,
        }
        self.assertIsNone(validate_candidate(candidate, 100, 80))
        self.assertEqual("marker", marker_record["family"])
        self.assertEqual("marker_to_value", relation_record["relation"]["relation_type"])

    def test_optional_geometry_is_defensively_copied(self):
        relation = find_marker_value_relations(f"טלפון: {VALID_PHONE}")[0]
        geometry = {"type": "bbox", "coordinates": [1, 2, 3, 4]}
        original = copy.deepcopy(geometry)
        marker_record, _ = make_marker_relation_evidence(
            relation, "marker-001", "direct-001", "relation-001", geometry
        )
        marker_record["geometry"]["coordinates"][0] = 99
        self.assertEqual(original, geometry)

    def test_empty_and_non_string_inputs_fail_closed(self):
        self.assertEqual((), find_marker_value_relations(""))
        for value in (None, b"text", ["text"], 123):
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "text must be a string"):
                find_marker_value_relations(value)

    def test_repeated_calls_do_not_mutate_input(self):
        text = f"IBAN: {VALID_IBAN}; email: {VALID_EMAIL}"
        original = copy.deepcopy(text)
        first = find_marker_value_relations(text)
        for _ in range(10):
            self.assertEqual(first, find_marker_value_relations(text))
        self.assertEqual(original, text)


if __name__ == "__main__":
    unittest.main()
