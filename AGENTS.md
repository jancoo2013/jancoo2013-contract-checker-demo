# AGENTS.md

## 1. Repository context hierarchy

Before creating a branch or modifying any file, read the current versions from the PR base branch in this order:

1. `AGENTS.md` — repository working rules.
2. `SECURITY.md` — binding security invariants and mandatory final-diff security review.
3. `docs/ARCHITECTURE.md` — product architecture source of truth.
4. `docs/CUSTOM_OCR_PIPELINE.md` — binding privacy/OCR product contract.
5. `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md` — frozen/deferred remote-processing architecture unless canonical state explicitly reopens it.
6. `docs/OCR_PROJECT_STATE.md` — canonical operational state, blockers, and the single permitted next step.
7. `docs/OCR_PROJECT_STATE.json` — machine-readable mirror of the canonical state identifiers.
8. `docs/DOCUMENT_STATUS_INDEX.md` — classification of current, task-specific, frozen, historical, and component-only documents.
9. `docs/CODEX_WORKFLOW.md` — execution/audit protocol for Codex and the orchestrating assistant.

The state files alone select the current `active_track` and `next_step_id`. Permanent process documents must not be treated as evidence of a current PR number, branch, active track, or next step merely because they contain historical examples.

If `docs/OCR_PROJECT_STATE.md` and `docs/OCR_PROJECT_STATE.json` disagree, or any binding documents conflict on a rule that affects the requested task, stop implementation and report the conflict.

After the binding sources are consistent, read only the task-specific documents named by the canonical state, `docs/DOCUMENT_STATUS_INDEX.md`, or the approved task packet. Historical/frozen/component documents do not become current direction merely because they exist in the repository.

Conversation history, old PRs, branch names, partially implemented code, README prose, and agent memory are not substitutes for current repository state.

## 2. Mandatory PR Context Gate v1

Every PR must contain exactly one Context Gate v1 JSON object in its PR body:

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

- `change` is lowercase kebab-case and must match `last_recorded_change` in state JSON.
- `allowed_paths` lists every changed file and no unchanged file.
- Both state files are mandatory in every PR.
- Every declared path must actually change; every changed path must be declared.
- Do not add a second Context Gate JSON block to the PR body.
- Implementation may proceed only when the task implements the current `next_step_id`, or the product owner explicitly authorizes a bounded corrective/security/documentation/architecture/process exception.
- An exception does not silently replace the canonical next step.

Every PR updates both state files after the PR number exists. Any change to active track, next step, blockers, evidence, privacy boundary, security invariants, or permitted scope must keep Markdown and JSON state semantically synchronized.

## 3. Current-direction rule

Do not hard-code or infer the current product direction here. Read it from the canonical state at task start.

When the active track is Question Engine development, task-specific context normally includes, as applicable:

- `docs/QUESTION_ENGINE_DISCOVERY_LOG.md` — current product/analysis design decisions;
- `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md` — maintained statutory engineering map;
- `docs/statutory/README.md` and versioned statutory snapshots when the task touches statutory comparison;
- `research/question_engine/golden_contracts/` fixtures when the task touches inventory/schema/evidence behavior.

These task-specific documents do not override binding privacy/security/architecture/state documents.

Question Engine must remain OCR-provider-independent. OCR, Android preprocessing, Surya/serverless work, old Streamlit UX, mobile transport experiments, and recognizer research remain outside a Question Engine PR unless the canonical state or product owner explicitly reopens them.

## 4. Question Engine data and product invariants

For Question Engine and golden-fixture work:

- raw real contract photos, raw OCR, and recoverable PII must not enter GitHub or CI;
- persisted fixtures must be sanitized before commit;
- handwriting must not be semantically reconstructed, transcribed, or guessed; if a result depends on handwriting, return an explicit unresolved dependency;
- preserve the party-role granularity actually used by operative contract text; do not invent numbered parties only because several names appear in a header;
- monetary amounts, dates, clause numbers, notice periods, and legally relevant printed wording are not PII by default when safely separable from identifiers;
- different security instruments must remain semantically distinct;
- contract facts, statutory rules, and product explanation remain separate evidence layers;
- a candidate finding may need a second pass and may be confirmed, narrowed, or cleared after related clauses/definitions/statutory checks are resolved;
- verified source evidence is the source of truth; the LLM is a semantic reader, not the authority.

### User-facing boundary

The product is an AI-assisted contract explanation and preparation tool. It must not:

- produce a `safe to sign` verdict;
- tell the user to sign or not sign;
- tell the user to sue, refuse payment, or ignore an obligation;
- predict who will win a dispute;
- present a model-generated replacement clause as the uniquely correct final wording;
- state with certainty that a clause is illegal, void, enforceable, or unenforceable unless a separately approved deterministic rule explicitly supports that exact bounded statement.

Current Question Engine Russian UX rules live in `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`. In production Russian copy, avoid words built from `юрист-` / `юрид-`; internal English `LEGAL_*` engineering identifiers may remain internal.

Exact Hebrew **source evidence** must come from sanitized source material or deterministic sanitized evidence references, never from an LLM-generated quotation. Optional Hebrew **discussion wording** is a separate remediation output and may be generated only under the provenance/gating rules defined for that subsystem; it must never be mislabeled as source evidence.

## 5. Privacy and data handling

