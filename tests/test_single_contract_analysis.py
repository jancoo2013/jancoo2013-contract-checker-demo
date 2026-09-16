import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from contract_checker.gemini_engine import GeminiAuthenticationError, GeminiResponseError
from tools import single_contract_analysis as runner


class FakeResult:
    def model_dump(self, mode="json"):
        return {"ok": True}


class SingleContractAnalysisTests(unittest.TestCase):
    def test_automatic_route_contains_36_37_then_35(self):
        self.assertEqual(
            runner.AUTO_MODEL_ROUTE,
            ("gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash"),
        )

    def test_auto_route_falls_from_36_to_37_without_user_choice(self):
        calls = []

        def analyze_fn(*, redacted_text, api_key, model):
            calls.append(model)
            if model == "gemini-3.6-flash":
                raise GeminiResponseError("overloaded")
            return FakeResult()

        result, model, attempts = runner.analyze_with_auto_route("sanitized", "key", analyze_fn)
        self.assertIsInstance(result, FakeResult)
        self.assertEqual(model, "gemini-3.7-flash")
        self.assertEqual(calls, ["gemini-3.6-flash", "gemini-3.7-flash"])
        self.assertEqual([item["status"] for item in attempts], ["FAILED", "OK"])

    def test_authentication_failure_aborts_without_fallback(self):
        calls = []

        def analyze_fn(*, redacted_text, api_key, model):
            calls.append(model)
            raise GeminiAuthenticationError("auth")

        with self.assertRaises(GeminiAuthenticationError):
            runner.analyze_with_auto_route("sanitized", "key", analyze_fn)
        self.assertEqual(calls, ["gemini-3.6-flash"])

    def test_identity_zones_are_removed_before_redaction(self):
        raw = (
            "--- СТРАНИЦА 1 ---\n"
            "שם אדם 050-1234567 person@example.com 123456789\n"
            "לפיכך הוסכם והותנה בין הצדדים כדלקמן\n"
            "המשכיר והשוכר מסכימים על דמי שכירות ותיקונים.\n"
            "ולראיה באו הצדדים על החתום\n"
            "שם אחר 050-7654321"
        )
        body = runner._trim_identity_zones(raw)
        self.assertNotIn("person@example.com", body)
        self.assertNotIn("050-1234567", body)
        self.assertNotIn("050-7654321", body)
        self.assertIn("דמי שכירות", body)

    def test_header_derived_person_names_are_redacted_in_body(self):
        raw = (
            "--- СТРАНИЦА 1 ---\n"
            "בין: שיר דנצינגר ת.ז. 123456789\n"
            "לבין: אנה איסקוביץ ת.ז. 987654321\n"
            "לפיכך הוסכם והותנה בין הצדדים כדלקמן\n"
            "התשלום יימסר למשכיר שיר דנצינגר בהתאם להסכם."
        )
        tokens = runner._header_person_tokens(raw)
        body = runner._trim_identity_zones(raw)
        redacted, count = runner._redact_header_names(body, tokens)
        self.assertGreaterEqual(count, 2)
        self.assertNotIn("שיר", redacted)
        self.assertNotIn("דנצינגר", redacted)
        self.assertIn(runner.NAME_PLACEHOLDER, redacted)

    def test_residual_pii_gate_detects_identifiers(self):
        findings = runner.residual_pii_findings(
            "המשכיר 050-1234567 person@example.com ת.ז 123456789"
        )
        self.assertIn("phone", findings)
        self.assertIn("email", findings)
        self.assertIn("id", findings)
        self.assertIn("marker:ת.ז", findings)

    def test_image_only_pdf_fails_closed_without_ocr(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scan.pdf"
            document = fitz.open()
            document.new_page()
            document.save(path)
            document.close()
            with self.assertRaisesRegex(RuntimeError, "OCR is required"):
                runner.extract_pdf_text(path)

    def test_report_does_not_store_contract_text_or_source_filename(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            runner.time, "strftime", return_value="20260916_220000"
        ):
            pdf = Path(tmp) / "person-name-contract.pdf"
            pdf.write_bytes(b"unused")
            path = runner.write_report(
                pdf,
                "gemini-3.7-flash",
                [{"model": "gemini-3.7-flash", "status": "OK"}],
                {"total": 2},
                FakeResult(),
            )
            text = path.read_text(encoding="utf-8")
        self.assertNotIn("sanitized_text", text)
        self.assertNotIn("raw_text", text)
        self.assertNotIn("person-name-contract.pdf", text)


if __name__ == "__main__":
    unittest.main()
