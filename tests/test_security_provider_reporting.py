import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import security_provider_experiment as experiment
from tests.test_security_provider_experiment import FakeResponse, http_error


class SecurityProviderReportingTests(unittest.TestCase):
    def test_attempt_ledger_records_failure_and_success(self):
        attempts = []
        with patch.object(experiment.request, "urlopen", side_effect=[http_error(503), FakeResponse()]):
            _, model = experiment.call_gemini("key", "{}", 0, set(), attempts, "case1")
        self.assertEqual(model, experiment.FALLBACK_MODEL)
        self.assertEqual([x["attempt"] for x in attempts], [1, 2])
        self.assertEqual([x["model"] for x in attempts], [experiment.MODEL, experiment.FALLBACK_MODEL])
        self.assertEqual(attempts[0]["failure_class"], "provider_overloaded")
        self.assertEqual(attempts[1]["status"], "OK")
        self.assertTrue(all(x["case_id"] == "case1" for x in attempts))

    def test_persist_report_recursively_redacts_key(self):
        secret = "secret-sentinel"
        case_id = "case1"
        by_id = {case_id: {"assertions": [], "resolution": None}}
        results = [{"case_id": case_id, "status": "OK", "model_used": experiment.MODEL,
                    "attempts": [], "score": {"assertions_exact": 0, "assertions_total": 0,
                    "value_matches": 0, "state_matches": 0, "refs_matches": 0,
                    "resolution_ok": True, "hard_failures": []},
                    "actual": {"nested": [f"x-{secret}-y"]}}]
        with tempfile.TemporaryDirectory() as tmp, patch.object(experiment, "CASES", (case_id,)):
            path = Path(tmp) / "report.json"
            _, txt = experiment.persist_report(path, results, by_id, set(), [], 0, "COMPLETED", secret)
            material = path.read_text(encoding="utf-8") + txt.read_text(encoding="utf-8")
        self.assertNotIn(secret, material)
        self.assertIn("[REDACTED]", material)

    def test_route_exhaustion_aborts_before_next_sleep(self):
        case_ids = ("c1", "c2")
        cases = [{"case_id": cid, "domain": "security", "lifecycle": "EXECUTED",
                  "clauses": [], "assertions": []} for cid in case_ids]
        def exhaust(_key, _prompt, _count, unavailable, attempts, case_id):
            unavailable.update(experiment.MODEL_ROUTE)
            attempts.append({"case_id": case_id, "model": experiment.MODEL, "attempt": 1,
                             "status": "ERROR", "failure_class": "daily_quota", "duration_ms": 1})
            raise RuntimeError("daily_quota")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus.json"
            corpus.write_text(json.dumps({"cases": cases}), encoding="utf-8")
            with patch.object(experiment, "CASES", case_ids), patch.object(experiment, "CORPUS", corpus), \
                 patch.object(experiment, "desktop_dirs", return_value=[root]), \
                 patch.object(experiment, "load_key", return_value=("key", None)), \
                 patch.object(experiment, "call_gemini", side_effect=exhaust), \
                 patch.object(experiment.time, "sleep") as sleep:
                report, _ = experiment.run()
        self.assertEqual(report["status"], "ABORTED_ROUTE_EXHAUSTED")
        self.assertEqual(len(report["results"]), 1)
        sleep.assert_not_called()

    def test_last_case_route_exhaustion_persists_aborted_status(self):
        case_id = "c1"
        case = {"case_id": case_id, "domain": "security", "lifecycle": "EXECUTED",
                "clauses": [], "assertions": []}
        quota_payload = json.dumps({"error": {"details": [{
            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
            "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}],
        }]}}).encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus.json"
            corpus.write_text(json.dumps({"cases": [case]}), encoding="utf-8")
            with patch.object(experiment, "CASES", (case_id,)), patch.object(experiment, "CORPUS", corpus), \
                 patch.object(experiment, "desktop_dirs", return_value=[root]), \
                 patch.object(experiment, "load_key", return_value=("key", None)), \
                 patch.object(experiment.request, "urlopen", side_effect=[
                     http_error(429, quota_payload), http_error(429, quota_payload)]
                 ) as urlopen, patch.object(experiment.time, "sleep") as sleep:
                report, _ = experiment.run()
            saved = json.loads(next(root.glob("security_provider_experiment_*.json")).read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ABORTED_ROUTE_EXHAUSTED")
        self.assertEqual(saved["status"], "ABORTED_ROUTE_EXHAUSTED")
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(len(report["attempts"]), 2)
        self.assertEqual([x["model"] for x in report["attempts"]], list(experiment.MODEL_ROUTE))
        self.assertTrue(all(x["failure_class"] == "daily_quota" for x in report["attempts"]))
        sleep.assert_not_called()

    def test_global_error_checkpoints_before_propagating(self):
        case_id = "c1"
        case = {"case_id": case_id, "domain": "security", "lifecycle": "EXECUTED",
                "clauses": [], "assertions": []}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus.json"
            corpus.write_text(json.dumps({"cases": [case]}), encoding="utf-8")
            with patch.object(experiment, "CASES", (case_id,)), patch.object(experiment, "CORPUS", corpus), \
                 patch.object(experiment, "desktop_dirs", return_value=[root]), \
                 patch.object(experiment, "load_key", return_value=("key", None)), \
                 patch.object(experiment, "call_gemini", side_effect=experiment.GlobalProviderError("auth")):
                with self.assertRaises(experiment.GlobalProviderError):
                    experiment.run()
            saved = json.loads(next(root.glob("security_provider_experiment_*.json")).read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "ABORTED_GLOBAL_PROVIDER_ERROR")

    def test_internal_abort_is_checkpointed(self):
        case_id = "c1"
        case = {"case_id": case_id, "domain": "security", "lifecycle": "EXECUTED",
                "clauses": [], "assertions": []}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "corpus.json"
            corpus.write_text(json.dumps({"cases": [case]}), encoding="utf-8")
            with patch.object(experiment, "CASES", (case_id,)), patch.object(experiment, "CORPUS", corpus), \
                 patch.object(experiment, "desktop_dirs", return_value=[root]), \
                 patch.object(experiment, "load_key", return_value=("key", None)), \
                 patch.object(experiment, "call_gemini", side_effect=ValueError("boom")):
                report, _ = experiment.run()
            saved = json.loads(next(root.glob("security_provider_experiment_*.json")).read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "ABORTED_INTERNAL_ERROR")
        self.assertEqual(saved["status"], "ABORTED_INTERNAL_ERROR")

    def test_terminal_json_is_published_after_txt(self):
        case_id = "c1"
        by_id = {case_id: {"assertions": [], "resolution": None}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(experiment, "CASES", (case_id,)):
            path = Path(tmp) / "report.json"
            txt = path.with_suffix(".txt")
            path.write_text('{"status":"OLD"}', encoding="utf-8")
            txt.write_text("OLD", encoding="utf-8")
            original_replace = Path.replace
            def fail_json_publish(source, target):
                if source.name.endswith(".json.tmp"):
                    raise OSError("stop before canonical JSON commit")
                return original_replace(source, target)
            with patch.object(Path, "replace", new=fail_json_publish):
                with self.assertRaises(OSError):
                    experiment.persist_report(path, [], by_id, set(), [], 0, "COMPLETED", "key")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"], "OLD")
            self.assertIn("Run status: COMPLETED", txt.read_text(encoding="utf-8"))

    def test_single_model_report_has_no_fake_fallback(self):
        case_id = "c1"
        by_id = {case_id: {"assertions": [], "resolution": None}}
        with patch.object(experiment, "MODEL", experiment.FALLBACK_MODEL), \
             patch.object(experiment, "MODEL_ROUTE", (experiment.FALLBACK_MODEL,)), \
             patch.object(experiment, "CASES", (case_id,)):
            report = experiment.make_report([], by_id, set(), [], 0, "COMPLETED")
        self.assertEqual(report["model_route"], [experiment.FALLBACK_MODEL])
        self.assertIsNone(report["fallback_model"])
        self.assertIn(f"Model route: {experiment.FALLBACK_MODEL}", experiment.render(report))


if __name__ == "__main__":
    unittest.main()
