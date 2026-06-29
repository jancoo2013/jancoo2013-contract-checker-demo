"""Tests for deterministic Hebrew text PII redaction v0.2."""

from __future__ import annotations

import unittest

from contract_checker.redaction import (
    ADDRESS_PLACEHOLDER,
    BANK_PLACEHOLDER,
    EMAIL_PLACEHOLDER,
    GUARANTOR_PLACEHOLDER,
    ID_PLACEHOLDER,
    NAME_PLACEHOLDER,
    PHONE_PLACEHOLDER,
    SIGNATURE_PLACEHOLDER,
    redact_personal_data,
    redact_personal_data_with_report,
)


SYNTHETIC_CONTRACT = """
שם המשכיר: דוד כהן, ת.ז. 123456789, טלפון 050-123-4567, כתובת: הרצל 10 תל אביב
שם השוכר * משה לוי
דואר אלקטרוני — tenant@example.com
נייד 052-765-4321
פרטי בנק: בנק לאומי חשבון 123456 סניף 800
שם הערב: יוסי ערב
ת.ז. ערב: 987654321
מיופה כוח — רונית כהן
סוכן: אבי מתווך
חתימה ________
דמי שכירות יהיו 3,500 ₪ לחודש.
פיקדון בסך 7,000 ₪.
שיק ביטחון בסך 7,500 ₪ מספר שיק 765432.
שטר חוב בסך 40,000 ₪.
המשכיר יהיה אחראי לתיקונים שאינם נגרמו על ידי השוכר.
השוכר רשאי להביא שוכר חלופי.
"""


class TextRedactionV02Tests(unittest.TestCase):
    def test_personal_fields_are_redacted_and_financial_terms_remain(self) -> None:
        result = redact_personal_data_with_report(SYNTHETIC_CONTRACT)
        redacted = result.redacted_text

        for placeholder in (
            NAME_PLACEHOLDER,
            ID_PLACEHOLDER,
            PHONE_PLACEHOLDER,
            EMAIL_PLACEHOLDER,
            ADDRESS_PLACEHOLDER,
            BANK_PLACEHOLDER,
            GUARANTOR_PLACEHOLDER,
            SIGNATURE_PLACEHOLDER,
        ):
            self.assertIn(placeholder, redacted)

        for original_value in (
            "דוד כהן",
            "משה לוי",
            "123456789",
            "050-123-4567",
            "tenant@example.com",
            "052-765-4321",
            "הרצל 10",
            "לאומי",
            "123456",
            "800",
            "יוסי ערב",
            "987654321",
            "רונית כהן",
            "אבי מתווך",
            "765432",
        ):
            self.assertNotIn(original_value, redacted)

        for preserved_text in (
            "דמי שכירות",
            "3,500 ₪",
            "פיקדון",
            "7,000 ₪",
            "שיק ביטחון",
            "7,500 ₪",
            "שטר חוב",
            "40,000 ₪",
            "המשכיר יהיה אחראי",
            "השוכר רשאי להביא שוכר חלופי",
        ):
            self.assertIn(preserved_text, redacted)

    def test_report_contains_only_safe_counts(self) -> None:
        result = redact_personal_data_with_report(SYNTHETIC_CONTRACT)
        report = result.report

        self.assertGreaterEqual(report.names, 4)
        self.assertGreaterEqual(report.ids, 1)
        self.assertGreaterEqual(report.phones, 2)
        self.assertGreaterEqual(report.emails, 1)
        self.assertGreaterEqual(report.addresses, 1)
        self.assertGreaterEqual(report.bank_details, 2)
        self.assertGreaterEqual(report.guarantor_details, 2)
        self.assertGreaterEqual(report.signatures, 1)
        self.assertEqual(
            report.total,
            report.names
            + report.ids
            + report.phones
            + report.emails
            + report.addresses
            + report.bank_details
            + report.guarantor_details
            + report.signatures,
        )

        report_text = repr(report) + str(report.__dict__)
        for original_value in (
            "דוד כהן",
            "משה לוי",
            "123456789",
            "050-123-4567",
            "tenant@example.com",
            "הרצל 10",
            "לאומי",
            "יוסי ערב",
            "987654321",
            "רונית כהן",
            "אבי מתווך",
        ):
            self.assertNotIn(original_value, report_text)

    def test_unrelated_legal_text_with_party_words_is_not_destroyed(self) -> None:
        legal_text = (
            "המשכיר יהיה אחראי לתיקונים שאינם נגרמו על ידי השוכר.\n"
            "השוכר ישלם ועד בית וארנונה לפי צריכה.\n"
            "דמי שכירות יהיו 3,500 ₪ לחודש.\n"
        )

        self.assertEqual(redact_personal_data(legal_text), legal_text)

    def test_backward_compatible_redact_personal_data_returns_string(self) -> None:
        redacted = redact_personal_data(SYNTHETIC_CONTRACT)

        self.assertIsInstance(redacted, str)
        self.assertIn(NAME_PLACEHOLDER, redacted)


if __name__ == "__main__":
    unittest.main()
