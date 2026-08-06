# PR Context Gate Canary v1

This document is a deliberately inert canary for the restored GitHub Actions context gate.

## Purpose

The pull request containing this file is successful only when all of the following are true:

1. `PR context gate / validate-context` appears automatically for the exact final head SHA.
2. The automatic run completes with `success`.
3. A manual `workflow_dispatch` run for the same pull request number also completes with `success`.
4. The pull request diff contains only the three paths declared in its Context Gate v1 block.
5. `validate-context` remains non-required until both runs are confirmed.

## Scope

This canary changes documentation and project state only. It does not change application runtime, OCR, Android, image processing, dependencies, provider integration, upload, encryption, PII handling, Gemini calls, credentials, or storage.

## Interpretation

A missing, skipped, cancelled, stale-head, permanently queued, or failed status is a failed canary. A successful canary permits restoring `validate-context` as a required check before the next implementation PR.

Run IDs and exact-head evidence belong in the pull request description or conversation so recording them does not create another head SHA and invalidate the observed run.
