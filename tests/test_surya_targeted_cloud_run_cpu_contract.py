from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "research" / "ocr_benchmark"
DOCKER = B / "Dockerfile.surya-targeted-cloud-run-cpu"
ENTRY = B / "surya_targeted_cloud_run_entrypoint.sh"
SERVER = B / "surya_targeted_cloud_run_server.py"
SERVICE = B / "cloud_run_targeted_cpu_service.template.yaml"


def _shell() -> str | None:
    shell, git = shutil.which("sh"), shutil.which("git")
    candidate = Path(git).parent.parent / "bin" / "sh.exe" if git else None
    return shell or (str(candidate) if candidate and candidate.is_file() else None)


class TargetedCloudRunCPUContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.docker = DOCKER.read_text(encoding="utf-8")
        cls.entry = ENTRY.read_text(encoding="utf-8")
        cls.server = SERVER.read_text(encoding="utf-8")
        cls.service = SERVICE.read_text(encoding="utf-8")

    def test_image_is_pinned_narrow_and_runtime_offline(self):
        self.assertIn("surya-ocr==0.22.1", self.docker)
        self.assertEqual(self.docker.count("sha256sum -c -"), 2)
        self.assertIn("HF_HUB_OFFLINE=1", self.docker)
        self.assertIn("surya_targeted_region_benchmark.py", self.docker)
        self.assertNotIn("surya_fullframe_worker.py", self.docker)
        self.assertNotIn("COPY .", self.docker)

    def test_llama_cpu_parallelism_matches_targeted_client_ceiling(self):
        for expected in ("--parallel 4", "--ctx-size 49152", "--threads 8", "--threads-batch 8", "--n-gpu-layers 0", "--host 127.0.0.1"):
            self.assertIn(expected, self.entry)
        self.assertIn("SURYA_INFERENCE_PARALLEL=4", self.docker)
        self.assertIn("settings.SURYA_INFERENCE_PARALLEL = self.parallelism", self.server)
        self.assertIn("_PREDICTOR = RecognitionPredictor(_MANAGER)", self.server)

    def test_service_is_bounded_cpu_only_and_israel_only(self):
        self.assertGreaterEqual(self.service.count("me-west1"), 3)
        for expected in ('cpu: "8"', "memory: 16Gi", 'autoscaling.knative.dev/minScale: "0"', 'autoscaling.knative.dev/maxScale: "1"', "containerConcurrency: 1"):
            self.assertIn(expected, self.service)
        for forbidden in ("nvidia.com/gpu", "accelerator", "europe-", "us-"):
            self.assertNotIn(forbidden, self.service.lower())

    def test_http_contract_is_bounded_and_aggregate_only(self):
        for expected in ("MAX_REQUEST_BYTES", "MAX_REGIONS_HEADER_CHARS", "X-Surya-Parallel", "X-Surya-Regions", "ALLOWED_PARALLELISM", "PNG_SIGNATURE", "os.unlink(temp_path)"):
            self.assertIn(expected, self.server)
        for forbidden in ('"text"', '"bbox"', "print("):
            self.assertNotIn(forbidden, self.server)
        self.assertIn("def log_message", self.server)
        self.assertIn('"TEMP_CLEANUP_FAILED"', self.server)

    def test_no_production_subsystem_is_added(self):
        combined = "\n".join((self.docker, self.entry, self.server, self.service)).lower()
        for forbidden in ("gemini", "redis", "rabbitmq", "terraform", "database_url", "pii mask"):
            self.assertNotIn(forbidden, combined)

    @unittest.skipUnless(_shell(), "POSIX shell unavailable")
    def test_entrypoint_shell_syntax(self):
        result = subprocess.run([_shell(), "-n", str(ENTRY)], capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
