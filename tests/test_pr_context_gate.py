from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_pr_context_gate", ROOT / "scripts" / "check_pr_context_gate.py"
)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class ContextGateTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "base"
        self.head = self.root / "head"
        self.base.mkdir()
        self.head.mkdir()
        self.pr_number = 141
        self.base_version = "privacy-ocr-2026-07-22-01"
        self.head_version = "privacy-ocr-2026-07-22-02"
        self.change_id = "context-gate-ci-v0"
        self.next_step_id = "android-reviewer-device-pilot-v0"
        self.next_step_summary = (
            "Build and install the controlled Android reviewer APK, then run the "
            "repository-external human pilot on Samsung A55 without external image calls."
        )
        self._write_fixture()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _state(self, version: str, pr: int, change: str) -> dict[str, object]:
        return {
            "schema_version": 1,
            "state_version": version,
            "active_track": "local-pii-redaction",
            "next_step_id": self.next_step_id,
            "next_step_summary": self.next_step_summary,
            "last_recorded_pr": pr,
            "last_recorded_change": change,
            "state_update_required_per_pr": True,
            "canonical_state_document": "docs/OCR_PROJECT_STATE.md",
            "updated_on": "2026-07-22",
        }

    def _write_fixture(self) -> None:
        common_files = {
            "AGENTS.md": "agents base\n",
            "docs/ARCHITECTURE.md": "architecture base\n",
            "docs/CUSTOM_OCR_PIPELINE.md": "pipeline base\n",
        }
        for relative, content in common_files.items():
            self._write(self.base, relative, content)
            self._write(self.head, relative, content)

        base_state = self._state(self.base_version, 140, "repository-context-gate-v0")
        head_state = self._state(self.head_version, self.pr_number, self.change_id)
        self._write(
            self.base,
            "docs/OCR_PROJECT_STATE.json",
            json.dumps(base_state, ensure_ascii=False, indent=2) + "\n",
        )
        self._write(
            self.head,
            "docs/OCR_PROJECT_STATE.json",
            json.dumps(head_state, ensure_ascii=False, indent=2) + "\n",
        )
        self._write(
            self.base,
            "docs/OCR_PROJECT_STATE.md",
            "# State\n\nПоследнее обновление: 2026-07-22, PR #140 old.\n",
        )
        self._write(
            self.head,
            "docs/OCR_PROJECT_STATE.md",
            f"""# State

Последнее обновление: 2026-07-22, PR #{self.pr_number} Context Gate CI v0.

## 0. Последнее изменение

### PR #{self.pr_number} — Context Gate CI v0

- Идентификатор: `{self.change_id}`.
- Изменение: added a trusted validator.
- Проверено: focused tests passed.
- Осталось: branch protection must be configured separately.
- Влияние: runtime/data/API behavior unchanged.
- Следующий шаг: `{self.next_step_id}` без изменений.

## 1. Product
""",
        )

    def _body(self) -> str:
        base_shas = {
            relative: checker.git_blob_sha((self.base / relative).read_bytes())
            for relative in checker.BINDING_PATHS
        }
        checks = "\n".join(
            f"- [x] {snippet}" for snippet in checker.REQUIRED_CHECKBOX_SNIPPETS
        )
        return f"""## PR Context Gate

{checks}

```text
PR CONTEXT GATE

active_track: local-pii-redaction
state_version: {self.base_version}
next_step_id: {self.next_step_id}
permitted_next_step: {self.next_step_summary}
task_scope: Add Context Gate CI v0.
explicitly_out_of_scope: Product runtime and data changes.
exception_authorization: Explicit product-owner approval for PR2.
state_change: Process enforcement only.
binding_document_shas:
  AGENTS.md: {base_shas['AGENTS.md']}
  docs/ARCHITECTURE.md: {base_shas['docs/ARCHITECTURE.md']}
  docs/CUSTOM_OCR_PIPELINE.md: {base_shas['docs/CUSTOM_OCR_PIPELINE.md']}
  docs/OCR_PROJECT_STATE.md: {base_shas['docs/OCR_PROJECT_STATE.md']}
  docs/OCR_PROJECT_STATE.json: {base_shas['docs/OCR_PROJECT_STATE.json']}
```

```text
state_update:
  recorded_pr: {self.pr_number}
  new_state_version: {self.head_version}
  recorded_change: {self.change_id}
  next_step_effect: unchanged
```
"""

    def _event(self, *, body: str | None = None, draft: bool = False) -> dict[str, object]:
        return {
            "number": self.pr_number,
            "pull_request": {
                "number": self.pr_number,
                "body": self._body() if body is None else body,
                "draft": draft,
            },
        }

    def test_valid_gate_passes(self) -> None:
        self.assertEqual([], checker.validate_gate(self._event(), self.base, self.head))

    def test_draft_pr_is_skipped(self) -> None:
        self.assertEqual([], checker.validate_gate(self._event(draft=True), self.base, self.head))

    def test_missing_checkbox_fails(self) -> None:
        body = self._body().replace(
            "- [x] Ready for review.", "- [ ] Ready for review."
        )
        errors = checker.validate_gate(self._event(body=body), self.base, self.head)
        self.assertTrue(any("Ready for review" in error for error in errors))

    def test_stale_binding_sha_fails(self) -> None:
        body = self._body().replace(
            checker.git_blob_sha((self.base / "AGENTS.md").read_bytes()), "0" * 40
        )
        errors = checker.validate_gate(self._event(body=body), self.base, self.head)
        self.assertTrue(any("binding SHA mismatch for AGENTS.md" in error for error in errors))

    def test_state_files_must_change(self) -> None:
        (self.head / "docs/OCR_PROJECT_STATE.md").write_bytes(
            (self.base / "docs/OCR_PROJECT_STATE.md").read_bytes()
        )
        errors = checker.validate_gate(self._event(), self.base, self.head)
        self.assertTrue(any("every PR must change docs/OCR_PROJECT_STATE.md" in error for error in errors))

    def test_wrong_recorded_pr_fails(self) -> None:
        state = json.loads((self.head / "docs/OCR_PROJECT_STATE.json").read_text())
        state["last_recorded_pr"] = 999
        (self.head / "docs/OCR_PROJECT_STATE.json").write_text(
            json.dumps(state), encoding="utf-8"
        )
        errors = checker.validate_gate(self._event(), self.base, self.head)
        self.assertTrue(any("last_recorded_pr" in error for error in errors))

    def test_state_version_must_advance(self) -> None:
        state = json.loads((self.head / "docs/OCR_PROJECT_STATE.json").read_text())
        state["state_version"] = self.base_version
        (self.head / "docs/OCR_PROJECT_STATE.json").write_text(
            json.dumps(state), encoding="utf-8"
        )
        body = self._body().replace(self.head_version, self.base_version)
        errors = checker.validate_gate(self._event(body=body), self.base, self.head)
        self.assertTrue(any("strictly newer" in error for error in errors))

    def test_next_step_change_requires_authorization(self) -> None:
        state = json.loads((self.head / "docs/OCR_PROJECT_STATE.json").read_text())
        state["next_step_id"] = "different-step"
        state["next_step_summary"] = "Different step."
        (self.head / "docs/OCR_PROJECT_STATE.json").write_text(
            json.dumps(state), encoding="utf-8"
        )
        errors = checker.validate_gate(self._event(), self.base, self.head)
        self.assertTrue(any("requires explicit next_step_effect" in error for error in errors))

    def test_structured_state_record_is_required(self) -> None:
        markdown = (self.head / "docs/OCR_PROJECT_STATE.md").read_text()
        (self.head / "docs/OCR_PROJECT_STATE.md").write_text(
            markdown.replace("- Проверено:", "- Evidence:"), encoding="utf-8"
        )
        errors = checker.validate_gate(self._event(), self.base, self.head)
        self.assertTrue(any("Проверено:" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
