# AGENTS.md

## 1. Binding Sources of Truth

Before creating a branch or modifying any file, read the current versions from the PR base branch:

1. `AGENTS.md` — repository working rules.
2. `docs/ARCHITECTURE.md` — product architecture source of truth.
3. `docs/CUSTOM_OCR_PIPELINE.md` — binding privacy/OCR product contract.
4. `docs/OCR_PROJECT_STATE.md` — operational state, blockers, and the single permitted next privacy/OCR step.

Component contracts define exact inputs, outputs, schemas, and limits only for the component being changed.

Do not derive current architecture from chat history, old PRs, branch names, partially implemented code, or one agent's memory. If binding documents conflict, stop implementation, describe the conflict, and fix the documents in a separate small PR or under explicit product-owner authorization.

## 2. Mandatory PR Context Gate v0

Every PR must pass a context gate before branch creation or file modification.

The working session must publish this block before implementation and copy the same information into the PR description:

```text
PR CONTEXT GATE

active_track: <value from docs/OCR_PROJECT_STATE.md>
state_version: <value from docs/OCR_PROJECT_STATE.md>
next_step_id: <value from docs/OCR_PROJECT_STATE.md>
permitted_next_step: <exact concise description>
task_scope: <one bounded change>
explicitly_out_of_scope: <prohibited detours>
exception_authorization: none | <explicit product-owner decision>
state_change: none | <what state metadata or next step changes>
binding_document_shas:
  AGENTS.md: <blob SHA>
  docs/ARCHITECTURE.md: <blob SHA>
  docs/CUSTOM_OCR_PIPELINE.md: <blob SHA>
  docs/OCR_PROJECT_STATE.md: <blob SHA>
```

Implementation may proceed only when one of these is true:

- the task implements the current `next_step_id`; or
- the product owner explicitly authorizes a bounded corrective, security, documentation, or process exception.

An exception does not silently replace the product next step. Any change to `active_track`, `state_version`, `next_step_id`, blockers, proven evidence, or implementation state must update `docs/OCR_PROJECT_STATE.md` in the same PR.

If a required field is missing, a SHA cannot be tied to the base branch, or the requested task conflicts with the binding documents, do not create implementation changes.

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

For mobile reviewer changes, run the relevant commands from `mobile/pii-reviewer`, including tests and build/smoke checks required by the component contract.

Documentation-only PRs do not require application tests, but must validate that:

- all referenced files exist;
- machine-readable state metadata is internally consistent;
- the PR template uses the same field names as the context gate;
- no product next step changed unintentionally.

## 8. Pull Request Requirements

- Create the PR against `main`.
- Open privacy/OCR PRs ready for review unless the product owner explicitly requests a draft.
- Do not auto-merge.
- Include the completed Context Gate in the PR body.
- List changed files and explain why each is in scope.
- State whether runtime behavior, data handling, dependencies, external APIs, OCR, Gemini image calls, or state metadata changed.
- Report tests or validation performed and any remaining limitations.
- Keep `docs/OCR_PROJECT_STATE.md` synchronized whenever implementation status, evidence, blockers, active track, or the permitted next step changes.

Every 3–5 merged privacy/OCR PRs, run the repository-only cold-start audit defined in `docs/OCR_PROJECT_STATE.md`.
