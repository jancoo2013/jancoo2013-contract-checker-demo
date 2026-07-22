from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gate", ROOT / "scripts/check_pr_context_gate.py")
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base, self.head = Path(self.tmp.name) / "base", Path(self.tmp.name) / "head"
        self.base.mkdir(); self.head.mkdir()
        self.number = 145
        self.base_version = "privacy-ocr-2026-07-22-04"
        self.head_version = "privacy-ocr-2026-07-22-05"
        self.change = "context-gate-scope-v1"
        self.step = "android-reviewer-device-pilot-v0"
        self.summary = "Prepare a safe synthetic review pack and verify it on Samsung A55."
        self.write(self.base, "scripts/example.py", "old\n")
        self.write(self.head, "scripts/example.py", "new\n")
        self.write_state(self.base, self.base_version, 143, "android-reviewer-standalone-apk-v0")
        self.write_state(self.head, self.head_version, self.number, self.change)
        self.write(self.base, GATE.STATE_MD, "Последнее обновление: 2026-07-22, PR #143.\n")
        self.write(self.head, GATE.STATE_MD, self.record())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def write(root: Path, rel: str, value: str) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def write_state(self, root: Path, version: str, number: int, change: str) -> None:
        value = {
            "schema_version": 1,
            "state_version": version,
            "active_track": "local-pii-redaction",
            "next_step_id": self.step,
            "next_step_summary": self.summary,
            "last_recorded_pr": number,
            "last_recorded_change": change,
            "state_update_required_per_pr": True,
            "canonical_state_document": GATE.STATE_MD,
            "updated_on": "2026-07-22",
        }
        self.write(root, GATE.STATE_JSON, json.dumps(value) + "\n")

    def record(self) -> str:
        return f"""# State

Последнее обновление: 2026-07-22, PR #{self.number}.

## 0. Последнее изменение

Изменение `{self.change}`. Следующий шаг `{self.step}`.

## 1. Product
"""

    def contract(self, paths: list[str] | None = None, change: str | None = None) -> str:
        value = {
            "context_gate_version": 1,
            "change": change or self.change,
            "allowed_paths": paths or ["scripts/example.py", GATE.STATE_MD, GATE.STATE_JSON],
        }
        return "Пояснение может быть написано как угодно.\n```json\n" + json.dumps(value, indent=2) + "\n```\n"

    def event(self, body: str | None = None, draft: bool = False) -> dict:
        return {"number": self.number, "pull_request": {"number": self.number, "body": body or self.contract(), "draft": draft}}

    def test_valid_contract_and_draft(self) -> None:
        self.assertEqual([], GATE.validate(self.event(), self.base, self.head))
        self.assertEqual([], GATE.validate(self.event(draft=True), self.base, self.head))

    def test_prose_and_punctuation_are_irrelevant(self) -> None:
        body = "Без чекбоксов. Пунктуация?! Не важна.\n" + self.contract()
        self.assertEqual([], GATE.validate(self.event(body), self.base, self.head))

    def test_undeclared_extra_file_is_blocked(self) -> None:
        self.write(self.head, "surprise.txt", "unexpected\n")
        errors = GATE.validate(self.event(), self.base, self.head)
        self.assertIn("undeclared changed paths: surprise.txt", errors)

    def test_declared_but_unchanged_file_is_blocked(self) -> None:
        self.write(self.base, "README.md", "same\n")
        self.write(self.head, "README.md", "same\n")
        paths = ["scripts/example.py", "README.md", GATE.STATE_MD, GATE.STATE_JSON]
        errors = GATE.validate(self.event(self.contract(paths)), self.base, self.head)
        self.assertIn("allowed_paths entries did not change: README.md", errors)

    def test_path_contract_rejects_duplicates_and_traversal(self) -> None:
        paths = ["scripts/example.py", "../escape", GATE.STATE_MD, GATE.STATE_JSON, GATE.STATE_JSON]
        errors = GATE.validate(self.event(self.contract(paths)), self.base, self.head)
        self.assertTrue(any("invalid allowed path" in error for error in errors))
        self.assertIn("allowed_paths must not contain duplicates", errors)

    def test_control_character_path_is_rejected(self) -> None:
        paths = ["scripts/example.py", "bad\npath", GATE.STATE_MD, GATE.STATE_JSON]
        errors = GATE.validate(self.event(self.contract(paths)), self.base, self.head)
        self.assertTrue(any("invalid allowed path" in error for error in errors))

    def test_missing_or_extra_contract_keys_are_blocked(self) -> None:
        value = {
            "context_gate_version": 1,
            "change": self.change,
            "allowed_paths": ["scripts/example.py", GATE.STATE_MD, GATE.STATE_JSON],
            "authorization": "claimed",
        }
        body = "```json\n" + json.dumps(value) + "\n```"
        errors = GATE.validate(self.event(body), self.base, self.head)
        self.assertTrue(any("must contain only" in error for error in errors))

    def test_state_version_number_and_change_are_checked(self) -> None:
        value = json.loads((self.head / GATE.STATE_JSON).read_text(encoding="utf-8"))
        value["state_version"] = self.base_version
        value["last_recorded_pr"] = 999
        value["last_recorded_change"] = "different-change"
        self.write(self.head, GATE.STATE_JSON, json.dumps(value) + "\n")
        errors = GATE.validate(self.event(), self.base, self.head)
        self.assertIn("state_version must increase", errors)
        self.assertTrue(any("last_recorded_pr" in error for error in errors))
        self.assertIn("last_recorded_change must match context gate change", errors)

    def test_state_summary_requires_machine_facts_not_fixed_prose(self) -> None:
        self.write(self.head, GATE.STATE_MD, self.record().replace(self.change, "missing-change"))
        errors = GATE.validate(self.event(), self.base, self.head)
        self.assertTrue(any(self.change in error for error in errors))

    def test_executable_bit_change_is_detected(self) -> None:
        os.chmod(self.base / "scripts/example.py", 0o644)
        os.chmod(self.head / "scripts/example.py", 0o755)
        self.assertIn("scripts/example.py", GATE.changed_paths(self.base, self.head))


if __name__ == "__main__":
    unittest.main()
