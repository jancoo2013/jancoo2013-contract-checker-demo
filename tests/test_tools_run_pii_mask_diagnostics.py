from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.run_pii_mask_diagnostics import PIIMaskRunnerError, run_diagnostics


def _result(command, returncode=0, stdout=""):
    return subprocess.CompletedProcess(command, returncode, stdout, "")


class PIIMaskDiagnosticsRunnerTests(unittest.TestCase):
    def test_uses_temporary_origin_main_worktree_and_publishes_sibling_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            pack = root / "2_review_pack"
            repo.mkdir()
            pack.mkdir()
            commands: list[list[str]] = []

            def fake_run(command, cwd):
                command = list(command)
                commands.append(command)
                if command[:3] == ["git", "worktree", "add"]:
                    Path(command[-2]).mkdir(parents=True)
                if "research.hebrew_contract_ocr.pii_mask_diagnostics" in command:
                    output = Path(command[command.index("--output") + 1])
                    output.write_text("{}\n", encoding="utf-8")
                    return _result(command, stdout="DIAGNOSTICS READY: 3 pages, 20 candidates, 41.2% masked\n")
                return _result(command)

            with patch("tools.run_pii_mask_diagnostics._run", side_effect=fake_run):
                output, marker = run_diagnostics(pack, repo_root=repo, python_executable="python")

            self.assertEqual(output, root / "2_review_pack-mask-diagnostics.json")
            self.assertTrue(output.is_file())
            self.assertIn("41.2% masked", marker)
            self.assertEqual(commands[0], ["git", "fetch", "--quiet", "origin", "main"])
            self.assertIn(["git", "worktree", "remove", "--force"], [item[:4] for item in commands])
            self.assertFalse(any(item[:2] == ["git", "switch"] for item in commands))

    def test_existing_report_blocks_before_git_or_python_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            pack = root / "2_review_pack"
            output = root / "2_review_pack-mask-diagnostics.json"
            repo.mkdir()
            pack.mkdir()
            output.write_text("keep", encoding="utf-8")

            with patch("tools.run_pii_mask_diagnostics._run") as mocked:
                with self.assertRaisesRegex(PIIMaskRunnerError, "already exists"):
                    run_diagnostics(pack, repo_root=repo)
            mocked.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), "keep")

    def test_diagnostic_failure_removes_temporary_worktree_and_partial_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            pack = root / "2_review_pack"
            repo.mkdir()
            pack.mkdir()
            commands: list[list[str]] = []

            def fake_run(command, cwd):
                command = list(command)
                commands.append(command)
                if command[:3] == ["git", "worktree", "add"]:
                    Path(command[-2]).mkdir(parents=True)
                if "research.hebrew_contract_ocr.pii_mask_diagnostics" in command:
                    output = Path(command[command.index("--output") + 1])
                    output.write_text("partial", encoding="utf-8")
                    return _result(command, returncode=1)
                return _result(command)

            with patch("tools.run_pii_mask_diagnostics._run", side_effect=fake_run):
                with self.assertRaisesRegex(PIIMaskRunnerError, "mask diagnostics failed"):
                    run_diagnostics(pack, repo_root=repo, python_executable="python")

            self.assertFalse((root / "2_review_pack-mask-diagnostics.json").exists())
            self.assertTrue(any(item[:4] == ["git", "worktree", "remove", "--force"] for item in commands))

    def test_missing_ready_marker_rejects_and_removes_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            pack = root / "2_review_pack"
            repo.mkdir()
            pack.mkdir()

            def fake_run(command, cwd):
                command = list(command)
                if command[:3] == ["git", "worktree", "add"]:
                    Path(command[-2]).mkdir(parents=True)
                if "research.hebrew_contract_ocr.pii_mask_diagnostics" in command:
                    output = Path(command[command.index("--output") + 1])
                    output.write_text("{}\n", encoding="utf-8")
                    return _result(command, stdout="unexpected output\n")
                return _result(command)

            with patch("tools.run_pii_mask_diagnostics._run", side_effect=fake_run):
                with self.assertRaisesRegex(PIIMaskRunnerError, "no ready marker"):
                    run_diagnostics(pack, repo_root=repo, python_executable="python")

            self.assertFalse((root / "2_review_pack-mask-diagnostics.json").exists())


if __name__ == "__main__":
    unittest.main()
