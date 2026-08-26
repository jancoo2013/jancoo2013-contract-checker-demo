## Context Gate v1

Replace this block with the exact bounded change contract. Keep exactly one Context Gate JSON block in the PR body.

```json
{
  "context_gate_version": 1,
  "change": "replace-with-kebab-case-change-id",
  "allowed_paths": [
    "replace/with/exact/changed/path",
    "docs/OCR_PROJECT_STATE.md",
    "docs/OCR_PROJECT_STATE.json"
  ]
}
```

## Change Summary

- Changed files:
- Why each file is in scope:
- User/developer impact:

## State Update

- Recorded PR:
- New `state_version`:
- `last_recorded_change`:
- `active_track` effect: unchanged / explicitly changed
- `next_step_id` effect: unchanged / explicitly changed

## Boundaries

- Runtime behavior changed: yes / no
- Data handling changed: yes / no
- Privacy boundary changed: yes / no
- Security invariants changed: yes / no
- Final report persistence changed: yes / no
- State metadata changed: yes / no
- New dependencies: none / describe
- External APIs, network destinations, permissions, or services added: none / describe
- OCR or Gemini image calls added: no / describe
- Raw/unsanitized real contracts, original page images, raw OCR, credentials, secrets, or recoverable PII written to GitHub: no
- Sanitized golden contract text/fixtures added or changed: no / describe explicit scope and privacy review

## Security Review

- Security impact: `NONE` / `LOW` / `HIGH`
- Areas inspected:
  - data flows and trust boundaries;
  - raw/transient material, report storage, retention, deletion, caches, and backups;
  - authentication, authorization, ownership checks, and IDOR/enumeration risk;
  - secrets, tokens, signed URLs, logs, analytics, crash reports, and errors;
  - Israel-only endpoint allowlisting and absence of cross-region fallback;
  - hostile input, parsing, paths, SSRF, resource bounds, retries, concurrency, and cost amplification;
  - redaction irreversibility, privacy validation, dependencies, permissions, and supply chain;
  - cleanup on success, failure, timeout, cancellation, and interruption.
- Findings and disposition:
- Runtime/provider behavior not verified:
- Final verdict: `Security review: PASS` / `Security review: BLOCKING FINDINGS`

## Validation

- Tests or checks run:
- Results:
- Final head SHA covered by validation and security review:
- Remaining limitations:

## Review Policy

- Per-PR Codex review required: no.
- Periodic Codex batch audit: per current repository workflow/state policy or explicit product-owner request.
- Pending batch audit blocks this PR: no, unless a concrete finding or explicit freeze applies.

## Merge

- [ ] State-update commit is present.
- [ ] Final-diff security review is complete.
- [ ] `Security review: PASS` and no blocking finding remains.
- [ ] Ready for review.
- [ ] No auto-merge requested.
