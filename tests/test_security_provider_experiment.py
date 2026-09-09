from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import security_provider_experiment as experiment


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


if __name__ == "__main__":
    unittest.main()
