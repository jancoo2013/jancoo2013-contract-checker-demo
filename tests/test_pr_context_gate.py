from __future__ import annotations

import importlib.util
import json
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
        self.number = 141
        self.base_version, self.head_version = "privacy-ocr-2026-07-22-01", "privacy-ocr-2026-07-22-02"
        self.change, self.step = "context-gate-ci-v0", "android-reviewer-device-pilot-v0"
        self.summary = "Build and install the controlled Android reviewer APK, then run the repository-external human pilot on Samsung A55 without external image calls."
        for rel in GATE.PATHS[:3]:
            self.write(self.base, rel, rel + "\n"); self.write(self.head, rel, rel + "\n")
        self.write_state(self.base, self.base_version, 140, "repository-context-gate-v0")
        self.write_state(self.head, self.head_version, self.number, self.change)
        self.write(self.base, "docs/OCR_PROJECT_STATE.md", "Последнее обновление: 2026-07-22, PR #140 old.\n")
        self.write(self.head, "docs/OCR_PROJECT_STATE.md", self.record())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def write(root: Path, rel: str, value: str) -> None:
        path = root / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value, encoding="utf-8")

    def write_state(self, root: Path, version: str, number: int, change: str) -> None:
        value = {"schema_version": 1, "state_version": version, "active_track": "local-pii-redaction", "next_step_id": self.step, "next_step_summary": self.summary, "last_recorded_pr": number, "last_recorded_change": change, "state_update_required_per_pr": True, "canonical_state_document": "docs/OCR_PROJECT_STATE.md", "updated_on": "2026-07-22"}
        self.write(root, "docs/OCR_PROJECT_STATE.json", json.dumps(value) + "\n")

    def record(self) -> str:
        return f"""Последнее обновление: 2026-07-22, PR #{self.number} Context Gate CI v0.

## 0. Последнее изменение
### PR #{self.number} — Context Gate CI v0
- Идентификатор: `{self.change}`.
- Изменение: trusted validator.
- Проверено: focused tests.
- Осталось: branch protection.
- Влияние: runtime unchanged.
- Следующий шаг: `{self.step}` без изменений.

## 1. Product
"""

    def body(self) -> str:
        shas = {rel: GATE.blob_sha((self.base / rel).read_bytes()) for rel in GATE.PATHS}
        boxes = "\n".join(f"- [x] {item}" for item in GATE.CHECKS)
        return f"""{boxes}
```text
PR CONTEXT GATE
active_track: local-pii-redaction
state_version: {self.base_version}
next_step_id: {self.step}
permitted_next_step: {self.summary}
task_scope: Add CI.
explicitly_out_of_scope: Runtime.
exception_authorization: Product-owner approved PR2.
state_change: Process only.
binding_document_shas:
""" + "\n".join(f"  {key}: {value}" for key, value in shas.items()) + f"""
```
```text
state_update:
  recorded_pr: {self.number}
  new_state_version: {self.head_version}
  recorded_change: {self.change}
  next_step_effect: unchanged
```
"""

    def event(self, body: str | None = None, draft: bool = False) -> dict:
        return {"number": self.number, "pull_request": {"number": self.number, "body": body or self.body(), "draft": draft}}

    def test_valid_and_draft(self) -> None:
        self.assertEqual([], GATE.validate(self.event(), self.base, self.head))
        self.assertEqual([], GATE.validate(self.event(draft=True), self.base, self.head))

    def test_unchecked_box_and_stale_sha(self) -> None:
        body = self.body().replace("- [x] Ready for review.", "- [ ] Ready for review.")
        body = body.replace(GATE.blob_sha((self.base / "AGENTS.md").read_bytes()), "0" * 40)
        errors = GATE.validate(self.event(body), self.base, self.head)
        self.assertTrue(any("Ready for review" in error for error in errors))
        self.assertIn("binding SHA mismatch: AGENTS.md", errors)

    def test_state_files_and_number_are_required(self) -> None:
        (self.head / "docs/OCR_PROJECT_STATE.md").write_bytes((self.base / "docs/OCR_PROJECT_STATE.md").read_bytes())
        value = json.loads((self.head / "docs/OCR_PROJECT_STATE.json").read_text()); value["last_recorded_pr"] = 999
        self.write(self.head, "docs/OCR_PROJECT_STATE.json", json.dumps(value))
        errors = GATE.validate(self.event(), self.base, self.head)
        self.assertTrue(any("every PR must change docs/OCR_PROJECT_STATE.md" in error for error in errors))
        self.assertTrue(any("last_recorded_pr" in error for error in errors))

    def test_version_and_next_step_guards(self) -> None:
        value = json.loads((self.head / "docs/OCR_PROJECT_STATE.json").read_text())
        value["state_version"] = self.base_version; value["next_step_id"] = "different-step"
        self.write(self.head, "docs/OCR_PROJECT_STATE.json", json.dumps(value))
        errors = GATE.validate(self.event(self.body().replace(self.head_version, self.base_version)), self.base, self.head)
        self.assertIn("state_version must increase", errors)
        self.assertTrue(any("without explicit authorization" in error for error in errors))

    def test_structured_record_is_required(self) -> None:
        self.write(self.head, "docs/OCR_PROJECT_STATE.md", self.record().replace("Проверено:", "Evidence:"))
        self.assertTrue(any("Проверено:" in error for error in GATE.validate(self.event(), self.base, self.head)))


if __name__ == "__main__":
    unittest.main()
