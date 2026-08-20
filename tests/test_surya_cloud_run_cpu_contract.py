from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "research" / "ocr_benchmark"
DOCKERFILE = BENCHMARK / "Dockerfile.surya-cloud-run-cpu"
ENTRYPOINT = BENCHMARK / "surya_cloud_run_entrypoint.sh"
SERVER = BENCHMARK / "surya_cloud_run_server.py"
SERVICE = BENCHMARK / "cloud_run_cpu_service.template.yaml"


def _shell() -> str | None:
    shell = shutil.which("sh")
    git = shutil.which("git")
    candidate = Path(git).parent.parent / "bin" / "sh.exe" if git else None
    return shell or (str(candidate) if candidate and candidate.is_file() else None)


SHELL = _shell()


class SuryaCloudRunCPUContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.docker = DOCKERFILE.read_text(encoding="utf-8")
        cls.entrypoint = ENTRYPOINT.read_text(encoding="utf-8")
        cls.server = SERVER.read_text(encoding="utf-8")
        cls.service = SERVICE.read_text(encoding="utf-8")

    def test_image_build_is_pinned_narrow_and_offline_at_runtime(self):
        self.assertIn("surya-ocr==0.22.1", self.docker)
        self.assertRegex(self.docker, r"LLAMA_CPP_REVISION=[0-9a-f]{40}\n")
        self.assertRegex(self.docker, r"SURYA_MODEL_REVISION=[0-9a-f]{40}\n")
        self.assertEqual(self.docker.count("sha256sum -c -"), 2)
        self.assertNotRegex(self.docker.lower(), r"(?:^|[/:@-])latest(?:$|[\s\"'])")
        self.assertNotIn("COPY .", self.docker)
        self.assertNotIn("COPY research/ocr_benchmark/ ", self.docker)
        self.assertIn("HF_HUB_OFFLINE=1", self.docker)
        self.assertIn("TRANSFORMERS_OFFLINE=1", self.docker)
        self.assertIn("USER benchmark", self.docker)
        self.assertNotIn("huggingface.co", self.entrypoint)
        self.assertNotIn("curl ", self.entrypoint)
        self.assertNotIn("wget ", self.entrypoint)

    def test_cloud_run_contract_is_cpu_only_israel_and_scale_to_zero(self):
        self.assertEqual(self.service.count("me-west1"), 4)
        self.assertIn('cpu: "8"', self.service)
        self.assertIn("memory: 16Gi", self.service)
        self.assertIn('autoscaling.knative.dev/minScale: "0"', self.service)
        self.assertIn('autoscaling.knative.dev/maxScale: "1"', self.service)
        self.assertIn("containerConcurrency: 1", self.service)
        self.assertIn('run.googleapis.com/startup-cpu-boost: "true"', self.service)
        self.assertIn("timeoutSeconds: 900", self.service)
        self.assertIn("failureThreshold: 24", self.service)
        for forbidden in ("nvidia.com/gpu", "run.googleapis.com/accelerator", "multi-region", "europe-", "us-"):
            self.assertNotIn(forbidden, self.service.lower())

    def test_llama_server_is_internal_and_wrapper_owns_cloud_run_port(self):
        self.assertIn("--host 127.0.0.1", self.entrypoint)
        self.assertIn("--n-gpu-layers 0", self.entrypoint)
        self.assertNotIn("--host 0.0.0.0", self.entrypoint)
        self.assertIn('PORT=8080', self.docker)
        self.assertIn('os.environ.get("PORT"', self.server)
        self.assertIn('("0.0.0.0", int(port_text))', self.server)

    def test_http_input_and_output_are_bounded_and_non_sensitive(self):
        self.assertIn("MAX_REQUEST_BYTES = 16 * 1024 * 1024", self.server)
        self.assertIn('SUPPORTED_MEDIA_TYPE = "image/png"', self.server)
        self.assertIn("Content-Length", self.server)
        self.assertIn("PNG_SIGNATURE", self.server)
        self.assertIn("recognized_characters", self.server)
        self.assertNotIn('"text"', self.server)
        self.assertNotIn('"bbox"', self.server)
        self.assertNotIn("print(", self.server)
        self.assertIn("def log_message", self.server)
        self.assertRegex(self.server, r"finally:\n\s+if temp_path is not None:")
        self.assertIn("os.unlink(temp_path)", self.server)
        self.assertIn('"TEMP_CLEANUP_FAILED"', self.server)

    def test_startup_is_bounded_and_engine_is_reused(self):
        self.assertIn('startup_seconds="${SURYA_BACKEND_STARTUP_SECONDS:-220}"', self.entrypoint)
        self.assertIn('time.monotonic() + timeout', self.entrypoint)
        self.assertIn("kill -KILL", self.entrypoint)
        self.assertIn("for _attempt in 1 2 3 4 5", self.entrypoint)
        self.assertEqual(self.server.count("_ENGINE = SuryaEngine()"), 1)
        self.assertIn("engine=_ENGINE", self.server)
        self.assertIn('"model_startup_ms"', self.server)

    def test_no_production_subsystem_is_introduced(self):
        combined = "\n".join((self.docker, self.entrypoint, self.server, self.service)).lower()
        for forbidden in ("gemini", "redis", "rabbitmq", "terraform", "github actions", "pii mask", "database_url"):
            self.assertNotIn(forbidden, combined)

    @unittest.skipUnless(SHELL, "POSIX shell is unavailable")
    def test_entrypoint_shell_syntax(self):
        result = subprocess.run([SHELL, "-n", str(ENTRYPOINT)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