- Restricted raw material may leave the device only through an explicitly approved processing path after that path is formally reopened and required consent/security controls exist.
- Original images, raw OCR, recoverable PII, signatures, bank/account/check identifiers, job keys, secrets, and other restricted material must not enter GitHub, CI, Airtable, general logs, analytics, crash reports, support artifacts, or downstream LLM prompts.
- Only privacy-validated sanitized derivatives may proceed to downstream analysis models.
- Masked pixels must not remain recoverable through alpha channels, hidden layers, overlays, metadata, caches, alternate frames, or reversible transformations.
- Encryption protects transport/storage, not computation; an authorized remote worker may decrypt in memory. Do not describe such processing as local or zero-access.
- Any future raw remote processing must preserve the binding Israel-only, deletion, logging, fail-closed, and no-cross-region-fallback rules in `SECURITY.md`.
- Do not store raw contract material or PII in Airtable.
- Final reports may be persisted only under the sanitized-report contract in `SECURITY.md`.

## 6. Development scope

- Implement one bounded measurable step per branch and PR.
- Make the smallest working change that satisfies the approved task.
- Do not redesign unrelated components or add speculative abstractions.
- Do not add dependencies, external APIs, permissions, workflows, providers, storage, or runtime integrations outside scope.
- Prefer existing project patterns and readable code.
- Target no more than 300 changed implementation lines per PR; treat 400 as the normal hard limit.
- Do not commit build directories, binaries, APKs, model weights, workflow artifacts, local logs, caches, IDE metadata, temporary scripts/workflows, or lock-file changes without a dependency change unless explicitly required.
- Never accept an executor's claim of completion without inspecting the actual final diff and validation evidence.

## 7. Validation

Use validation proportionately to the changed component.

For Python changes when applicable:

```bash
python -m py_compile app.py contract_checker/*.py research/hebrew_contract_ocr/*.py
python -m unittest discover -s tests
```

For the repository-owned Android reviewer path when applicable:

```powershell
npm --prefix mobile/pii-reviewer test
.\tools\android-dev.ps1 doctor
.\tools\android-dev.ps1 build
.\tools\android-dev.ps1 run
.\tools\android-dev.ps1 logs
.\tools\android-dev.ps1 restart
```

Do not substitute Android Studio/manual steps for required repository automation unless a bounded diagnostic explicitly requires it.

For serverless work, report only evidence that actually ran, including relevant provider/region/resource/latency/log/cleanup facts. Configuration review is not runtime proof.

When a required command fails:

1. inspect the output and repository-owned diagnostics;
2. identify the first actionable root cause before editing;
3. make the smallest in-scope correction;
4. rerun the failed command;
5. rerun final focused validation after it passes;
6. stop when continuation requires broader scope, a new dependency/subsystem, unavailable credential/device/GPU/approved region, destructive action, or a new product/privacy/security decision.

Do not make more than two consecutive correction attempts for the same root cause without returning to the product owner. Stop earlier if failure category changes or the next fix becomes speculative.

All final validation claims must apply to the same final head SHA presented for review. If code, docs, state, dependencies, configuration, fixtures, or workflow changes after a passing command, rerun the required final checks.

Documentation-only PRs do not require application tests, but must validate referenced files, state JSON syntax/semantic agreement, declared versus actual paths, absence of restricted material/credentials/generated artifacts, and final security metadata.

## 8. Pull request lifecycle

- Create the PR against `main`.
- Open every PR as a draft first so its number is known.
- Do not auto-merge.
- Read current binding/state documents and check overlapping open PRs before branching.
- Publish the Context Gate before edits.
- Branch from current `main`.
- Implement only the bounded task and run focused checks.
- Open the draft PR.
- Update both state files after the PR number exists.
- Rerun final checks on the final head SHA.
- Compare declared and actual changed paths exactly.
- Perform the mandatory final-diff security review.
- Mark Ready only after state agreement, final validation, and `Security review: PASS`.
- Leave merge decision to the product owner.

The PR body must state changed files/scope, state effect, runtime/data/privacy/security impact, dependencies/network/API changes, validation, limitations, and exactly one final security verdict required by `SECURITY.md`.

Codex must not merge a PR or enable auto-merge when acting as executor or reviewer.

## 9. Codex execution and audit

`docs/CODEX_WORKFLOW.md` defines detailed mechanics.

When Codex is used as a bounded executor, the task packet must include the repository/base, current state identifiers, one measurable change, exactly one Context Gate, allowed paths, explicit forbidden changes, expected behavior, focused/final validation, blocker policy, draft/Ready requirements, and no-auto-merge instruction.

Do not say that Codex was invoked, is running, or completed work unless an actual Codex invocation occurred. If direct invocation is unavailable, provide a ready-to-run packet and say execution has not started.

The orchestrating assistant independently audits each resulting PR: base/final head, Context Gate, actual paths, scope, final validation, state agreement, privacy/security invariants, generated files, credentials/provider artifacts, and auto-merge state.

Codex review is not a normal per-PR merge prerequisite. Periodic batch audits may be requested by the product owner or run at the cadence recorded in the current state/workflow policy. A pending batch audit does not block unrelated work unless a concrete blocking finding or explicit freeze applies.

## 10. Mandatory security review

`SECURITY.md` is binding for every PR, including docs/test/state-only changes.

Before Ready, the exact final diff must be reviewed and the PR body must include:

- `Security impact: NONE`, `LOW`, or `HIGH`;
- exactly one verdict: `Security review: PASS` or `Security review: BLOCKING FINDINGS`;
- inspected areas;
- findings and disposition;
- runtime/provider behavior that remains unverified.

Any blocking condition in `SECURITY.md`, or any unresolved conflict among binding/state documents, prevents Ready and a merge recommendation.
