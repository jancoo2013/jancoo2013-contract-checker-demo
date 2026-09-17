"""Mocked tests for the Gemini-only contract audit engine."""

from __future__ import annotations

import types
import unittest
from unittest.mock import Mock, patch

from contract_checker import gemini_engine
from contract_checker.gemini_engine import (
    DEFAULT_GEMINI_MODEL,
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiRateLimitError,
    GeminiResponseError,
    analyze_contract_with_gemini,
    analyze_contract_with_gemini_debug,
)
from contract_checker.output_validator import validate_model_evidence
from contract_checker.prompt_builder import question_engine_expected_answer_fields
from contract_checker.schemas import ClauseAnalysis, ContractAuditResult, DocumentQuality, RiskItem


QUOTE = "תקופת תיקון של 14 ימים"
REDACTED_CONTRACT = f"""
הסכם שכירות בלתי מוגנת
1. המשכיר משכיר לשוכר דירה למטרת מגורים בלבד.
2. דמי שכירות יהיו 3,500 ש"ח לחודש.
3. במקרה של הפרה יסודית תינתן הודעה בכתב ו{QUOTE}.
"""


def _complete_question_engine_answers() -> list[dict[str, object]]:
    return [
        {
            "question_id": question_id,
            "status": "NOT_FOUND",
            "values": [None] * len(answer_fields),
            "evidence_block_ids": [],
        }
        for question_id, answer_fields in question_engine_expected_answer_fields().items()
    ]


def _sample_result(quote: str = QUOTE) -> ContractAuditResult:
    return ContractAuditResult(
        risk_profile="issues_to_clarify",
        risk_profile_summary_ru="Есть проверяемые условия и вопросы для уточнения.",
        document_quality=DocumentQuality(usable=True, completeness="medium", problems=[]),
        question_engine_answers=_complete_question_engine_answers(),
        clauses=[
            ClauseAnalysis(
                clause_id="breach_notice",
                page=None,
                source_quote_he=quote,
                evidence_block_ids=["P1-B04"],
                explanation_ru="Срок исправления указан.",
                category="termination",
                risk_level="normal",
                tenant_obligation=None,
                landlord_obligation=None,
                financial_effect=None,
                confidence=0.9,
            )
        ],
        risks=[
            RiskItem(
                title_ru="Проверяемый риск",
                level="yellow",
                page=None,
                source_quote_he=quote,
                evidence_block_ids=["P1-B04"],
                explanation_ru="Нужно уточнить 14 дней.",
                requested_change_ru="Сохранить 14 дней на исправление.",
            )
        ],
        missing_clauses=[],
        unclear_fragments=[],
        questions_to_agent=[],
        proposed_changes=[],
    )


class _FakeResponse:
    def __init__(self, text: str | None) -> None:
        self.text = text


class _FakeConfig:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class _AuthFailure(Exception):
    status_code = 401


class _QuotaFailure(Exception):
    status_code = 429

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.details = details or {}
        self.response = types.SimpleNamespace(status_code=429, headers=headers or {})


class _ServiceFailure(Exception):
    status_code = 503


def _fake_modules(response: object | None = None, side_effect: Exception | None = None) -> tuple[Mock, types.SimpleNamespace, Mock]:
    generate_content = Mock(side_effect=side_effect, return_value=response)
    client = types.SimpleNamespace(models=types.SimpleNamespace(generate_content=generate_content))
    genai = Mock()
    genai.Client.return_value = client
    fake_types = types.SimpleNamespace(GenerateContentConfig=_FakeConfig)
    return genai, fake_types, generate_content


