import io
import json
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        if self.raw is not None:
            return self.raw
        payload = self.envelope if self.envelope is not None else {
            "candidates": [{"content": {"parts": [{"text": self.text}]}}]
        }
        return json.dumps(payload).encode("utf-8")


def http_error(code, detail=b"temporary"):
    return experiment.error.HTTPError(
        "https://example.invalid", code, "error", {}, io.BytesIO(detail))


def daily_quota_error(model="gemini-3.6-flash"):
    payload = {"error": {"code": 429, "details": [{
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [{
            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
            "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            "quotaDimensions": {"model": model},
        }],
    }]}}
    return http_error(429, json.dumps(payload).encode())


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
        case = {
            "lifecycle": "EXECUTED", "clauses": [],
            "assertions": [
                {"question_id": "security.instrument_amounts", "field": "instrument_amounts",
                 "expected": 10000, "refs": ["c1"], "mechanism_id": "security_1"},
                {"question_id": "security.instrument_amounts", "field": "instrument_amounts",
                 "expected": 30000, "refs": ["c2"], "mechanism_id": "security_2"},
            ],
        }
        self.assertEqual(experiment.case_input(case)["target_assertions"], [
            {"question_id": "security.instrument_amounts", "mechanism_id": "security_1",
             "field": "instrument_amounts"},
            {"question_id": "security.instrument_amounts", "mechanism_id": "security_2",
             "field": "instrument_amounts"},
        ])

    def test_prompt_defines_days_and_dependency_states(self):
        prompt = experiment.build_prompt({"lifecycle": "EXECUTED", "clauses": [], "assertions": []})
        self.assertIn("integer day counts", prompt)
        self.assertIn("HANDWRITING_DEPENDENCY", prompt)
        self.assertIn("MISSING_DEPENDENCY", prompt)
        self.assertIn("state.value=BLANK", prompt)

    def test_response_schema_and_request_shape(self):
        schema = experiment.response_schema(3)
        assertions = schema["properties"]["assertions"]
        self.assertEqual((assertions["minItems"], assertions["maxItems"]), (3, 3))
        body = experiment.request_body("{}", 2)
        config = body["generationConfig"]
        self.assertEqual(config["responseMimeType"], "application/json")
        self.assertIn("responseJsonSchema", config)
        self.assertNotIn("responseFormat", config)

    def test_exact_scoring_and_handwriting_guard(self):
        case = {"clauses": [{"ref": "c1", "text_he": "טקסט"}], "assertions": [{
            "question_id": "security.instrument_amounts", "field": "instrument_amounts",
            "expected": 10000, "refs": ["c1"], "mechanism_id": "security_1"}]}
        actual = {"assertions": [{
            "question_id": "security.instrument_amounts", "field": "instrument_amounts",
            "mechanism_id": "security_1", "value": 10000,
            "state": dict(experiment.DEFAULT_STATE), "refs": ["c1"]}], "resolution": None}
        self.assertEqual(experiment.score_case(case, actual)["assertions_exact"], 1)

        case["redactions"] = [{"ref": "r1", "kind": "HANDWRITING"}]
        case["assertions"][0].update({"expected": None, "refs": ["c1", "r1"],
                                      "state": {"value": "UNKNOWN", "evidence": "HANDWRITING_DEPENDENCY"}})
        actual["assertions"][0].update({"value": 9000, "refs": ["c1", "r1"],
                                         "state": {**experiment.DEFAULT_STATE, "value": "UNKNOWN",
                                                   "evidence": "HANDWRITING_DEPENDENCY"}})
        self.assertIn("guessed_unavailable_value", experiment.score_case(case, actual)["hard_failures"])

    def test_load_key_from_desktop_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            desktop = Path(tmp)
            (desktop / ".env.local").write_text("GEMINI_API_KEY=test-key\n", encoding="utf-8")
            with patch.object(experiment, "desktop_dirs", return_value=[desktop]), \
                 patch.dict("os.environ", {}, clear=True):
                key, path = experiment.load_key()
        self.assertEqual((key, path), ("test-key", desktop / ".env.local"))

    def test_only_flash_models_are_routed_and_override_is_validated(self):
        self.assertEqual(experiment.DEFAULT_MODEL, "gemini-3.6-flash")
        self.assertEqual(experiment.FALLBACK_MODEL, "gemini-3.5-flash")
        self.assertEqual(experiment.build_model_route("gemini-3.6-flash"),
                         ("gemini-3.6-flash", "gemini-3.5-flash"))
        self.assertEqual(experiment.build_model_route("gemini-3.5-flash"), ("gemini-3.5-flash",))
        with self.assertRaisesRegex(RuntimeError, "Unsupported GEMINI_MODEL"):
            experiment.build_model_route("gemini-3.1-pro-preview")

    def test_quota_and_retryinfo_are_parsed_structurally(self):
        payload = {"error": {"details": [
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
             "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "41s"},
        ]}}
        self.assertTrue(experiment.is_daily_quota_error("", payload))
        self.assertEqual(experiment.retry_wait_seconds("", {}, 1, payload), 42.0)
        self.assertFalse(experiment.is_daily_quota_error("Please retry in 41s", {}))

    def test_daily_quota_is_remembered_across_cases(self):
        state = experiment.new_run_state()
        with patch.object(experiment.request, "urlopen",
                          side_effect=[daily_quota_error(), FakeResponse(), FakeResponse()]) as urlopen, \
             patch.object(experiment.time, "sleep") as sleep:
            _, first_model, _ = experiment.call_gemini("key", "{}", 0, state, "case1")
            _, second_model, _ = experiment.call_gemini("key", "{}", 0, state, "case2")
        self.assertEqual(first_model, experiment.FALLBACK_MODEL)
        self.assertEqual(second_model, experiment.FALLBACK_MODEL)
        self.assertEqual(urlopen.call_count, 3)
        self.assertIn(experiment.FALLBACK_MODEL, urlopen.call_args_list[2].args[0].full_url)
        self.assertEqual(state["unavailable_models"][experiment.DEFAULT_MODEL], "daily_quota")
        sleep.assert_not_called()

    def test_503_and_timeout_switch_to_fallback(self):
        for failure in (http_error(503), TimeoutError("read timed out")):
            state = experiment.new_run_state()
            with patch.object(experiment.request, "urlopen", side_effect=[failure, FakeResponse()]) as urlopen:
                _, model, _ = experiment.call_gemini("key", "{}", 0, state, "case")
            self.assertEqual(model, experiment.FALLBACK_MODEL)
            self.assertIn(experiment.FALLBACK_MODEL, urlopen.call_args_list[1].args[0].full_url)

    def test_short_window_429_retries_same_model(self):
        state = experiment.new_run_state()
        with patch.object(experiment.request, "urlopen",
                          side_effect=[http_error(429, b"retry in 1s"), FakeResponse()]) as urlopen, \
             patch.object(experiment.time, "sleep") as sleep:
            _, model, _ = experiment.call_gemini("key", "{}", 0, state, "case")
        self.assertEqual(model, experiment.MODEL)
        self.assertTrue(all(experiment.MODEL in c.args[0].full_url for c in urlopen.call_args_list))
        sleep.assert_called_once_with(2.0)

    def test_malformed_model_json_falls_back(self):
        state = experiment.new_run_state()
        with patch.object(experiment.request, "urlopen",
                          side_effect=[FakeResponse(text="not-json"), FakeResponse()]) as urlopen:
            actual, model, _ = experiment.call_gemini("key", "{}", 0, state, "case")
        self.assertEqual(actual, {"assertions": [], "resolution": None})
        self.assertEqual(model, experiment.FALLBACK_MODEL)
        self.assertEqual(state["attempts"][0]["failure_class"], "model_output_invalid_json")
        self.assertIn(experiment.FALLBACK_MODEL, urlopen.call_args_list[1].args[0].full_url)

    def test_malformed_envelope_and_schema_invalid_output_fall_back(self):
        for first in (
            FakeResponse(envelope={"unexpected": []}),
            FakeResponse(text='{"assertions":[{"bad":1}],"resolution":null}'),
        ):
            state = experiment.new_run_state()
            with patch.object(experiment.request, "urlopen", side_effect=[first, FakeResponse()]):
                _, model, _ = experiment.call_gemini("key", "{}", 0, state, "case")
            self.assertEqual(model, experiment.FALLBACK_MODEL)

    def test_outer_http200_invalid_json_falls_back(self):
        state = experiment.new_run_state()
        with patch.object(experiment.request, "urlopen",
                          side_effect=[FakeResponse(raw=b"not-json"), FakeResponse()]):
            _, model, _ = experiment.call_gemini("key", "{}", 0, state, "case")
        self.assertEqual(model, experiment.FALLBACK_MODEL)
        self.assertEqual(state["attempts"][0]["failure_class"], "provider_envelope_json")

    def test_model_unavailable_is_remembered_and_http400_aborts(self):
        state = experiment.new_run_state()
        with patch.object(experiment.request, "urlopen",
                          side_effect=[http_error(404), FakeResponse(), FakeResponse()]) as urlopen:
            experiment.call_gemini("key", "{}", 0, state, "case1")
            experiment.call_gemini("key", "{}", 0, state, "case2")
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(state["unavailable_models"][experiment.DEFAULT_MODEL], "model_unavailable")
        with patch.object(experiment.request, "urlopen", side_effect=http_error(400)):
            with self.assertRaises(experiment.GlobalProviderError):
                experiment.call_gemini("key", "{}", 0, experiment.new_run_state(), "case3")

    def test_both_models_daily_exhausted_fail_fast_after_memory(self):
        state = experiment.new_run_state()
        with patch.object(experiment.request, "urlopen",
                          side_effect=[daily_quota_error(), daily_quota_error(experiment.FALLBACK_MODEL)]) as urlopen:
            with self.assertRaisesRegex(RuntimeError, "daily_quota"):
                experiment.call_gemini("key", "{}", 0, state, "case1")
        with patch.object(experiment.request, "urlopen") as second:
            with self.assertRaisesRegex(RuntimeError, "no_available_models"):
                experiment.call_gemini("key", "{}", 0, state, "case2")
            second.assert_not_called()
        self.assertEqual(urlopen.call_count, 2)

    def test_attempt_ledger_and_summary_are_per_model(self):
        attempts = [
            {"model": experiment.DEFAULT_MODEL, "failure_class": "daily_quota"},
            {"model": experiment.FALLBACK_MODEL, "status": "OK"},
        ]
        case_id = experiment.CASES[0]
        by_id = {x: {"assertions": [], "resolution": None} for x in experiment.CASES}
        results = [{"case_id": case_id, "status": "OK", "model_used": experiment.FALLBACK_MODEL,
                    "score": {"assertions_exact": 0, "assertions_total": 0, "value_matches": 0,
                              "state_matches": 0, "refs_matches": 0, "resolution_ok": True,
                              "hard_failures": []}}]
        summary = experiment.build_summary(results, by_id, attempts)
        self.assertEqual(summary["attempts_by_model"][experiment.DEFAULT_MODEL], 1)
        self.assertEqual(summary["successes_by_model"][experiment.FALLBACK_MODEL], 1)
        self.assertEqual(summary["failure_classes"], {"daily_quota": 1})

    def test_partial_report_is_persisted_before_global_abort(self):
        case_ids = ("case1", "case2")
        cases = [{"case_id": cid, "domain": "security", "lifecycle": "EXECUTED",
                  "clauses": [], "assertions": []} for cid in case_ids]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus.json"
            corpus.write_text(json.dumps({"cases": cases}), encoding="utf-8")
            with patch.object(experiment, "CASES", case_ids), \
                 patch.object(experiment, "CORPUS", corpus), \
                 patch.object(experiment, "desktop_dirs", return_value=[root]), \
                 patch.object(experiment, "load_key", return_value=("key", None)), \
                 patch.object(experiment, "REQUEST_SPACING_SECONDS", 0), \
                 patch.object(experiment, "call_gemini",
                              side_effect=[({"assertions": [], "resolution": None}, experiment.DEFAULT_MODEL, []),
                                           experiment.GlobalProviderError("provider_config_http_400")]):
                report, txt = experiment.run()
            self.assertEqual(report["status"], "ABORTED_GLOBAL_PROVIDER_ERROR")
            self.assertEqual(len(report["results"]), 2)
            json_files = list(root.glob("security_provider_experiment_*.json"))
            self.assertEqual(len(json_files), 1)
            saved = json.loads(json_files[0].read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "ABORTED_GLOBAL_PROVIDER_ERROR")
            self.assertTrue(txt.is_file())

    def test_api_key_never_enters_http_error_report(self):
        secret = "very-secret-key"
        with patch.object(experiment.request, "urlopen",
                          side_effect=http_error(500, f"oops {secret}".encode())):
            with self.assertRaises(RuntimeError) as caught:
                experiment.call_gemini(secret, "{}", 0, experiment.new_run_state(), "case")
        self.assertNotIn(secret, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
