## PR Context Gate

- [ ] I read `AGENTS.md` from the PR base branch.
- [ ] I read `docs/ARCHITECTURE.md` from the PR base branch.
- [ ] I read `docs/CUSTOM_OCR_PIPELINE.md` from the PR base branch.
- [ ] I read `docs/OCR_PROJECT_STATE.md` from the PR base branch.
- [ ] I read `docs/OCR_PROJECT_STATE.json` from the PR base branch.
- [ ] The Markdown and JSON state documents agree.

```text
PR CONTEXT GATE

active_track:
state_version:
next_step_id:
permitted_next_step:
task_scope:
explicitly_out_of_scope:
exception_authorization: none
state_change: none
binding_document_shas:
  AGENTS.md:
  docs/ARCHITECTURE.md:
  docs/CUSTOM_OCR_PIPELINE.md:
  docs/OCR_PROJECT_STATE.md:
  docs/OCR_PROJECT_STATE.json:
```

## Change Summary

- Changed files:
- Why each file is in scope:
- User/developer impact:

## Required State Update

- [ ] `docs/OCR_PROJECT_STATE.md` records this PR number, date, bounded change, validation, remaining limitations, and next-step effect.
- [ ] `docs/OCR_PROJECT_STATE.json` has an incremented `state_version`.
- [ ] `last_recorded_pr` equals this PR number.
- [ ] `last_recorded_change` identifies this bounded change.
- [ ] `active_track` and `next_step_id` remain unchanged unless the product owner explicitly changed them.

```text
state_update:
  recorded_pr:
  new_state_version:
  recorded_change:
  next_step_effect: unchanged | changed with explicit authorization
```

## Boundaries

- Runtime behavior changed: yes / no
- Data handling changed: yes / no
- State metadata changed: yes / no
- New dependencies: none / describe
- External APIs or services added: none / describe
- OCR or Gemini image calls added: no / describe
- Real contracts, page images, contract text, or PII written to GitHub: no

## Validation

- Tests or checks run:
- Results:
- Remaining limitations:

## Merge

- [ ] State-update commit is present.
- [ ] Ready for review.
- [ ] No auto-merge requested.
