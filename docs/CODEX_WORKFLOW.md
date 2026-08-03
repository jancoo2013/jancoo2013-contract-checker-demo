# Codex Orchestration Protocol

Status: repository execution protocol. This document defines how the product owner, orchestrating assistant, and Codex divide work. It does not override `AGENTS.md`, product architecture, privacy/OCR contracts, or the current state files.

## 1. Roles

- The product owner chooses product direction, approves bounded steps, and decides whether to merge.
- The orchestrating assistant reads the repository state, proposes one bounded step, writes the exact Codex task, and independently audits the resulting PR.
- Codex is the repository executor. It reads the repository, creates the branch, changes files, runs available checks, fixes in-scope failures, opens the PR, and never merges it.

Do not transfer implementation code manually between ChatGPT, Android Studio, and GitHub. Android Studio may be used only for visual inspection or a separately justified low-level diagnostic.

## 2. Current state is never hard-coded here

Permanent process documents must not name a supposedly current PR number, branch, `active_track`, or `next_step_id` as operational truth.

At the start of every task, read the current values from the actual `main` branch:

1. `AGENTS.md`
2. `docs/ARCHITECTURE.md`
3. `docs/CUSTOM_OCR_PIPELINE.md`
4. `docs/OCR_PROJECT_STATE.md`
5. `docs/OCR_PROJECT_STATE.json`

Conversation history may explain product-owner intent, but it does not replace repository state. If the binding documents disagree, stop before implementation and propose a separate consistency fix.

## 3. One task packet per PR

Before Codex starts implementation, the orchestrating assistant prepares one bounded task packet containing:

- repository and base branch;
- the five binding sources;
- the actual current `active_track` and `next_step_id` read from `main`;
- one measurable change;
- exactly one Context Gate v1 JSON object;
- the complete list of allowed paths;
- explicit forbidden changes;
- expected behavior;
- focused tests and final validation;
- failure and blocker policy;
- draft/Ready requirements;
- a no-auto-merge instruction.

Avoid broad instructions such as “improve the detector”, “clean up the code”, or “fix anything you find”. One PR implements one measurable step.

## 4. Required execution order

Codex must use this sequence:

1. Read all five binding documents from the current base branch.
2. Confirm that Markdown and JSON state agree.
3. Check for an overlapping open PR.
4. Publish the Context Gate v1 in its initial task report before changing files.
5. Create a new branch from the current `main` head.
6. Implement only the bounded change and run focused checks.
7. Open the PR against `main` as a draft, copying the same single Context Gate JSON block into the PR body.
8. After the PR number exists, update both state files in the same branch.
9. Re-run all required final checks after the last code, documentation, and state change.
10. Inspect the final diff and verify that actual changed paths exactly match `allowed_paths`.
11. Record final validation evidence and remaining limitations in the PR body.
12. Mark the PR ready for review.
13. Do not merge and do not enable auto-merge.

The Context Gate may be published before a PR exists, but the PR body must contain the same object and exactly one Context Gate JSON block.

## 5. Final-SHA evidence

A passing command from an earlier commit is not final proof.

Before Ready, Codex must report:

- base SHA;
- final head SHA;
- exact commands run;
- command results or exit codes;
- relevant workflow run identifiers when CI was used;
- whether build, install, launch, logs, or device smoke actually ran.

All claimed final tests, builds, and device checks must apply to the same final head SHA that is presented for review. If state or code changes after a passing test, the required final checks must run again.

Never claim build, install, launch, device smoke, log inspection, or external-service behavior from static review alone.

## 6. Bounded failure loop

When a required command fails, Codex should not stop at the first obvious in-scope error. It must:

1. Read the command output and any repository-owned failure log.
2. Identify the first actionable root cause.
3. Make the smallest correction allowed by the Context Gate.
4. Re-run the failed command.
5. After it passes, re-run focused tests and the final required validation on the resulting diff.

Codex may make at most two consecutive correction attempts for the same root cause without returning to the product owner. Stop earlier if the failure changes category, the proposed correction becomes speculative, or the task boundary is no longer clear.

Codex must stop and report a blocker when continuation requires:

- a new dependency;
- a different subsystem;
- an architecture or product decision;
- a privacy-boundary change;
- unavailable credentials;
- an unavailable authorized device;
- a destructive device action;
- a larger allowed-path list;
- sending real contracts or recoverable PII to an external service.

Environment failures in Java, Android SDK, Node, Gradle, adb, credentials, or device authorization must not be hidden by changing product code.

## 7. Repository hygiene

Unless explicitly required by the approved task, do not commit:

- build directories or generated binaries;
- APK files or workflow artifacts;
- local logs or diagnostic dumps;
- caches, IDE metadata, temporary scripts, or temporary workflows;
- repository-external review packs or reports;
- lock-file changes when dependencies did not change.

Before Ready, inspect the diff specifically for generated, temporary, binary, environment-specific, and undeclared files.

Do not introduce speculative abstractions, opportunistic refactors, adjacent features, or “future-proofing” outside the measurable change.

## 8. Android execution

For mobile work, use the repository-owned Windows PowerShell commands defined in `AGENTS.md` from the repository root. Apply `test`, `doctor`, `build`, `run`, `logs`, and `restart` only under their documented conditions.

The final Android evidence must distinguish:

- static code review;
- JavaScript tests;
- environment validation;
- standalone APK build;
- device installation;
- application launch;
- runtime smoke;
- log inspection.

One does not prove another.

## 9. Truthful Codex dispatch

The orchestrating assistant must not say that a task was sent to Codex, that Codex is running, or that Codex completed work unless an actual Codex invocation occurred.

When direct Codex invocation is unavailable, provide the complete ready-to-run task packet and state that execution has not started. Do not substitute an improvised GitHub workflow while describing it as Codex.

## 10. Independent PR audit

The orchestrating assistant must inspect GitHub independently rather than accept the Codex summary as proof. The audit checks:

- the PR base and base SHA;
- the final head SHA;
- exactly one Context Gate JSON block;
- declared versus actual changed paths;
- implementation scope and hidden architecture expansion;
- focused and final test evidence;
- whether final checks ran after the last change;
- build/install/device claims;
- Markdown/JSON state agreement;
- unauthorized changes to `active_track` or `next_step_id`;
- privacy-boundary compliance;
- generated or temporary files;
- auto-merge state.

The audit verdict must state:

- what changed;
- what is actually proved;
- what remains unverified;
- any findings;
- whether the PR can be merged.

Use one of these outcomes:

1. `MERGEABLE` — no blocking finding remains.
2. `CORRECTIVE REQUIRED IN THIS PR` — the fix is bounded and does not require a new product decision.
3. `BLOCKED PENDING PRODUCT DECISION` — continuing would expand scope or change architecture, dependencies, privacy, or product direction.

Do not recommend merge when there is a blocking defect, state inconsistency, undeclared file, stale validation, unsupported claim, or enabled auto-merge.

## 11. PR size and scope

Target no more than 300 changed implementation lines. Treat 400 implementation lines as the normal hard limit. Documentation and state are assessed separately for reasonableness but do not justify an oversized implementation.

One Codex task must not bundle multiple sequential PRs. The next step is selected only after the current PR is merged and the new `main` state is read again.
