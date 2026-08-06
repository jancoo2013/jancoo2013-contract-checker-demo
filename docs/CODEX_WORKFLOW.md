# Codex Execution and Periodic Audit Protocol

Status: repository protocol for bounded Codex execution and periodic batch audits. This document does not override `AGENTS.md`, `SECURITY.md`, product architecture, privacy/OCR contracts, or the current state files.

## 1. Roles

- The product owner chooses product direction, approves bounded steps, decides whether to merge, and may request an immediate audit.
- The orchestrating assistant reads repository state, defines bounded work, audits each PR, maintains state continuity, and performs the per-PR security review.
- Codex may be used in two separate modes:
  1. **bounded executor** for a specifically assigned implementation task;
  2. **periodic batch auditor** for a range of accumulated merged work.

Codex review is not required after every PR and is not a normal merge prerequisite.

## 2. Binding sources

Before either execution or audit, read current versions from the relevant base or audit endpoint:

1. `AGENTS.md`
2. `SECURITY.md`
3. `docs/ARCHITECTURE.md`
4. `docs/CUSTOM_OCR_PIPELINE.md`
5. `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`
6. `docs/OCR_PROJECT_STATE.md`
7. `docs/OCR_PROJECT_STATE.json`

Conversation history may explain intent but does not replace repository state. Stop and report a conflict when binding documents disagree.

## 3. Mode A — bounded Codex execution

When Codex is explicitly assigned one PR, the task packet must contain:

- repository and base branch;
- actual current `active_track` and `next_step_id`;
- one measurable change;
- exactly one Context Gate v1 object;
- complete allowed paths;
- explicit forbidden changes;
- expected behavior;
- focused tests and final validation;
- failure and blocker policy;
- draft/Ready requirements;
- no-auto-merge instruction.

Avoid broad instructions such as “improve security”, “clean up the subsystem”, or “fix everything you find”.

### 3.1 Execution order

Codex must:

1. read all binding documents from the current base;
2. confirm state agreement and check overlapping open PRs;
3. publish the Context Gate before modifying files;
4. create a branch from the current `main` head;
5. implement only the bounded change;
6. run focused checks;
7. open the PR as draft;
8. update both state files after the PR number exists;
9. re-run final checks after the last change;
10. verify declared and actual paths match exactly;
11. record exact validation evidence and remaining limitations;
12. leave merge and auto-merge disabled.

When Codex implements the PR, its final implementation report is not an additional independent Codex review gate. The orchestrating assistant still performs the normal per-PR audit and security verdict.

### 3.2 Final-SHA evidence

Report:

- base SHA;
- final head SHA;
- exact commands and results;
- workflow/job identifiers when used;
- which build, install, launch, device, log, provider, deletion, retention, region, or authorization checks actually ran;
- all runtime/provider behavior that remains unverified.

Claims from an earlier commit are stale after code, documentation, state, dependency, configuration, or workflow changes.

### 3.3 Bounded failure loop

On a required-command failure:

1. inspect output and repository-owned diagnostics;
2. identify the first actionable root cause;
3. make the smallest in-scope correction;
4. rerun the failed command;
5. rerun final focused validation after it passes.

Make no more than two consecutive correction attempts for the same root cause without returning to the product owner. Stop earlier when the category changes, the fix becomes speculative, or scope expands.

Stop and report a blocker when continuation requires:

- a new dependency or subsystem;
- a product, architecture, privacy, or security decision;
- unavailable credentials, device, GPU, or approved region;
- a destructive device action;
- a larger allowed-path list;
- real contracts or recoverable PII sent to an external service;
- weakening an Israel-only, deletion, authorization, redaction, secret-handling, or fail-closed invariant.

## 4. Mode B — periodic Codex batch audit

The default review policy is a batch audit of accumulated merged work approximately twice per week, not a review after every PR.

A periodic audit should cover the commit or PR range since the last completed audit. When no prior audit marker exists, choose a bounded recent range and record its start and end SHAs.

