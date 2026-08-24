from __future__ import annotations

import shutil, subprocess, unittest
from pathlib import Path

B = Path(__file__).resolve().parents[1] / "research" / "ocr_benchmark"
DOCKER, ENTRY = B / "Dockerfile.surya-targeted-cloud-run-cpu", B / "surya_targeted_cloud_run_entrypoint.sh"
SERVER, SERVICE = B / "surya_targeted_cloud_run_server.py", B / "cloud_run_targeted_cpu_service.template.yaml"


def _shell() -> str | None:
    git = shutil.which("git"); candidate = Path(git).parent.parent / "bin" / "sh.exe" if git else None
    return shutil.which("sh") or (str(candidate) if candidate and candidate.is_file() else None)


class TargetedCloudRunCPUContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.docker, cls.entry = DOCKER.read_text(), ENTRY.read_text()
        cls.server, cls.service = SERVER.read_text(), SERVICE.read_text()

    def test_pinned_offline_targeted_image(self):
        for value in ("surya-ocr==0.22.1", "HF_HUB_OFFLINE=1", "surya_targeted_region_benchmark.py"):
            self.assertIn(value, self.docker)
        self.assertEqual(2, self.docker.count("sha256sum -c -")); self.assertNotIn("surya_fullframe_worker.py", self.docker); self.assertNotIn("COPY .", self.docker)

    def test_cpu_parallelism_and_israel_service_bounds(self):
        for value in ("--parallel 4", "--ctx-size 49152", "--threads 8", "--threads-batch 8", "--n-gpu-layers 0", "--host 127.0.0.1"):
            self.assertIn(value, self.entry)
        for value in ('cpu: "8"', "memory: 16Gi", 'minScale: "0"', 'maxScale: "1"', "containerConcurrency: 1"):
            self.assertIn(value, self.service)
        self.assertGreaterEqual(self.service.count("me-west1"), 3); self.assertIn("SURYA_INFERENCE_PARALLEL=4", self.docker)

    def test_http_is_bounded_aggregate_only_and_cleanup_fail_closed(self):
        for value in ("MAX_REQUEST_BYTES", "MAX_REGIONS_HEADER_CHARS", "X-Surya-Parallel", "X-Surya-Regions", "ALLOWED_PARALLELISM", "PNG_SIGNATURE", "os.unlink(temp_path)", '"TEMP_CLEANUP_FAILED"', "def log_message"):
            self.assertIn(value, self.server)
        for forbidden in ('"text"', '"bbox"', "print(", "gemini", "database_url", "pii mask"):
            self.assertNotIn(forbidden, self.server.lower())
        for forbidden in ("nvidia.com/gpu", "accelerator", "europe-", "us-"):
            self.assertNotIn(forbidden, self.service.lower())

    @unittest.skipUnless(_shell(), "POSIX shell unavailable")
    def test_entrypoint_shell_syntax(self):
        result = subprocess.run([_shell(), "-n", str(ENTRY)], capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__": unittest.main()
