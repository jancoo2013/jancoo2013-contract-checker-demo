# AGENTS.md

## 1. Binding Sources of Truth

Before creating a branch or modifying any file, read the current versions from the PR base branch:

1. `AGENTS.md` — repository working rules.
2. `docs/ARCHITECTURE.md` — product architecture source of truth.
3. `docs/CUSTOM_OCR_PIPELINE.md` — binding privacy/OCR product contract.
4. `docs/OCR_PROJECT_STATE.md` — canonical operational state, blockers, completed changes, and the single permitted next privacy/OCR step.
5. `docs/OCR_PROJECT_STATE.json` — machine-readable identifier mirror for the canonical state document.

Component contracts define exact inputs, outputs, schemas, and limits only for the component being changed.

Do not derive current architecture from chat history, old PRs, branch names, partially implemented code, or one agent's memory. The JSON companion does not replace `docs/OCR_PROJECT_STATE.md`; it makes the active state identifiers machine-readable. If the JSON and Markdown state documents disagree, or any binding documents conflict, stop implementation and report the conflict.

`docs/CODEX_WORKFLOW.md` defines the repository execution protocol for the product owner, orchestrating assistant, and Codex. Read it after the five binding sources. It cannot override product architecture, privacy contracts, or current state. Permanent process documents must not hard-code a supposedly current PR number, branch, `active_track`, or `next_step_id`; those values are read from the current state files on `main` at the start of each task.

## 2. Mandatory PR Context Gate v1

Every PR must publish one exact JSON contract before implementation and copy the same contract into the PR description:

```json
{
  "context_gate_version": 1,
  "change": "stable-kebab-case-change-id",
  "allowed_paths": [
    "exact/path/changed/by/the/pr",
    "docs/OCR_PROJECT_STATE.md",
    "docs/OCR_PROJECT_STATE.json"
  ]
}
```

Rules:

- `change` is a stable lowercase kebab-case identifier and must match `last_recorded_change` in the updated state JSON.
- `allowed_paths` lists every file changed by the PR and no other file.
- Both state files are mandatory in every PR.
- Every declared path must actually change; every changed path must be declared.
- Human-readable PR prose is unrestricted and is not part of the machine contract.
- Do not add a second context-gate JSON block to the PR body.

Implementation may proceed only when one of these is true:

- the task implements the current `next_step_id`; or
- the product owner explicitly authorizes a bounded corrective, security, documentation, or process exception.

An exception does not silently replace the product next step.

Every PR, including documentation-only and process-only PRs, must update `docs/OCR_PROJECT_STATE.md` in the same branch with a concise record of what that PR changes. The JSON companion must also be updated so that `state_version`, `updated_on`, `last_recorded_pr`, and `last_recorded_change` identify the new state snapshot.

Any change to `active_track`, `next_step_id`, blockers, proven evidence, implementation state, or the permitted next step must keep the Markdown and JSON state documents semantically synchronized in the same PR.

If the requested task conflicts with the binding documents, do not mark the PR ready for review.

## 3. Current Product Direction

The active image-processing direction is automatic local PII detection and irreversible redaction before any external transfer.

Target path:

```text
raw phone photo
→ on-device geometric and image preprocessing
→ on-device PII-region detection
→ irreversible local masks
→ local fail-closed privacy validation
→ anonymized image/document
→ approved external full OCR
→ secondary text redaction
→ evidence blocks
→ legal-risk analysis
→ Russian report
```

The mobile privacy component is not required to perform full Hebrew transcription. The project-owned recognizer, CTC, synthetic-data, Gold, and CER work remains paused research unless the product owner explicitly reactivates it and the binding documents are updated in the same PR.

## 4. Privacy and Data Handling

- Raw contract photos, recoverable PII, and unredacted OCR text must not be sent to Gemini, Google Vision, external OCR, LLM services, or any external image/document API.
- Only an anonymized derivative may cross the local privacy boundary.
- Masked pixels must not remain recoverable through alpha channels, hidden layers, overlays, metadata, caches, debug exports, or reversible transformations.
- Do not commit raw contracts, real contract text, real page images, PII values, signatures, bank details, or identifying annotations to GitHub.
- Do not store PII or raw contract material in Airtable.
- Monetary amounts, dates, clause numbers, notice periods, and legally relevant wording are not PII by default.
- Do not require a mask on every page. Preserve legally relevant content whenever it can be separated safely from PII.

## 5. Development Scope

- Implement one bounded, measurable step per branch and PR.
- Make the smallest working change that satisfies the approved task.
- Do not redesign unrelated components or add speculative abstractions.
- Do not add features, dependencies, external APIs, or runtime integrations outside the approved scope.
- Prefer existing project patterns and readable code.
- Target no more than 300 changed implementation lines per PR; treat 400 as the normal hard limit.
- Never accept a worker session's claim that work is complete without inspecting its diff and validation results.
- The orchestrating assistant owns bounded handoff, diff review, test review, and state updates. The product owner is not responsible for transferring project history between sessions.
- Unless explicitly required by the task, do not commit build directories, binaries, APKs, workflow artifacts, local logs, caches, IDE metadata, temporary scripts, temporary workflows, repository-external reports, or lock-file changes when dependencies did not change.

## 6. Product and Legal Boundaries

