import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import security_provider_experiment as experiment


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        payload = {"candidates": [{"content": {"parts": [{
            "text": '{"assertions":[],"resolution":null}'
        }]}}]}
        return json.dumps(payload).encode("utf-8")


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

    def test_exact_scoring(self):
        case = {"clauses": [{"ref": "c1", "text_he": "טקסט"}], "assertions": [{
            "question_id": "security.instrument_amounts", "field": "instrument_amounts",
            "expected": 10000, "refs": ["c1"], "mechanism_id": "security_1"}]}
        actual = {"assertions": [{
            "question_id": "security.instrument_amounts", "field": "instrument_amounts",
            "mechanism_id": "security_1", "value": 10000,
            "state": dict(experiment.DEFAULT_STATE), "refs": ["c1"]}], "resolution": None}
        score = experiment.score_case(case, actual)
        self.assertEqual((score["assertions_exact"], score["hard_failures"]), (1, []))

    def test_handwriting_guess_is_hard_failure(self):
        case = {"clauses": [{"ref": "c1", "text_he": "טקסט"}],
                "redactions": [{"ref": "r1", "kind": "HANDWRITING"}], "assertions": [{
                    "question_id": "security.instrument_amounts", "field": "instrument_amounts",
                    "expected": None, "refs": ["c1", "r1"], "mechanism_id": "security_1",
                    "state": {"value": "UNKNOWN", "evidence": "HANDWRITING_DEPENDENCY"}}]}
        state = {**experiment.DEFAULT_STATE, "value": "UNKNOWN", "evidence": "HANDWRITING_DEPENDENCY"}
        actual = {"assertions": [{"question_id": "security.instrument_amounts",
                                   "field": "instrument_amounts", "mechanism_id": "security_1",
                                   "value": 9000, "state": state, "refs": ["c1", "r1"]}],
                  "resolution": None}
        self.assertIn("guessed_unavailable_value", experiment.score_case(case, actual)["hard_failures"])

    def test_load_key_from_desktop_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            desktop = Path(tmp)
            (desktop / ".env.local").write_text("GEMINI_API_KEY=test-key\n", encoding="utf-8")
            with patch.object(experiment, "desktop_dirs", return_value=[desktop]), \
                 patch.dict("os.environ", {}, clear=True):
                key, path = experiment.load_key()
        self.assertEqual((key, path), ("test-key", desktop / ".env.local"))

    def test_non_object_provider_json_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "root_not_object"):
            experiment.parse_provider_text("[]")

    def test_selected_subset_is_ten_cases(self):
        self.assertEqual(len(experiment.CASES), 10)
        self.assertEqual(len(set(experiment.CASES)), 10)

    def test_default_model_and_retry_policy(self):
        self.assertEqual(experiment.DEFAULT_MODEL, "gemini-3.6-flash")
        self.assertEqual(experiment.RETRYABLE_HTTP_CODES, {429, 503})
        self.assertGreaterEqual(experiment.REQUEST_SPACING_SECONDS, 12)
        self.assertGreaterEqual(experiment.REQUEST_TIMEOUT_SECONDS, 120)
        self.assertLessEqual(experiment.MAX_ATTEMPTS, 4)

    def test_retry_wait_uses_provider_hint_and_bounds_it(self):
        self.assertEqual(experiment.retry_wait_seconds("Please retry in 49.5s.", {}, 1), 50.5)
        self.assertEqual(experiment.retry_wait_seconds("Please retry in 999s.", {}, 1), 120.0)
        self.assertEqual(experiment.retry_wait_seconds("temporary overload", {}, 2), 30.0)

    def test_timeout_is_recognized_inside_url_error(self):
        wrapped = experiment.error.URLError(TimeoutError("The read operation timed out"))
        self.assertTrue(experiment.is_timeout_error(wrapped))

    def test_read_timeout_retries_and_then_succeeds(self):
        with patch.object(experiment.request, "urlopen",
                          side_effect=[TimeoutError("The read operation timed out"), FakeResponse()]) as urlopen, \
             patch.object(experiment.time, "sleep") as sleep:
            actual = experiment.call_gemini("test-key", "{}")
        self.assertEqual(actual, {"assertions": [], "resolution": None})
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], experiment.REQUEST_TIMEOUT_SECONDS)
        sleep.assert_called_once_with(15.0)


if __name__ == "__main__":
    unittest.main()
