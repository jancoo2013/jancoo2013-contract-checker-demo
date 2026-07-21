# Controlled PII Reviewer Validation Pilot v0

Status: binding local pilot contract. It does not authorize external upload or claim privacy safety.

## Purpose

A Hebrew-reading reviewer compares each repository-external source page with its grayscale masked derivative and records only three closed error categories:

- `missed_pii`: PII is visible and no mask covers it;
- `incomplete_mask`: a mask covers only part of the PII region;
- `over_redaction`: a mask hides useful content that is not PII.

The reviewer does not transcribe the contract, enter PII values, add free-text notes, classify legal risk, or call OCR/LLM services.

## Inputs

The pilot consumes a non-empty exact `marker_layout_baseline_v0` prediction JSONL, the immutable source-image root, and a completed `grayscale_opaque_mask_v0` renderer output. Top-level and nested candidate schemas are closed and use strict types. Source and derivative paths must be relative, remain inside their roots, match their SHA-256 values and dimensions, and stay below byte/pixel ceilings. Renderer rows must bind to the exact prediction-manifest SHA-256.

All real pages and reviewer output remain outside the repository. Only synthetic fixtures and empty/example schemas may be committed.

## Review workflow

This PR defines the deterministic core and review-manifest boundary. A separate next PR will add the localhost UI that collects two bbox corners without free-text input. The core validates exact source/prediction/derivative identity and can write only canonical closed-category output.

## Output

The deterministic JSONL contains immutable source/prediction/derivative hashes, dimensions, page status and canonical finding IDs. Findings contain only category and geometry. There are no names, addresses, document text, PII values, reviewer identity, timestamps or free-text fields.

Immediately before publication, the core re-reads and verifies every source and derivative file against the bound hashes, dimensions and derivative mode. Output is staged in a sibling temporary file and installed atomically without overwriting an existing or concurrently created output path. Failure removes the staging file.

## Proof boundary

The pilot provides a bounded, reproducible human-error record for later metrics. It does not itself prove PII recall, complete mask coverage, acceptable over-redaction, external-transfer safety, Android behavior or production privacy safety. Metrics are a separate step after controlled reviewer data exists.
