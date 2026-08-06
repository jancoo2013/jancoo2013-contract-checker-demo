from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "context-gate.yml"


class ContextGateWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_keeps_required_workflow_and_job_names(self) -> None:
        self.assertRegex(self.text, r"(?m)^name: PR context gate$")
        self.assertRegex(self.text, r"(?m)^  validate-context:$")

    def test_supports_pr_events_and_manual_diagnostics(self) -> None:
        self.assertIn("pull_request_target:", self.text)
        self.assertIn(
            "types: [opened, edited, synchronize, reopened, ready_for_review]",
            self.text,
        )
        self.assertIn("workflow_dispatch:", self.text)
        self.assertRegex(self.text, r"(?m)^      pr_number:$")

    def test_does_not_depend_on_downloadable_actions(self) -> None:
        self.assertNotRegex(self.text, r"(?m)^\s*-?\s*uses:")
        self.assertNotIn("actions/checkout", self.text)
        self.assertNotIn("actions/setup-python", self.text)

    def test_executes_only_the_trusted_validator(self) -> None:
        run_commands = "\n".join(
            line.strip() for line in self.text.splitlines() if "python3 " in line
        )
        self.assertIn("python3 trusted/scripts/check_pr_context_gate.py", run_commands)
        self.assertNotIn("candidate/scripts/", run_commands)

    def test_has_read_only_permissions_and_bounded_network_calls(self) -> None:
        self.assertIn("contents: read", self.text)
        self.assertIn("pull-requests: read", self.text)
        self.assertNotIn("contents: write", self.text)
        self.assertNotIn("pull-requests: write", self.text)
        self.assertIn("--max-time 90", self.text)
        self.assertIn("--retry 3", self.text)
        self.assertEqual(len(re.findall(r"tarball/\$sha", self.text)), 1)


if __name__ == "__main__":
    unittest.main()