class GeminiEngineTests(unittest.TestCase):
    def test_missing_api_key_raises_controlled_error(self) -> None:
        with self.assertRaises(GeminiConfigurationError):
            analyze_contract_with_gemini(REDACTED_CONTRACT, "")

    def test_mocked_valid_gemini_json_parses_to_contract_audit_result(self) -> None:
        response = _FakeResponse(_sample_result().model_dump_json())
        fake_genai, fake_types, generate_content = _fake_modules(response=response)

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            result = analyze_contract_with_gemini(REDACTED_CONTRACT, "test-key", model=DEFAULT_GEMINI_MODEL)

        self.assertIsInstance(result, ContractAuditResult)
        self.assertEqual(result.risks[0].source_quote_he, QUOTE)
        self.assertEqual(
            len(result.question_engine_answers),
            len(question_engine_expected_answer_fields()),
        )
        client_kwargs = fake_genai.Client.call_args.kwargs
        self.assertEqual(client_kwargs["api_key"], "test-key")
        self.assertEqual(client_kwargs["http_options"]["retry_options"]["attempts"], 1)
        call = generate_content.call_args.kwargs
        self.assertEqual(call["model"], DEFAULT_GEMINI_MODEL)
        self.assertIn("ОБЕЗЛИЧЕННЫЕ EVIDENCE BLOCKS", call["contents"])
        self.assertIn("[P1-B04]", call["contents"])
        self.assertIn("question_engine_answers", call["contents"])
        self.assertEqual(call["config"].kwargs["response_mime_type"], "application/json")
        self.assertIn("response_json_schema", call["config"].kwargs)

    def test_missing_question_engine_answer_is_rejected(self) -> None:
        payload = _sample_result().model_dump(mode="json")
        payload["question_engine_answers"] = payload["question_engine_answers"][1:]
        response = _FakeResponse(ContractAuditResult.model_validate(payload).model_dump_json())
        fake_genai, fake_types, _generate_content = _fake_modules(response=response)

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            with self.assertRaisesRegex(GeminiResponseError, "omitted mandatory"):
                analyze_contract_with_gemini(REDACTED_CONTRACT, "test-key")

    def test_wrong_question_engine_value_count_is_rejected(self) -> None:
        payload = _sample_result().model_dump(mode="json")
        payload["question_engine_answers"][0]["values"] = []
        response = _FakeResponse(ContractAuditResult.model_validate(payload).model_dump_json())
        fake_genai, fake_types, _generate_content = _fake_modules(response=response)

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            with self.assertRaisesRegex(GeminiResponseError, "incomplete Question Engine values"):
                analyze_contract_with_gemini(REDACTED_CONTRACT, "test-key")

    def test_grounded_question_engine_answer_requires_real_evidence_id(self) -> None:
        payload = _sample_result().model_dump(mode="json")
        first = payload["question_engine_answers"][0]
        first["status"] = "FOUND"
        first["values"] = ["3,500 NIS", "NIS", "monthly"]
        first["evidence_block_ids"] = ["P99-B99"]
        response = _FakeResponse(ContractAuditResult.model_validate(payload).model_dump_json())
        fake_genai, fake_types, _generate_content = _fake_modules(response=response)

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            with self.assertRaisesRegex(GeminiResponseError, "invalid Question Engine evidence"):
                analyze_contract_with_gemini(REDACTED_CONTRACT, "test-key")

    def test_duplicate_question_engine_answer_is_rejected(self) -> None:
        payload = _sample_result().model_dump(mode="json")
        payload["question_engine_answers"].append(payload["question_engine_answers"][0])
        response = _FakeResponse(ContractAuditResult.model_validate(payload).model_dump_json())
        fake_genai, fake_types, _generate_content = _fake_modules(response=response)

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            with self.assertRaisesRegex(GeminiResponseError, "invalid Question Engine coverage"):
                analyze_contract_with_gemini(REDACTED_CONTRACT, "test-key")

    def test_debug_gemini_analysis_returns_raw_text_and_parsed_result(self) -> None:
        raw_json = _sample_result().model_dump_json()
        fake_genai, fake_types, _generate_content = _fake_modules(response=_FakeResponse(raw_json))

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            result = analyze_contract_with_gemini_debug(REDACTED_CONTRACT, "test-key")

        self.assertEqual(result.raw_text, raw_json)
        self.assertIsInstance(result.parsed_result, ContractAuditResult)
        self.assertIsNone(result.parse_error)

    def test_malformed_json_raises_gemini_response_error(self) -> None:
        fake_genai, fake_types, _generate_content = _fake_modules(response=_FakeResponse("not-json"))

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            with self.assertRaises(GeminiResponseError):
                analyze_contract_with_gemini(REDACTED_CONTRACT, "test-key")

    def test_debug_gemini_analysis_preserves_raw_text_on_malformed_json(self) -> None:
        fake_genai, fake_types, _generate_content = _fake_modules(response=_FakeResponse("not-json"))

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            result = analyze_contract_with_gemini_debug(REDACTED_CONTRACT, "test-key")

        self.assertEqual(result.raw_text, "not-json")
        self.assertIsNone(result.parsed_result)
        self.assertIsNotNone(result.parse_error)

    def test_empty_response_raises_gemini_response_error(self) -> None:
        fake_genai, fake_types, _generate_content = _fake_modules(response=_FakeResponse(""))

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            with self.assertRaises(GeminiResponseError):
                analyze_contract_with_gemini(REDACTED_CONTRACT, "test-key")

    def test_mocked_authentication_failure_becomes_gemini_authentication_error(self) -> None:
        fake_genai, fake_types, _generate_content = _fake_modules(side_effect=_AuthFailure("bad key"))

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            with self.assertRaises(GeminiAuthenticationError):
                analyze_contract_with_gemini(REDACTED_CONTRACT, "bad-key")

    def test_daily_quota_metadata_is_preserved_without_raw_provider_text(self) -> None:
        details = {
            "error": {
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [
                            {"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}
                        ],
                    },
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "42s",
                    },
                ]
            }
        }
        fake_genai, fake_types, _generate_content = _fake_modules(
            side_effect=_QuotaFailure("sensitive provider text", details=details)
        )

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            with self.assertRaises(GeminiRateLimitError) as raised:
                analyze_contract_with_gemini(REDACTED_CONTRACT, "test-key")

        self.assertEqual(raised.exception.quota_scope, "daily")
        self.assertEqual(raised.exception.retry_after_seconds, 42.0)
        self.assertNotIn("sensitive provider text", str(raised.exception))

    def test_temporary_rate_limit_uses_retry_after_header(self) -> None:
        fake_genai, fake_types, _generate_content = _fake_modules(
            side_effect=_QuotaFailure("rate", headers={"Retry-After": "12"})
        )

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            with self.assertRaises(GeminiRateLimitError) as raised:
                analyze_contract_with_gemini(REDACTED_CONTRACT, "test-key")

        self.assertEqual(raised.exception.quota_scope, "temporary_or_unknown")
        self.assertEqual(raised.exception.retry_after_seconds, 12.0)

    def test_service_failure_is_marked_retryable_for_runner(self) -> None:
        fake_genai, fake_types, _generate_content = _fake_modules(
            side_effect=_ServiceFailure("unavailable")
        )

        with patch.object(gemini_engine, "genai", fake_genai), patch.object(gemini_engine, "_genai_types", fake_types):
            with self.assertRaises(GeminiResponseError) as raised:
                analyze_contract_with_gemini(REDACTED_CONTRACT, "test-key")

        self.assertTrue(raised.exception.retryable_provider)

    def test_gemini_result_passes_through_existing_evidence_validator(self) -> None:
        validated = validate_model_evidence(_sample_result(), REDACTED_CONTRACT)

        self.assertEqual(len(validated.result.risks), 1)
        self.assertEqual(validated.warnings, [])

    def test_app_imports_without_api_key(self) -> None:
        import app  # noqa: F401

        self.assertTrue(True)

    def test_requirements_no_longer_contains_removed_ai_provider(self) -> None:
        with open("requirements.txt", encoding="utf-8") as requirements_file:
            requirements = requirements_file.read().lower()

        self.assertIn("google-genai", requirements)
        self.assertNotIn("open" + "ai", requirements)

    def test_ui_no_longer_mentions_removed_ai_provider(self) -> None:
        with open("app.py", encoding="utf-8") as app_file:
            source = app_file.read()

        self.assertNotIn("Open" + "AI", source)
        self.assertNotIn("open" + "ai", source)
        self.assertIn("Gemini API-ключ — dev override", source)

    def test_ui_uses_risk_profile_shell_instead_of_verdict_copy(self) -> None:
        with open("app.py", encoding="utf-8") as app_file:
            source = app_file.read()

        self.assertIn("Итоговый риск-профиль загруженных материалов", source)
        self.assertIn("Риск-профиль", source)
        self.assertIn("Сервис показывает только риск-профиль", source)
        self.assertNotIn("st.metric(\"Вердикт\"", source)
        self.assertNotIn("Нельзя подписывать в текущем виде", source)
        self.assertNotIn("Можно обсуждать", source)
        self.assertNotIn("Нужна проверка юриста", source)


if __name__ == "__main__":
    unittest.main()
