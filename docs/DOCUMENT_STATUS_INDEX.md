# Repository document status index

Purpose: prevent agents and developers from mistaking historical experiments, frozen component contracts, or old UX scenarios for the current product direction.

This file classifies repository documents. It does **not** choose `active_track` or `next_step_id`; those are selected only by `docs/OCR_PROJECT_STATE.md` and `docs/OCR_PROJECT_STATE.json`.

If this index conflicts with a binding source or canonical state, stop and report the conflict.

## 1. Always-read binding/current governance

Read these before implementation:

- `AGENTS.md` — repository working rules and context precedence.
- `SECURITY.md` — binding security/privacy review policy.
- `docs/ARCHITECTURE.md` — product architecture; deferred OCR sections do not select current work.
- `docs/CUSTOM_OCR_PIPELINE.md` — binding privacy/OCR contract; currently a frozen/deferred reference unless state reopens OCR.
- `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md` — frozen/deferred remote OCR architecture and privacy boundary unless state explicitly reopens it.
- `docs/OCR_PROJECT_STATE.md` — canonical operational state and permitted next step.
- `docs/OCR_PROJECT_STATE.json` — machine-readable mirror of current state identifiers.
- `docs/CODEX_WORKFLOW.md` — Codex execution/audit protocol; subordinate to binding sources and state.
- `.github/pull_request_template.md` — PR metadata/security template.
- `.github/workflows/context-gate.yml` and `scripts/check_pr_context_gate.py` — machine enforcement of Context Gate/state continuity.

## 2. Current Question Engine task context

Read these when the canonical task concerns Question Engine design/implementation:

- `docs/QUESTION_ENGINE_DISCOVERY_LOG.md` — consolidated current Question Engine product and UX decisions.
- `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md` — maintained statutory engineering map; not current-law authority by itself.
- `docs/statutory/README.md` — statutory source hierarchy/versioning policy.
- `docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2017_V1.json` — immutable historical 2017 normalized snapshot; never use alone as current law.
- `research/question_engine/golden_contracts/contract_001_he.txt` — sanitized printed Hebrew golden fixture.
- `research/question_engine/golden_contracts/contract_001.meta.json` — fixture provenance/sanitization metadata.

For `question-engine-question-inventory-v1`, these are the primary task-specific sources after the always-read governance set.

## 3. Frozen/deferred OCR and preprocessing references

These files preserve useful component decisions or research evidence but do not authorize current implementation unless state/task scope explicitly reopens the affected area:

- `docs/DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`
- `docs/PII_EVIDENCE_DETECTOR_V1.md`
- `docs/VISUAL_PII_LOCALIZATION_V1.md`
- `docs/SERVERLESS_OCR_WORKER_CONTRACT_V1.md`
- `docs/israel_region_ai_spike.md`
- research documents under `research/hebrew_contract_ocr/`
- research documents under `research/handwriting_gate/`
- research documents under `research/ocr_benchmark/`
- historical Android geometry/Tesseract component documentation under `mobile/` and its native modules.

A component contract may define exact behavior for that component, but it does not override the active track or reopen the component.

## 4. Historical/legacy UX and workflow scenarios

The following documents describe earlier prototype/testing flows. They are retained as historical evidence and may still support regression tests, but they are **not the current product UX or current implementation order**:

- `docs/mvp_ux_freeze.md` — closed Streamlit prototype with manual masking/OCR/report sections.
- `docs/MOBILE_USER_FLOW_V0.md` — earlier mobile capture/on-device-processing concept; superseded where it conflicts with current state, privacy architecture, or Question Engine UX.
- `docs/MODEL_ASSISTED_GOLD_TESTING_V0.md` — earlier recognizer/Gold review workflow; recognizer work is frozen unless explicitly reopened.
- `docs/mobile_backend_api_contract.md` — earlier mobile-to-backend redacted-image vertical-slice contract; does not define the current production privacy boundary.
- `docs/cloud_ocr_plan.md` — early Cloud OCR/demo plan; superseded by the frozen serverless/privacy architecture and current state.
- `mobile/README.md` — documentation of earlier Android Tesseract/transport test slices; Tesseract full-page OCR is not the current path.
- `README.md` sections describing the old Streamlit/Gemini/manual-mask prototype — historical prototype instructions, not canonical direction.

Current user-facing Question Engine report/negotiation UX is defined by the consolidated decisions in `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`, subject to future explicit product changes.

## 5. Optional audit/reference documents

These may be read when explicitly performing the corresponding audit/research task, but are not mandatory implementation context:

- `docs/GEMINI_PROJECT_AUDIT.md` — optional external-project-audit prompt/protocol; not a binding source and not a substitute for Codex workflow or current state.
- `docs/FUTURE_PRODUCT_AND_ARCHITECTURE_IDEAS.md` — non-binding future ideas and hypotheses.
- `docs/PR_CONTEXT_GATE_CANARY.md` — context-gate test/canary documentation.

## 6. README and code are not state selectors

Repository `README.md`, `mobile/README.md`, source code, test names, branch names, and old PR descriptions may describe implemented or historical behavior. They must not be used to infer the current product direction when canonical state says otherwise.

Code that remains in the repository after a track is frozen is retained implementation/research material, not implicit authorization to continue that track.

## 7. Conflict handling

When a document appears to disagree with current state:

1. determine its class using this index;
2. if it is historical/frozen/component-only, do not let it override current state;
3. if it is always-read binding/current governance, stop implementation and report the conflict;
4. if the task requires reactivating a frozen document/component, obtain an explicit product/state decision first;
5. never resolve a genuine binding conflict by silently choosing the more convenient document.

## 8. Maintenance rule

Update this index when:

- a new long-lived governing document is added;
- a previously current scenario is frozen/superseded;
- a frozen subsystem is explicitly reopened;
- a task-specific source becomes mandatory for an active track;
- a document's authority level materially changes.

Do not update it merely to record every PR. PR/state continuity belongs in the canonical state files.