### 4.1 Audit goals

Inspect for defects that are easier to detect across several PRs than within one diff:

- cross-PR integration errors and contract drift;
- inconsistent state or binding documents;
- security/privacy regressions;
- raw data, PII, credential, log, analytics, or artifact exposure;
- Israel-only endpoint or fallback violations;
- authorization/IDOR risks in stored reports;
- incomplete cleanup, retention, deletion, or backup behavior;
- stale or missing tests;
- unsupported runtime/provider claims;
- resource, retry, concurrency, GPU-cost, and denial-of-service risks;
- dependency, permission, workflow, and supply-chain changes;
- scope creep, dead code, duplicated logic, and contradictory component contracts.

### 4.2 Audit output

The audit must report:

- start SHA and end SHA;
- included PRs or commits;
- binding state read at the end SHA;
- checks and tests actually run;
- findings grouped as blocking, corrective, or observation;
- what remains unverified;
- whether an immediate product freeze is warranted;
- bounded corrective PR recommendations.

Use these outcomes:

1. `BATCH AUDIT CLEAR` — no blocking defect found in the inspected range.
2. `CORRECTIVE PR REQUIRED` — one or more bounded fixes are needed, but ordinary unrelated work may continue.
3. `FREEZE AFFECTED AREA` — a serious security, privacy, architecture, or data-integrity issue requires pausing the affected subsystem pending owner decision or correction.

A pending periodic audit does not block ordinary PR merges. Only an explicit product-owner freeze or a concrete blocking finding affecting the current PR changes that.

### 4.3 Audit continuity

Record the last completed audit range and date in the canonical project state or the dedicated audit record selected by the product owner. The next audit begins after that end SHA so ranges do not silently overlap or leave gaps.

The “approximately twice per week” target is an operating cadence, not an automated merge condition. Missing the target does not invalidate already merged PRs.

## 5. Per-PR audit remains with the orchestrating assistant

For each individual PR, the orchestrating assistant checks:

- base and final head SHA;
- exactly one Context Gate JSON block;
- declared versus actual paths;
- bounded scope;
- final validation evidence;
- state agreement;
- privacy and security invariants;
- credentials, raw data, generated files, and provider artifacts;
- auto-merge state;
- the mandatory security verdict required by `SECURITY.md`.

Possible per-PR outcomes:

1. `MERGEABLE`
2. `CORRECTIVE REQUIRED IN THIS PR`
3. `BLOCKED PENDING PRODUCT DECISION`

This per-PR audit does not require a separate Codex review.

## 6. Repository hygiene

Unless explicitly required, do not commit:

- build directories, generated binaries, APKs, or workflow artifacts;
- local logs, diagnostic dumps, caches, or IDE metadata;
- temporary scripts or workflows;
- lock-file changes without a dependency change;
- credentials, tokens, signed URLs, endpoint IDs, real job payloads, raw OCR, page images, or recoverable PII.

Do not introduce opportunistic refactors, speculative abstractions, adjacent features, or “future-proofing” outside the approved task or audit correction.

## 7. Truthful Codex dispatch

Do not claim that Codex was invoked, is running, completed a task, or completed an audit unless an actual invocation occurred.

When direct invocation is unavailable, provide a ready-to-run task or audit packet and state that execution has not started. Do not label an improvised GitHub action as Codex work.

## 8. Android and serverless evidence

For Android work, distinguish static review, JavaScript tests, environment validation, APK build, installation, launch, runtime smoke, logs, and security behavior. One does not prove another.

For serverless work, distinguish static configuration review from actual evidence of region, retention, deletion, cleanup, authentication, authorization, resource limits, and provider behavior.

## 9. PR size and scope

Target no more than 300 changed implementation lines per PR and treat 400 as the normal hard limit. Documentation does not justify an oversized implementation.

A bounded Codex task must not bundle multiple sequential PRs. A periodic audit may inspect multiple PRs but must propose corrections as separate bounded PRs.
