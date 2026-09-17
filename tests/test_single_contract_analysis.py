import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from contract_checker.gemini_engine import (
    GeminiAuthenticationError,
    GeminiRateLimitError,
    GeminiResponseError,
)
from contract_checker.schemas import ContractAuditResult
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

    def test_cli_sets_known_advisory_loggers_to_error(self):
        self.assertEqual(logging.getLogger("streamlit").level, logging.ERROR)
        self.assertEqual(
            logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").level,
            logging.ERROR,
        )
        self.assertEqual(logging.getLogger("google_genai.models").level, logging.ERROR)

    def test_auto_route_falls_from_36_to_37_without_user_choice(self):
        calls = []

        def analyze_fn(*, redacted_text, api_key, model):
            calls.append(model)
            if model == "gemini-3.6-flash":
                raise GeminiResponseError("overloaded")
            return FakeResult()

        result, model, attempts = runner.analyze_with_auto_route(
            "sanitized", "key", analyze_fn, status_fn=lambda _message: None
        )
        self.assertIsInstance(result, FakeResult)
        self.assertEqual(model, "gemini-3.7-flash")
        self.assertEqual(calls, ["gemini-3.6-flash", "gemini-3.7-flash"])
        self.assertEqual([item["status"] for item in attempts], ["FAILED", "OK"])
        self.assertEqual([item["cycle"] for item in attempts], [1, 1])

    def test_auto_route_repeats_full_cycle_until_success(self):
        calls = []
        sleeps = []
        statuses = []

        def analyze_fn(*, redacted_text, api_key, model):
            calls.append(model)
            if len(calls) <= len(runner.AUTO_MODEL_ROUTE):
                raise GeminiResponseError("temporary")
            return FakeResult()

        result, model, attempts = runner.analyze_with_auto_route(
            "sanitized",
            "key",
            analyze_fn,
            sleep_fn=sleeps.append,
            status_fn=statuses.append,
        )

        self.assertIsInstance(result, FakeResult)
        self.assertEqual(model, "gemini-3.6-flash")
        self.assertEqual(
            calls,
            [
                "gemini-3.6-flash",
                "gemini-3.7-flash",
                "gemini-3.5-flash",
                "gemini-3.6-flash",
            ],
        )
        self.assertEqual(sleeps, [runner.RETRY_CYCLE_DELAY_SECONDS])
        self.assertEqual([item["cycle"] for item in attempts], [1, 1, 1, 2])
        self.assertEqual([item["status"] for item in attempts], ["FAILED", "FAILED", "FAILED", "OK"])
        self.assertTrue(any("Повтор через" in message for message in statuses))

    def test_full_rate_limit_cycle_uses_long_cooldown(self):
        calls = []
        sleeps = []
        statuses = []

        def analyze_fn(*, redacted_text, api_key, model):
            calls.append(model)
            if len(calls) <= len(runner.AUTO_MODEL_ROUTE):
                raise GeminiRateLimitError("rate limit")
            return FakeResult()

        result, model, attempts = runner.analyze_with_auto_route(
            "sanitized",
            "key",
            analyze_fn,
            sleep_fn=sleeps.append,
            status_fn=statuses.append,
        )

        self.assertIsInstance(result, FakeResult)
        self.assertEqual(model, "gemini-3.6-flash")
        self.assertEqual(sleeps, [runner.RATE_LIMIT_CYCLE_DELAY_SECONDS])
        self.assertEqual([item["cycle"] for item in attempts], [1, 1, 1, 2])
        self.assertTrue(any("rate limit" in message for message in statuses))
        self.assertTrue(any("300" in message for message in statuses))

    def test_authentication_failure_aborts_without_fallback(self):
        calls = []
        sleeps = []

        def analyze_fn(*, redacted_text, api_key, model):
            calls.append(model)
            raise GeminiAuthenticationError("auth")

        with self.assertRaises(GeminiAuthenticationError):
            runner.analyze_with_auto_route(
                "sanitized",
                "key",
                analyze_fn,
                sleep_fn=sleeps.append,
                status_fn=lambda _message: None,
            )
        self.assertEqual(calls, ["gemini-3.6-flash"])
        self.assertEqual(sleeps, [])

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
            "בין: שיר דנצינגר\n"
            "ת.ז. 123456789\n"
            "לבין: אנה איסקוביץ ת.ז. 987654321\n"
            "לפיכך הוסכם, הוצהר:והותנה בין הצדדים כדלקמן\n"
            "התשלום יימסר למשכיר שיר דנצינגר בהתאם להסכם."
        )
        tokens = runner._header_person_tokens(raw)
        body = runner._trim_identity_zones(raw)
        redacted, count = runner._redact_header_names(body, tokens)
        self.assertGreaterEqual(count, 2)
        self.assertNotIn("דנצינגר", redacted)
        self.assertIn(runner.NAME_PLACEHOLDER, redacted)

    def test_residual_pii_gate_detects_values_and_header_names(self):
        findings = runner.residual_pii_findings(
            "המשכיר 050-1234567 person@example.com 123456789 IL121234567890123456",
            {"דנצינגר"},
        )
        self.assertIn("phone", findings)
        self.assertIn("email", findings)
        self.assertIn("id", findings)
        self.assertIn("iban", findings)

        self.assertEqual(
            runner.residual_pii_findings("המשכיר דנצינגר", {"דנצינגר"}),
            ["header_name"],
        )

    def test_image_only_pdf_fails_closed_without_ocr(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scan.pdf"
            document = pymupdf.open()
            document.new_page()
            document.save(path)
            document.close()
            with self.assertRaisesRegex(RuntimeError, "OCR is required"):
                runner.extract_pdf_text(path)

    def test_real_contract_guardrails_keep_evidence_but_remove_ungated_layers(self):
        result = ContractAuditResult.model_validate(
            {
                "risk_profile": "issues_to_clarify",
                "risk_profile_summary_ru": "Есть вопросы для уточнения.",
                "document_quality": {"usable": True, "completeness": "high", "problems": []},
                "clauses": [],
                "risks": [
                    {
                        "title_ru": "Широкий механизм",
                        "level": "yellow",
                        "page": 1,
                        "source_quote_he": "",
                        "evidence_block_ids": ["P1-B01"],
                        "explanation_ru": "Нужно сопоставить связанные пункты.",
                        "requested_change_ru": "Добавить 14 дней на исправление.",
                    }
                ],
                "financial_hints": [
                    {
                        "title_ru": "Обеспечение",
                        "category": "guarantee",
                        "page": 1,
                        "source_quote_he": "",
                        "evidence_block_ids": ["P1-B01"],
                        "explanation_ru": "Сумма указана в договоре.",
                        "checklist_ru": [],
                        "amount_detected": "20,000 NIS",
                        "comparison_ru": "Обычно 2-3 месяца аренды.",
                        "confidence": 0.9,
                    }
                ],
                "missing_clauses": [
                    {
                        "title_ru": "Страхование строения",
                        "explanation_ru": "Желательная оговорка отсутствует.",
                        "importance": "yellow",
                        "requested_change_ru": "Добавить страхование.",
                    }
                ],
                "unclear_fragments": [],
                "questions_to_agent": [],
                "proposed_changes": [
                    {
                        "title_ru": "Новый срок",
                        "source_quote_he": None,
                        "evidence_block_ids": ["P1-B01"],
                        "proposed_text_ru": "Добавить срок 48 часов.",
                        "priority": "yellow",
                    }
                ],
            }
        )

        guarded = runner.apply_real_contract_output_guardrails(result)

        self.assertEqual(len(guarded.risks), 1)
        self.assertEqual(guarded.risks[0].evidence_block_ids, ["P1-B01"])
        self.assertIsNone(guarded.risks[0].requested_change_ru)
        self.assertEqual(guarded.financial_hints[0].amount_detected, "20,000 NIS")
        self.assertIsNone(guarded.financial_hints[0].comparison_ru)
        self.assertEqual(guarded.missing_clauses, [])
        self.assertEqual(guarded.proposed_changes, [])

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
