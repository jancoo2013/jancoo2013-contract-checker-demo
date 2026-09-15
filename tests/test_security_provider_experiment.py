import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import security_provider_experiment as experiment


VALID_TEXT = '{"assertions":[],"resolution":null}'


class FakeResponse:
    def __init__(self, text=VALID_TEXT, envelope=None, raw=None):
        self.text = text
        self.envelope = envelope
        self.raw = raw
        self.read_sizes = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        self.read_sizes.append(size)
        if self.raw is not None:
            data = self.raw
        else:
            payload = self.envelope if self.envelope is not None else {
                "candidates": [{"content": {"parts": [{"text": self.text}]}}]
            }
            data = json.dumps(payload).encode("utf-8")
        return data if size is None or size < 0 else data[:size]


def http_error(code, detail=b"temporary", headers=None):
    return experiment.error.HTTPError(
        "https://example.invalid", code, "error", headers or {}, io.BytesIO(detail))


def structured_error(code, details):
    return http_error(code, json.dumps({"error": {"code": code, "details": details}}).encode())


def daily_quota_error(model="gemini-3.6-flash"):
    return structured_error(429, [{
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [{
            "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            "quotaDimensions": {"model": model},
        }],
    }])


class SecurityProviderExperimentTests(unittest.TestCase):
    def test_prompt_hides_oracle_answers(self):
        case = {
            "lifecycle": "EXECUTED", "clauses": [{"ref": "c1", "text_he": "טקסט"}],
            "assertions": [{"question_id": "security.instrument_amounts", "field": "instrument_amounts",
                            "expected": 10000, "refs": ["c1"], "mechanism_id": "security_1"}],
            "candidate": {"candidate_kind": "x", "claim": "test", "subject_refs": ["c1"]},
            "resolution": {"outcome": "CONFIRMED", "reviewed_refs": ["c1"]},
        }
        prompt = experiment.build_prompt(case)
        self.assertNotIn('"expected"', prompt)
        self.assertNotIn('"CONFIRMED"', prompt)
        self.assertIn('"candidate"', prompt)

    def test_target_slots_preserve_mechanism_identity(self):
        case = {"lifecycle": "EXECUTED", "clauses": [], "assertions": [
            {"question_id": "security.instrument_amounts", "field": "instrument_amounts",
             "expected": 10000, "refs": ["c1"], "mechanism_id": "security_1"},
            {"question_id": "security.instrument_amounts", "field": "instrument_amounts",
             "expected": 30000, "refs": ["c2"], "mechanism_id": "security_2"},
        ]}
        self.assertEqual(experiment.case_input(case)["target_assertions"], [
            {"question_id": "security.instrument_amounts", "mechanism_id": "security_1",
             "field": "instrument_amounts"},
            {"question_id": "security.instrument_amounts", "mechanism_id": "security_2",
             "field": "instrument_amounts"},
        ])

    def test_request_body_uses_generate_content_schema_fields(self):
        config = experiment.request_body("{}", 2)["generationConfig"]
        self.assertEqual(config["responseMimeType"], "application/json")
        self.assertIn("responseJsonSchema", config)
        self.assertNotIn("responseFormat", config)

    def test_exact_scoring(self):
        case = {"clauses": [{"ref": "c1", "text_he": "x"}], "assertions": [{
            "question_id": "security.instrument_amounts", "field": "instrument_amounts",
            "expected": 10000, "refs": ["c1"], "mechanism_id": "security_1"}]}
        actual = {"assertions": [{
            "question_id": "security.instrument_amounts", "field": "instrument_amounts",
            "mechanism_id": "security_1", "value": 10000,
            "state": dict(experiment.DEFAULT_STATE), "refs": ["c1"]}], "resolution": None}
        self.assertEqual(experiment.score_case(case, actual)["assertions_exact"], 1)

    def test_load_key_from_desktop_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            desktop = Path(tmp)
            (desktop / ".env.local").write_text("GEMINI_API_KEY=test-key\n", encoding="utf-8")
            with patch.object(experiment, "desktop_dirs", return_value=[desktop]), \
                 patch.dict("os.environ", {}, clear=True):
                key, path = experiment.load_key()
        self.assertEqual((key, path), ("test-key", desktop / ".env.local"))

    def test_models_are_flash_only(self):
        self.assertEqual(experiment.MODEL_ROUTE, (experiment.MODEL, experiment.FALLBACK_MODEL))
        self.assertNotIn("gemini-3.1-pro-preview", experiment.MODEL_ROUTE)
        self.assertEqual(experiment.MAX_ATTEMPTS_PER_MODEL, 2)
        self.assertEqual(experiment.MAX_TOTAL_ATTEMPTS, 4)

    def test_parse_rejects_non_object_and_non_finite_json(self):
        with self.assertRaisesRegex(RuntimeError, "root_not_object"):
            experiment.parse_provider_text("[]")
        for text in ('{"assertions":[],"resolution":null,"x":NaN}',
                     '{"assertions":[],"resolution":null,"x":Infinity}'):
            with self.assertRaisesRegex(RuntimeError, "invalid_json"):
                experiment.parse_provider_text(text)

    def test_validator_rejects_bad_resolution_type_without_typeerror(self):
        actual = {"assertions": [], "resolution": {"outcome": [], "reviewed_refs": []}}
        with self.assertRaisesRegex(RuntimeError, "resolution_outcome"):
            experiment.validate_provider_output(actual, 0)

    def test_validator_rejects_non_finite_manual_value(self):
        actual = {"assertions": [{
            "question_id": "q", "mechanism_id": None, "field": "f", "value": math.nan,
            "state": dict(experiment.DEFAULT_STATE), "refs": ["c1"]}], "resolution": None}
        with self.assertRaisesRegex(RuntimeError, "value_non_finite"):
            experiment.validate_provider_output(actual, 1)

    def test_malformed_error_shapes_are_safe(self):
        for payload in ({"error": []}, {"error": "bad"}, {"error": None}, {"error": {"details": {}}}):
            self.assertEqual(experiment.error_details(payload), [])
            self.assertEqual(experiment.quota_violations(payload), [])
            self.assertIsNone(experiment.retry_info_seconds(payload))

    def test_daily_quota_detection_is_narrow(self):
        payload = {"error": {"details": [{
            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
            "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}],
        }]}}
        self.assertTrue(experiment.is_daily_quota_error("", payload))
        self.assertTrue(experiment.is_daily_quota_error(
            "quotaId: GenerateTokensPerDayPerProjectPerModel-FreeTier", None))
        self.assertFalse(experiment.is_daily_quota_error("unrelated perDay text", None))
        rpm = {"error": {"details": [{
            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
            "violations": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}],
        }]}}
        self.assertFalse(experiment.is_daily_quota_error("", rpm))

    def test_retry_wait_prefers_longest_valid_hint_and_rejects_nan(self):
        payload = {"error": {"details": [{
            "@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "41s"}]}}
        self.assertEqual(experiment.retry_wait_seconds("retry in 2s", {"Retry-After": "1"}, 1, payload), 42.0)
        self.assertEqual(experiment.retry_wait_seconds("", {"Retry-After": "NaN"}, 2, None), 30.0)
        self.assertEqual(experiment.retry_wait_seconds("", {"Retry-After": "Infinity"}, 1, None), 15.0)

    def test_response_body_read_is_bounded(self):
        response = FakeResponse()
        experiment.read_provider_envelope(response)
        self.assertEqual(response.read_sizes, [experiment.MAX_RESPONSE_BODY_BYTES + 1])

    def test_oversize_response_falls_back(self):
        oversized = FakeResponse(raw=b"{" + b"x" * experiment.MAX_RESPONSE_BODY_BYTES + b"}")
        with patch.object(experiment.request, "urlopen", side_effect=[oversized, FakeResponse()]) as urlopen:
            actual, model = experiment.call_gemini("key", "{}", 0)
        self.assertEqual(actual, {"assertions": [], "resolution": None})
        self.assertEqual(model, experiment.FALLBACK_MODEL)
        self.assertEqual(urlopen.call_count, 2)

    def test_malformed_outer_json_falls_back(self):
        with patch.object(experiment.request, "urlopen",
                          side_effect=[FakeResponse(raw=b"not-json"), FakeResponse()]):
            _, model = experiment.call_gemini("key", "{}", 0)
        self.assertEqual(model, experiment.FALLBACK_MODEL)

    def test_malformed_envelope_falls_back(self):
        for first in (FakeResponse(envelope={"unexpected": []}), FakeResponse(envelope={"candidates": []}),
                      FakeResponse(envelope={"candidates": [{"content": {"parts": []}}]})):
            with patch.object(experiment.request, "urlopen", side_effect=[first, FakeResponse()]):
                _, model = experiment.call_gemini("key", "{}", 0)
            self.assertEqual(model, experiment.FALLBACK_MODEL)

    def test_malformed_model_json_and_schema_failure_fall_back(self):
        for first in (FakeResponse(text="not-json"),
                      FakeResponse(text='{"assertions":[{"bad":1}],"resolution":null}')):
            with patch.object(experiment.request, "urlopen", side_effect=[first, FakeResponse()]):
                _, model = experiment.call_gemini("key", "{}", 0)
            self.assertEqual(model, experiment.FALLBACK_MODEL)

    def test_global_400_401_403_abort_without_fallback(self):
        for code in (400, 401, 403):
            with patch.object(experiment.request, "urlopen", side_effect=http_error(code)) as urlopen:
                with self.assertRaises(experiment.GlobalProviderError):
                    experiment.call_gemini("key", "{}", 0)
            self.assertEqual(urlopen.call_count, 1)

    def test_404_is_remembered_across_cases(self):
        unavailable = set()
        with patch.object(experiment.request, "urlopen",
                          side_effect=[http_error(404), FakeResponse(), FakeResponse()]) as urlopen:
            _, first = experiment.call_gemini("key", "{}", 0, unavailable)
            _, second = experiment.call_gemini("key", "{}", 0, unavailable)
        self.assertEqual(first, experiment.FALLBACK_MODEL)
        self.assertEqual(second, experiment.FALLBACK_MODEL)
        self.assertIn(experiment.DEFAULT_MODEL, unavailable)
        self.assertEqual(urlopen.call_count, 3)

    def test_daily_quota_is_remembered_across_cases(self):
        unavailable = set()
        with patch.object(experiment.request, "urlopen",
                          side_effect=[daily_quota_error(), FakeResponse(), FakeResponse()]) as urlopen, \
             patch.object(experiment.time, "sleep") as sleep:
            _, first = experiment.call_gemini("key", "{}", 0, unavailable)
            _, second = experiment.call_gemini("key", "{}", 0, unavailable)
        self.assertEqual((first, second), (experiment.FALLBACK_MODEL, experiment.FALLBACK_MODEL))
        self.assertEqual(urlopen.call_count, 3)
        self.assertIn(experiment.DEFAULT_MODEL, unavailable)
        sleep.assert_not_called()

    def test_short_window_429_retries_same_model(self):
        limited = http_error(429, b"retry in 1s")
        with patch.object(experiment.request, "urlopen", side_effect=[limited, FakeResponse()]) as urlopen, \
             patch.object(experiment.time, "sleep") as sleep:
            _, model = experiment.call_gemini("key", "{}", 0)
        self.assertEqual(model, experiment.MODEL)
        self.assertTrue(all(experiment.MODEL in c.args[0].full_url for c in urlopen.call_args_list))
        sleep.assert_called_once_with(2.0)

    def test_503_and_timeout_switch_to_fallback(self):
        for failure in (http_error(503), TimeoutError("read timed out"),
                        experiment.error.URLError(TimeoutError("network timed out"))):
            with patch.object(experiment.request, "urlopen", side_effect=[failure, FakeResponse()]) as urlopen:
                _, model = experiment.call_gemini("key", "{}", 0)
            self.assertEqual(model, experiment.FALLBACK_MODEL)
            self.assertEqual(urlopen.call_count, 2)

    def test_mixed_retry_then_503_reaches_fallback_within_cap(self):
        with patch.object(experiment.request, "urlopen", side_effect=[
            http_error(429, b"retry in 1s"), http_error(503), FakeResponse()]) as urlopen, \
             patch.object(experiment.time, "sleep"):
            _, model = experiment.call_gemini("key", "{}", 0)
        self.assertEqual(model, experiment.FALLBACK_MODEL)
        self.assertEqual(urlopen.call_count, 3)

    def test_global_attempt_cap_is_hard(self):
        failures = [http_error(429, b"retry in 1s") for _ in range(experiment.MAX_TOTAL_ATTEMPTS)]
        with patch.object(experiment.request, "urlopen", side_effect=failures) as urlopen, \
             patch.object(experiment.time, "sleep"):
            with self.assertRaises(RuntimeError):
                experiment.call_gemini("key", "{}", 0)
        self.assertLessEqual(urlopen.call_count, experiment.MAX_TOTAL_ATTEMPTS)

    def test_run_propagates_global_provider_error(self):
        case_id = "case1"
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp) / "corpus.json"
            corpus.write_text(json.dumps({"cases": [{
                "case_id": case_id, "domain": "security", "lifecycle": "EXECUTED",
                "clauses": [], "assertions": []}]}), encoding="utf-8")
            with patch.object(experiment, "CASES", (case_id,)), \
                 patch.object(experiment, "CORPUS", corpus), \
                 patch.object(experiment, "load_key", return_value=("key", None)), \
                 patch.object(experiment, "call_gemini", side_effect=experiment.GlobalProviderError("auth")):
                with self.assertRaises(experiment.GlobalProviderError):
                    experiment.run()


if __name__ == "__main__":
    unittest.main()
