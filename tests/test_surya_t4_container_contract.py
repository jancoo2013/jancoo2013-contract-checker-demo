from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "research" / "ocr_benchmark" / "Dockerfile.surya-t4"
ENTRYPOINT = ROOT / "research" / "ocr_benchmark" / "surya_t4_entrypoint.sh"
JOB_TEMPLATE = ROOT / "research" / "ocr_benchmark" / "google_batch_t4_job.template.json"


class SuryaT4ContainerContractTests(unittest.TestCase):
    def test_dockerfile_copies_only_required_benchmark_files(self):
        text = DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("FROM python:3.12.11-slim-bookworm", text)
        self.assertIn("surya_fullframe_worker.py", text)
        self.assertIn("requirements-surya.txt", text)
        self.assertNotIn("COPY . ", text)
        self.assertNotIn("COPY research/ocr_benchmark/ /app", text)
        self.assertNotIn("dataset", text)
        self.assertNotIn("artifacts", text)

    def test_entrypoint_has_bounded_wait_pages_and_safe_metrics_output(self):
        text = ENTRYPOINT.read_text(encoding="utf-8")
        self.assertIn("SURYA_BACKEND_WAIT_SECONDS:-600", text)
        self.assertIn('page_count" -gt 10', text)
        self.assertIn("--metrics-output", text)
        self.assertIn("surya_fullframe_worker", text)
        self.assertNotIn("results.json", text)

    @unittest.skipUnless(shutil.which("sh"), "POSIX shell is unavailable")
    def test_entrypoint_shell_syntax(self):
        completed = subprocess.run(["sh", "-n", str(ENTRYPOINT)], capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_google_batch_template_is_single_t4_israel_only_and_no_retry(self):
        payload = json.loads(JOB_TEMPLATE.read_text(encoding="utf-8"))
        group = payload["taskGroups"][0]
        task = group["taskSpec"]
        policy = payload["allocationPolicy"]
        instance = policy["instances"][0]
        accelerator = instance["policy"]["accelerators"][0]

        self.assertEqual(group["taskCount"], 1)
        self.assertEqual(group["parallelism"], 1)
        self.assertEqual(task["maxRetryCount"], 0)
        self.assertEqual(task["maxRunDuration"], "1800s")
        self.assertTrue(instance["installGpuDrivers"])
        self.assertEqual(instance["policy"]["machineType"], "n1-standard-8")
        self.assertEqual(instance["policy"]["provisioningModel"], "STANDARD")
        self.assertEqual(instance["policy"]["reservation"], "NO_RESERVATION")
        self.assertEqual(accelerator, {"type": "nvidia-tesla-t4", "count": 1})
        self.assertEqual(set(policy["location"]["allowedLocations"]), {"zones/me-west1-b", "zones/me-west1-c"})

    def test_google_batch_template_keeps_raw_result_out_of_cloud_logging(self):
        payload = json.loads(JOB_TEMPLATE.read_text(encoding="utf-8"))
        runnables = payload["taskGroups"][0]["taskSpec"]["runnables"]
        vllm = runnables[0]
        worker = runnables[1]

        self.assertTrue(vllm["background"])
        self.assertIn("--disable-log-requests", vllm["container"]["commands"])
        self.assertIn("--disable-uvicorn-access-log", vllm["container"]["commands"])
        self.assertEqual(worker["container"]["imageUri"], "__WORKER_IMAGE_URI__")
        self.assertEqual(worker["environment"]["variables"]["BENCHMARK_METRICS_OUTPUT"], "/mnt/disks/benchmark/output/metrics.json")
        self.assertEqual(payload["taskGroups"][0]["taskSpec"]["volumes"][0]["gcs"]["remotePath"], "__BENCHMARK_BUCKET__")
        self.assertEqual(payload["logsPolicy"]["destination"], "CLOUD_LOGGING")


if __name__ == "__main__":
    unittest.main()
