"""Tests for framework-agnostic contract analysis orchestration."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from contract_checker.analysis_pipeline import run_contract_analysis
from contract_checker.gemini_engine import DEFAULT_GEMINI_MODEL, GeminiResponseError


class AnalysisPipelineTests(unittest.TestCase):
    @patch("contract_checker.analysis_pipeline.validate_model_evidence")
    @patch("contract_checker.analysis_pipeline.analyze_contract_with_gemini")
    def test_pipeline_composes_analysis_and_evidence_validation(
        self,
        analyze_mock,
        validate_mock,
    ) -> None:
        parsed_result = object()
        validated_result = object()
        analyze_mock.return_value = parsed_result
        validate_mock.return_value = SimpleNamespace(
            result=validated_result,
            warnings=["warning-1", "warning-2"],
        )

        result = run_contract_analysis(
            "redacted contract text",
            "test-api-key",
            model="test-model",
        )

        analyze_mock.assert_called_once_with(
            redacted_text="redacted contract text",
            api_key="test-api-key",
            model="test-model",
        )
        validate_mock.assert_called_once_with(parsed_result, "redacted contract text")
        self.assertIs(result.result, validated_result)
        self.assertEqual(result.evidence_warnings, ["warning-1", "warning-2"])

    @patch("contract_checker.analysis_pipeline.validate_model_evidence")
    @patch("contract_checker.analysis_pipeline.analyze_contract_with_gemini")
    def test_default_model_is_forwarded_to_gemini_layer(
        self,
        analyze_mock,
        validate_mock,
    ) -> None:
        parsed_result = object()
        analyze_mock.return_value = parsed_result
        validate_mock.return_value = SimpleNamespace(result=object(), warnings=[])

        run_contract_analysis("redacted contract text", "test-api-key")

        analyze_mock.assert_called_once_with(
            redacted_text="redacted contract text",
            api_key="test-api-key",
            model=DEFAULT_GEMINI_MODEL,
        )

    @patch("contract_checker.analysis_pipeline.validate_model_evidence")
    @patch("contract_checker.analysis_pipeline.analyze_contract_with_gemini")
    def test_analysis_error_propagates_without_running_evidence_validation(
        self,
        analyze_mock,
        validate_mock,
    ) -> None:
        analyze_mock.side_effect = GeminiResponseError("structured response failed")

        with self.assertRaises(GeminiResponseError):
            run_contract_analysis("redacted contract text", "test-api-key")

        validate_mock.assert_not_called()

    @patch("contract_checker.analysis_pipeline.validate_model_evidence")
    @patch("contract_checker.analysis_pipeline.analyze_contract_with_gemini")
    def test_evidence_validation_error_propagates(
        self,
        analyze_mock,
        validate_mock,
    ) -> None:
        analyze_mock.return_value = object()
        validate_mock.side_effect = RuntimeError("validation failed")

        with self.assertRaises(RuntimeError):
            run_contract_analysis("redacted contract text", "test-api-key")


if __name__ == "__main__":
    unittest.main()
