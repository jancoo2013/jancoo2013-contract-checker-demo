import copy
import unittest

from research.hebrew_contract_ocr.pii_candidate_evidence import validate_candidate
from research.hebrew_contract_ocr.pii_visual_sensitive_regions import (
    VISUAL_KINDS,
    VisualSensitiveRegion,
    make_visual_relation_evidence,
    record_visual_sensitive_region,
)


def marker_evidence():
    return {
        "evidence_id": "marker-1",
        "family": "marker",
        "detector_id": "marker-phone-v0",
        "geometry": {"type": "bbox", "coordinates": [5, 10, 25, 25]},
    }


def candidate(records, disposition="local_review", proposed_class="signature"):
    return {
        "schema_version": 1,
        "candidate_id": "candidate-visual-1",
        "proposed_class": proposed_class,
        "geometry": {"type": "bbox", "coordinates": [30, 10, 80, 35]},
        "disposition": disposition,
        "detector_version": "synthetic-decision-v0",
        "evidence": records,
        "ambiguity_reason": "Visual relation requires compatible detector semantics."
        if disposition == "local_review"
        else None,
    }


class PiiVisualSensitiveRegionTests(unittest.TestCase):
    def test_all_approved_visual_kinds_are_recorded(self):
        self.assertEqual(
            {"filled_field", "handwriting", "signature", "initials", "stamp"},
            VISUAL_KINDS,
        )
        for visual_kind in sorted(VISUAL_KINDS):
            with self.subTest(visual_kind=visual_kind):
                region = record_visual_sensitive_region(visual_kind, [30, 10, 80, 35], 100, 80)
                self.assertEqual(visual_kind, region.visual_kind)
                self.assertEqual((30, 10, 80, 35), (region.x0, region.y0, region.x1, region.y1))
                self.assertEqual(f"visual-evidence-{visual_kind.replace('_', '-')}-v0", region.detector_id)

    def test_unknown_and_non_string_kinds_fail_closed(self):
        for rejected in ("table_border", "underline", "strikethrough", "printed_paragraph"):
            with self.subTest(rejected=rejected):
                with self.assertRaisesRegex(ValueError, "unsupported visual_kind"):
                    record_visual_sensitive_region(rejected, [1, 1, 5, 5], 10, 10)
        with self.assertRaisesRegex(TypeError, "visual_kind"):
            record_visual_sensitive_region(["signature"], [1, 1, 5, 5], 10, 10)

    def test_bbox_must_be_integer_positive_and_in_bounds(self):
        invalid = (
            ([1, 1, 1, 5], "positive in-bounds"),
            ([-1, 1, 5, 5], "positive in-bounds"),
            ([1, 1, 11, 5], "positive in-bounds"),
            ([True, 1, 5, 5], "four integers"),
            ([1, 1, 5], "four integers"),
        )
        for bbox, message in invalid:
            with self.subTest(bbox=bbox):
                with self.assertRaisesRegex(ValueError, message):
                    record_visual_sensitive_region("signature", bbox, 10, 10)
        with self.assertRaisesRegex(TypeError, "bbox"):
            record_visual_sensitive_region("signature", object(), 10, 10)

    def test_image_dimensions_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            record_visual_sensitive_region("signature", [1, 1, 5, 5], 0, 10)
        with self.assertRaisesRegex(TypeError, "integers"):
            record_visual_sensitive_region("signature", [1, 1, 5, 5], True, 10)

    def test_region_is_immutable_and_value_free(self):
        region = record_visual_sensitive_region("handwriting", [30, 10, 80, 35], 100, 80)
        with self.assertRaises((AttributeError, TypeError)):
            region.x0 = 0
        self.assertNotIn("text", region.__dataclass_fields__)
        self.assertNotIn("value", region.__dataclass_fields__)
        self.assertNotIn("pixels", region.__dataclass_fields__)
        self.assertNotIn("synthetic-secret", repr(region))

    def test_evidence_has_exact_schema_fields_and_offsets(self):
        region = record_visual_sensitive_region("signature", [30, 10, 80, 35], 100, 80)
        visual, relation = make_visual_relation_evidence(region, "marker-1", "visual-1", "relation-1")
        self.assertEqual(
            {
                "evidence_id": "visual-1",
                "family": "visual_sensitive_region",
                "detector_id": "visual-evidence-signature-v0",
                "geometry": {"type": "bbox", "coordinates": [30, 10, 80, 35]},
            },
            visual,
        )
        self.assertEqual(
            {
                "evidence_id": "relation-1",
                "family": "relation",
                "detector_id": "marker-to-visual-v0",
                "relation": {
                    "relation_type": "marker_to_visual",
                    "source_evidence_id": "marker-1",
                    "target_evidence_id": "visual-1",
                },
            },
            relation,
        )

    def test_generated_records_validate_for_local_review_with_existing_marker(self):
        region = record_visual_sensitive_region("signature", [30, 10, 80, 35], 100, 80)
        visual, relation = make_visual_relation_evidence(region, "marker-1", "visual-1", "relation-1")
        self.assertIsNone(validate_candidate(candidate([marker_evidence(), visual, relation]), 100, 80))

    def test_signature_visual_with_phone_marker_cannot_auto_mask(self):
        region = record_visual_sensitive_region("signature", [30, 10, 80, 35], 100, 80)
        visual, relation = make_visual_relation_evidence(region, "marker-1", "visual-1", "relation-1")
        with self.assertRaisesRegex(ValueError, "incompatible marker and target"):
            validate_candidate(
                candidate([marker_evidence(), visual, relation], "auto_mask", "phone"),
                100,
                80,
            )

    def test_helper_does_not_create_marker_candidate_or_disposition(self):
        region = record_visual_sensitive_region("stamp", [30, 10, 80, 35], 100, 80)
        records = make_visual_relation_evidence(region, "marker-1", "visual-1", "relation-1")
        self.assertEqual(2, len(records))
        self.assertNotIn("marker", {record["family"] for record in records})
        for record in records:
            self.assertNotIn("candidate_id", record)
            self.assertNotIn("disposition", record)
            self.assertNotIn("raw_text", record)
            self.assertNotIn("value", record)

    def test_unlinked_visual_evidence_still_cannot_auto_mask(self):
        region = record_visual_sensitive_region("signature", [30, 10, 80, 35], 100, 80)
        visual, _relation = make_visual_relation_evidence(region, "marker-1", "visual-1", "relation-1")
        with self.assertRaisesRegex(ValueError, "auto_mask requires"):
            validate_candidate(candidate([visual], "auto_mask"), 100, 80)

    def test_output_mutation_does_not_change_region_or_later_calls(self):
        region = record_visual_sensitive_region("initials", [30, 10, 80, 35], 100, 80)
        first = make_visual_relation_evidence(region, "marker-1", "visual-1", "relation-1")
        expected = copy.deepcopy(first)
        first[0]["geometry"]["coordinates"][0] = 0
        self.assertEqual(expected, make_visual_relation_evidence(region, "marker-1", "visual-1", "relation-1"))

    def test_repeated_calls_are_deterministic(self):
        region = record_visual_sensitive_region("filled_field", (30, 10, 80, 35), 100, 80)
        expected = make_visual_relation_evidence(region, "marker-1", "visual-1", "relation-1")
        for _ in range(10):
            self.assertEqual(expected, make_visual_relation_evidence(region, "marker-1", "visual-1", "relation-1"))

    def test_helper_types_fail_closed(self):
        region = record_visual_sensitive_region("signature", [30, 10, 80, 35], 100, 80)
        with self.assertRaisesRegex(TypeError, "region"):
            make_visual_relation_evidence(object(), "marker-1", "visual-1", "relation-1")
        for index, ids in enumerate(
            ((1, "visual-1", "relation-1"), ("marker-1", 1, "relation-1"), ("marker-1", "visual-1", 1))
        ):
            with self.subTest(index=index):
                with self.assertRaises(TypeError):
                    make_visual_relation_evidence(region, *ids)

    def test_repr_and_records_contain_no_raw_visual_payload(self):
        region = record_visual_sensitive_region("handwriting", [30, 10, 80, 35], 100, 80)
        records = make_visual_relation_evidence(region, "marker-1", "visual-1", "relation-1")
        combined = repr((region, records))
        for forbidden in ("raw_text", "normalized_value", "image_bytes", "pixels", "hash"):
            self.assertNotIn(forbidden, combined)

    def test_region_type_is_exported(self):
        region = record_visual_sensitive_region("signature", [30, 10, 80, 35], 100, 80)
        self.assertIsInstance(region, VisualSensitiveRegion)


if __name__ == "__main__":
    unittest.main()
