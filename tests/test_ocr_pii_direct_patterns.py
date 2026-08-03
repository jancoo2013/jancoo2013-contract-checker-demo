import copy
from dataclasses import fields
import unittest

from research.hebrew_contract_ocr.pii_candidate_evidence import validate_candidate
from research.hebrew_contract_ocr.pii_direct_patterns import (
    DirectValueMatch,
    find_direct_value_matches,
    make_direct_value_evidence,
)


VALID_ID = "123456782"
VALID_IBAN = "IL88 1234 5678 9012 3456 789"


def candidate(match, record):
    return {
        "schema_version": 1,
        "candidate_id": "synthetic-candidate-001",
        "proposed_class": match.pii_class,
        "geometry": {"type": "bbox", "coordinates": [10, 10, 80, 30]},
        "disposition": "auto_mask",
        "detector_version": "synthetic-direct-candidate-v0",
        "evidence": [record],
        "ambiguity_reason": None,
    }


class PiiDirectPatternsTests(unittest.TestCase):
    def matches_for(self, text, pii_class):
        return [match for match in find_direct_value_matches(text) if match.pii_class == pii_class]

    def test_valid_email_has_exact_original_span(self):
        text = "Synthetic contact: tenant@example.test."
        match = self.matches_for(text, "email")[0]
        self.assertEqual("tenant@example.test", text[match.start : match.end])
        self.assertEqual("direct-email-v0", match.detector_id)

    def test_invalid_email_shapes_are_rejected(self):
        for text in ("a@b", "a @example.test", "a@example", "a..b@example.test", ".a@example.test"):
            with self.subTest(text=text):
                self.assertEqual([], self.matches_for(text, "email"))

    def test_valid_israeli_local_phone_is_detected(self):
        text = "Synthetic phone 050-123-4567."
        match = self.matches_for(text, "phone")[0]
        self.assertEqual("050-123-4567", text[match.start : match.end])
        self.assertEqual("direct-israeli-phone-v0", match.detector_id)

    def test_valid_plus_972_phone_is_detected(self):
        text = "Synthetic phone +972 54-123-4567."
        match = self.matches_for(text, "phone")[0]
        self.assertEqual("+972 54-123-4567", text[match.start : match.end])

    def test_invalid_phone_prefixes_and_lengths_are_rejected(self):
        for text in (
            "060-123-4567",
            "050-123-456",
            "+972 64-123-4567",
            "+972 54-123-45678",
            "12-050-123-4567-34",
            "12 050-123-4567 34",
        ):
            with self.subTest(text=text):
                self.assertEqual([], self.matches_for(text, "phone"))

    def test_valid_israeli_id_with_check_digit_is_detected(self):
        text = f"Synthetic ID {VALID_ID}."
        match = self.matches_for(text, "israeli_id")[0]
        self.assertEqual(VALID_ID, text[match.start : match.end])
        self.assertEqual("direct-israeli-id-v0", match.detector_id)

    def test_invalid_israeli_id_check_digit_is_rejected(self):
        for text in ("Synthetic ID 123456783.", "Synthetic ID 000000000."):
            with self.subTest(text=text):
                self.assertEqual([], self.matches_for(text, "israeli_id"))
        zero_padded = "Synthetic ID 000000018."
        match = self.matches_for(zero_padded, "israeli_id")[0]
        self.assertEqual("000000018", zero_padded[match.start : match.end])

    def test_ambiguous_numeric_categories_are_not_ids(self):
        text = "Date 01/02/2025; sum 7,500; clause 3.2; notice 30; generic 111111111."
        self.assertEqual([], self.matches_for(text, "israeli_id"))

    def test_valid_israeli_iban_is_detected_with_original_span(self):
        text = f"Synthetic bank identifier: {VALID_IBAN}."
        match = self.matches_for(text, "bank_identifier")[0]
        self.assertEqual(VALID_IBAN, text[match.start : match.end])
        self.assertEqual("direct-israeli-iban-v0", match.detector_id)

    def test_invalid_israeli_iban_check_digits_are_rejected(self):
        for text in (
            "IL89 1234 5678 9012 3456 789",
            f"123-{VALID_IBAN}-456",
            f"123 {VALID_IBAN} 456",
        ):
            with self.subTest(text=text):
                self.assertEqual([], self.matches_for(text, "bank_identifier"))

    def test_generic_account_and_cheque_numbers_are_rejected(self):
        text = "Account 123456789012; branch 321; cheque 12345678; postal 6100000."
        self.assertEqual((), find_direct_value_matches(text))

    def test_valid_iban_suppresses_overlapping_numeric_matches(self):
        matches = find_direct_value_matches(VALID_IBAN)
        self.assertEqual(1, len(matches))
        self.assertEqual("bank_identifier", matches[0].pii_class)

        email = "IL881234567890123456789@example.test"
        email_matches = find_direct_value_matches(email)
        self.assertEqual(1, len(email_matches))
        self.assertEqual("email", email_matches[0].pii_class)
        self.assertEqual(email, email[email_matches[0].start : email_matches[0].end])
        self.assertEqual(email_matches, find_direct_value_matches(email))

    def test_multiple_values_use_deterministic_source_order(self):
        text = f"{VALID_ID}; tenant@example.test; 050-123-4567"
        matches = find_direct_value_matches(text)
        self.assertEqual(["israeli_id", "email", "phone"], [match.pii_class for match in matches])
        self.assertEqual(
            sorted((match.start, match.end, match.detector_id) for match in matches),
            [(match.start, match.end, match.detector_id) for match in matches],
        )

    def test_evidence_record_is_schema_shaped_and_value_free(self):
        match = find_direct_value_matches("tenant@example.test")[0]
        geometry = {"type": "bbox", "coordinates": [10, 10, 80, 30]}
        record = make_direct_value_evidence(match, "direct-value-001", geometry)
        self.assertEqual(
            {"evidence_id", "family", "detector_id", "geometry"},
            set(record),
        )
        self.assertEqual("direct_value", record["family"])
        self.assertEqual(
            {"pii_class", "start", "end", "detector_id"},
            {field.name for field in fields(DirectValueMatch)},
        )
        self.assertNotIn("tenant@example.test", repr((match, record)))

    def test_generated_evidence_allows_auto_mask_candidate(self):
        match = find_direct_value_matches("050-123-4567")[0]
        record = make_direct_value_evidence(
            match,
            "direct-value-001",
            {"type": "bbox", "coordinates": [10, 10, 80, 30]},
        )
        self.assertIsNone(validate_candidate(candidate(match, record), 100, 80))

    def test_raw_value_or_unknown_evidence_fields_are_rejected(self):
        match = find_direct_value_matches(VALID_ID)[0]
        record = make_direct_value_evidence(match, "direct-value-001")
        for field_name in ("value", "raw_text"):
            with self.subTest(field_name=field_name):
                invalid_record = dict(record)
                invalid_record[field_name] = "synthetic-only"
                with self.assertRaisesRegex(ValueError, "unknown fields"):
                    validate_candidate(candidate(match, invalid_record), 100, 80)

    def test_non_string_input_fails_closed(self):
        for value in (None, b"text", ["text"], 123):
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "text must be a string"):
                find_direct_value_matches(value)

    def test_repeated_calls_are_identical_and_inputs_are_not_mutated(self):
        text = f"{VALID_IBAN}; tenant@example.test; {VALID_ID}"
        first = find_direct_value_matches(text)
        for _ in range(10):
            self.assertEqual(first, find_direct_value_matches(text))
        self.assertEqual((), find_direct_value_matches(""))

        geometry = {"type": "bbox", "coordinates": [1, 2, 3, 4]}
        original = copy.deepcopy(geometry)
        record = make_direct_value_evidence(first[0], "direct-value-001", geometry)
        record["geometry"]["coordinates"][0] = 99
        self.assertEqual(original, geometry)


if __name__ == "__main__":
    unittest.main()