- This product is a preliminary AI-assisted risk audit and explanation tool, not legal advice or an AI lawyer.
- Do not implement a `safe to sign` verdict.
- Do not state with certainty that a clause is illegal, void, enforceable, or unenforceable.
- Do not predict court outcomes.
- The LLM is not the source of truth. Verified source evidence and deterministic validation are required.
- User-facing explanations default to Russian; exact Hebrew source text is retrieved from stored evidence rather than regenerated by the model.

## 7. Validation

For Python code changes, run when applicable:

```bash
python -m py_compile app.py contract_checker/*.py research/hebrew_contract_ocr/*.py
python -m unittest discover -s tests
```

For mobile reviewer changes, use the repository-owned commands below from the repository root on Windows PowerShell. These wrappers are the canonical Android automation path; do not replace them with Android Studio copy/paste, direct Gradle invocations, or `expo run:android` unless a bounded task explicitly requires a lower-level diagnostic.

```powershell
npm --prefix mobile/pii-reviewer test
.\tools\android-dev.ps1 doctor
.\tools\android-dev.ps1 build
.\tools\android-dev.ps1 run
.\tools\android-dev.ps1 logs
.\tools\android-dev.ps1 restart
```

Use the commands proportionately:

- Run `npm --prefix mobile/pii-reviewer test` for every mobile JavaScript or application-behavior change.
- Run `doctor` before the first Android build in a working session and again after a toolchain, SDK, Java, Node, Gradle, or adb failure.
- Run `build` for every change that can affect the standalone APK. A successful build must end with `BUILD READY` and produce the expected repository-owned artifact.
- Run `run` only when device installation or device behavior is part of the completion criteria and exactly one authorized ready device is available.
- Run `logs` after a runtime failure or unexpected device behavior. Treat its output as local diagnostic material and do not publish raw logs without review.
- Run `restart` only when the installed APK is already current and the task requires another launch without rebuilding or reinstalling it.

When a required validation command fails:

1. Read the command output and the repository-owned local failure log, when one is named.
2. Identify the first actionable root cause before editing.
3. Make the smallest in-scope correction; do not change product code to conceal a broken local environment.
4. Re-run the failed command.
5. After it passes, re-run the focused tests and the final required build or device check so the reported result matches the final diff.
6. Repeat only while the correction remains inside the approved task contract. Stop and report the blocker if the next correction requires a new dependency, subsystem, privacy/product decision, destructive device action, unavailable credential, unavailable authorized device, or broader scope.

Do not make more than two consecutive correction attempts for the same root cause without returning to the product owner. Stop earlier if the failure changes category, the next fix becomes speculative, or scope is no longer clear.

All claimed final tests, builds, installs, launches, logs, and device checks must apply to the same final head SHA presented for review. Record the base SHA, final head SHA, exact commands, results or exit codes, and relevant workflow run identifiers. If code, documentation, or state changes after a passing command, re-run the required final checks.

Do not claim build, installation, launch, log, or device validation unless the corresponding command actually ran successfully. Android Studio may be used for human visual inspection, but it is not the required automation or evidence path.

Documentation-only PRs do not require application tests, but must validate that:

- all referenced files exist;
- machine-readable state metadata is internally consistent with the canonical state document;
- the PR template uses the same Context Gate v1 fields as the validator;
- the current PR is recorded in both state files;
- no product next step changed unintentionally.

## 8. Pull Request Requirements

- Create the PR against `main`.
- Open every PR as a draft first so that its PR number is known.
- Do not auto-merge.
- Include exactly one completed Context Gate v1 JSON block in the PR body.
- Use this order: read current binding sources and state; check overlapping open PRs; publish the Context Gate before edits; branch from current `main`; implement and run focused checks; open a draft PR; update both state files after the PR number exists; run final checks on the final head SHA; inspect declared versus actual paths; then mark Ready.
- After the PR number exists, add a final state-update commit to the same branch:
  - record the PR number, date, bounded change, validation, remaining limitations, and next-step effect in `docs/OCR_PROJECT_STATE.md`;
  - increment `state_version` and set `last_recorded_pr` and `last_recorded_change` in `docs/OCR_PROJECT_STATE.json`;
  - keep `active_track` and `next_step_id` unchanged unless the product owner explicitly changes them.
- Mark the PR ready for review only after the state-update commit is present, both state files agree, required validation applies to the final head SHA, and the final diff contains no undeclared, generated, temporary, binary, or environment-specific files.
- List changed files and explain why each is in scope.
- State whether runtime behavior, data handling, dependencies, external APIs, OCR, Gemini image calls, or state metadata changed.
- Report tests or validation performed and any remaining limitations.
- Codex must not merge the PR or enable auto-merge.

Every 3–5 merged privacy/OCR PRs, run the repository-only cold-start audit defined in `docs/OCR_PROJECT_STATE.md`.

## 9. Orchestration and truthful dispatch

The orchestrating assistant prepares one exact task packet and independently audits the resulting PR. Codex executes inside the repository. Detailed mechanics are defined in `docs/CODEX_WORKFLOW.md`.

Do not say that a task was sent to Codex, that Codex is running, or that Codex completed work unless an actual Codex invocation occurred. When direct invocation is unavailable, provide the complete ready-to-run task packet and state that execution has not started. Do not substitute an improvised GitHub workflow while describing it as Codex.

The independent audit must verify the base, final head SHA, one Context Gate JSON block, actual changed paths, scope, final validation evidence, state agreement, privacy boundary, generated files, and auto-merge state before recommending merge.
