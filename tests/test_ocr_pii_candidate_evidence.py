import copy
import unittest

from research.hebrew_contract_ocr.pii_candidate_evidence import (
    candidate_validation_errors,
    validate_candidate,
)


def geometry(x0=10, y0=10, x1=40, y1=30):
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
        "detector_id": detector_id or (
            defaults.get(family, "synthetic-detector-v0")
            if isinstance(family, str)
            else "synthetic-detector-v0"
        ),
        **extra,
    }


def candidate(disposition="preserve", records=None, ambiguity_reason=None):
    return {
        "schema_version": 1,
        "candidate_id": "candidate-001",
        "proposed_class": "phone",
        "geometry": geometry(),
        "disposition": disposition,
        "detector_version": "candidate-detector-v0",
        "evidence": [] if records is None else records,
        "ambiguity_reason": ambiguity_reason,
    }


class PiiCandidateEvidenceTests(unittest.TestCase):
    def assert_valid(self, value):
        self.assertIsNone(validate_candidate(value, 100, 80))
        self.assertEqual((), candidate_validation_errors(value, 100, 80))

    def assert_invalid(self, value, message=None):
        with self.assertRaisesRegex(ValueError, message or "."):
            validate_candidate(value, 100, 80)

    def test_direct_value_allows_auto_mask(self):
        self.assert_valid(candidate("auto_mask", [evidence("value-1", "direct_value", geometry=geometry())]))

    def test_marker_to_visual_relation_allows_auto_mask(self):
        records = [
            evidence("marker-1", "marker"),
            evidence("visual-1", "visual_sensitive_region", geometry=geometry()),
            evidence(
                "relation-1",
                "relation",
                relation={
                    "relation_type": "marker_to_visual",
                    "source_evidence_id": "marker-1",
                    "target_evidence_id": "visual-1",
                },
            ),
        ]
        self.assert_valid(candidate("auto_mask", records))

    def test_auto_mask_rejects_class_mismatched_direct_value(self):
        value = candidate("auto_mask", [evidence("value-1", "direct_value", geometry=geometry())])
        value["proposed_class"] = "email"
        self.assert_invalid(value, "incompatible with proposed_class")

    def test_auto_mask_rejects_phone_marker_linked_to_signature(self):
        records = [
            evidence("marker-1", "marker"),
            evidence(
                "visual-1",
                "visual_sensitive_region",
                detector_id="visual-evidence-signature-v0",
                geometry=geometry(),
            ),
            evidence(
                "relation-1",
                "relation",
                relation={
                    "relation_type": "marker_to_visual",
                    "source_evidence_id": "marker-1",
                    "target_evidence_id": "visual-1",
                },
            ),
        ]
        self.assert_invalid(candidate("auto_mask", records), "incompatible marker and target")

    def test_auto_mask_rejects_unapproved_direct_detector(self):
        records = [
            evidence(
                "value-1",
                "direct_value",
                detector_id="unapproved-digits-v0",
                geometry=geometry(),
            )
        ]
        value = candidate("auto_mask", records)
        value["proposed_class"] = "other_likely_pii"
        self.assert_invalid(value, "unapproved direct_value detector_id")

    def test_local_review_requires_evidence_and_reason(self):
        self.assert_valid(
            candidate(
                "local_review",
                [evidence("context-1", "weak_layout_context")],
                "Synthetic context is insufficient for automatic masking.",
            )
        )
        self.assert_invalid(candidate("local_review", [], "Ambiguous."), "at least one evidence")
        self.assert_invalid(
            candidate("local_review", [evidence("context-1", "weak_layout_context")]),
            "non-empty ambiguity_reason",
        )

    def test_preserve_is_valid_without_evidence(self):
        self.assert_valid(candidate())

    def test_weak_layout_context_never_allows_auto_mask(self):
        self.assert_invalid(
            candidate("auto_mask", [evidence("position-1", "weak_layout_context")]),
            "auto_mask requires",
        )
        weak_facts = [
            evidence("page-position", "weak_layout_context"),
            evidence("page-role", "weak_layout_context"),
            evidence("alignment", "weak_layout_context"),
            evidence("short-line", "weak_layout_context"),
            evidence("generic-digits", "weak_layout_context"),
        ]
        self.assert_invalid(candidate("auto_mask", weak_facts), "auto_mask requires")

    def test_unlinked_marker_or_visual_never_allows_auto_mask(self):
        self.assert_invalid(candidate("auto_mask", [evidence("marker-1", "marker")]), "auto_mask requires")
        self.assert_invalid(
            candidate("auto_mask", [evidence("visual-1", "visual_sensitive_region")]),
            "auto_mask requires",
        )

    def test_broken_self_referencing_and_wrong_endpoint_relations_fail(self):
        missing = candidate(
            "auto_mask",
            [
                evidence("marker-1", "marker"),
                evidence(
                    "relation-1",
                    "relation",
                    relation={
                        "relation_type": "marker_to_visual",
                        "source_evidence_id": "marker-1",
                        "target_evidence_id": "missing-1",
                    },
                ),
            ],
        )
        self.assert_invalid(missing, "references missing evidence")

        self_ref = candidate(
            "auto_mask",
            [
                evidence("marker-1", "marker"),
                evidence(
                    "relation-1",
                    "relation",
                    relation={
                        "relation_type": "marker_to_visual",
                        "source_evidence_id": "marker-1",
                        "target_evidence_id": "marker-1",
                    },
                ),
            ],
        )
        self.assert_invalid(self_ref, "cannot self-reference")

        invalid_endpoint = copy.deepcopy(missing)
        invalid_endpoint["evidence"][1]["relation"]["target_evidence_id"] = ["visual-1"]
        self.assert_invalid(invalid_endpoint, "invalid target_evidence_id")

        wrong = candidate(
            "auto_mask",
            [
                evidence("marker-1", "marker"),
                evidence("marker-2", "marker"),
                evidence(
                    "relation-1",
                    "relation",
                    relation={
                        "relation_type": "marker_to_visual",
                        "source_evidence_id": "marker-1",
                        "target_evidence_id": "marker-2",
                    },
                ),
            ],
        )
        self.assert_invalid(wrong, "endpoints do not match")

    def test_duplicate_evidence_ids_fail(self):
        self.assert_invalid(
            candidate("preserve", [evidence("same-id", "marker"), evidence("same-id", "marker")]),
            "duplicate evidence_id",
        )

    def test_unknown_fields_enums_and_raw_values_fail(self):
        unknown_candidate = candidate()
        unknown_candidate["raw_text"] = "synthetic"
        self.assert_invalid(unknown_candidate, "unknown fields: raw_text")

        unknown_disposition = candidate()
        unknown_disposition["disposition"] = "mask"
        self.assert_invalid(unknown_disposition, "unknown disposition")

        unknown_class = candidate()
        unknown_class["proposed_class"] = "generic_digits"
        self.assert_invalid(unknown_class, "unknown proposed_class")

        unknown_family = candidate("preserve", [evidence("value-1", "page_position")])
        self.assert_invalid(unknown_family, "unknown family")

        non_string_family = candidate("preserve", [evidence("value-1", ["direct_value"])])
        self.assert_invalid(non_string_family, "unknown family")

        raw_value = candidate("preserve", [evidence("value-1", "direct_value", value="000000000")])
        self.assert_invalid(raw_value, "unknown fields: value")

    def test_missing_fields_and_relation_data_placement_fail(self):
        missing = candidate()
        del missing["candidate_id"]
        self.assert_invalid(missing, "missing fields: candidate_id")
        self.assert_invalid(
            candidate("preserve", [evidence("marker-1", "marker", relation={})]),
            "allowed only for relation evidence",
        )
        self.assert_invalid(
            candidate("preserve", [evidence("relation-1", "relation")]),
            "requires relation data",
        )

    def test_invalid_identifiers_and_booleans_fail(self):
        invalid_id = candidate()
        invalid_id["candidate_id"] = "bad id"
        self.assert_invalid(invalid_id, "invalid candidate_id")

        bool_schema = candidate()
        bool_schema["schema_version"] = True
        self.assert_invalid(bool_schema, "schema_version must be integer")

        bool_geometry = candidate()
        bool_geometry["geometry"] = geometry(True, 1, 10, 10)
        self.assert_invalid(bool_geometry, "coordinates must be four integers")

        invalid_detector = candidate(
            "auto_mask",
            [evidence("value-1", "direct_value", detector_id=["bad"], geometry=geometry())],
        )
        self.assert_invalid(invalid_detector, "invalid detector_id")
        with self.assertRaisesRegex(ValueError, "positive integers"):
            validate_candidate(candidate(), True, 80)

    def test_empty_out_of_bounds_and_invalid_geometry_fail(self):
        empty = candidate()
        empty["geometry"] = geometry(10, 10, 10, 20)
        self.assert_invalid(empty, "positive in-bounds area")

        outside = candidate()
        outside["geometry"] = geometry(10, 10, 101, 20)
        self.assert_invalid(outside, "positive in-bounds area")

        evidence_outside = candidate("preserve", [evidence("marker-1", "marker", geometry=geometry(0, 0, 101, 2))])
        self.assert_invalid(evidence_outside, "positive in-bounds area")

        zero_area_polygon = candidate()
        zero_area_polygon["geometry"] = {"type": "polygon", "coordinates": [[1, 1], [2, 2], [3, 3]]}
        self.assert_invalid(zero_area_polygon, "positive area")

    def test_validation_is_deterministic_and_does_not_mutate_input(self):
        value = candidate("auto_mask", [evidence("weak-1", "weak_layout_context")])
        original = copy.deepcopy(value)
        first = candidate_validation_errors(value, 100, 80)
        for _ in range(10):
            self.assertEqual(first, candidate_validation_errors(value, 100, 80))
        self.assertEqual(original, value)


if __name__ == "__main__":
    unittest.main()
