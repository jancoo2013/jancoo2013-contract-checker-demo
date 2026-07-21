# AGENTS.md

## 1. Read This First

- Before making changes, read `docs/ARCHITECTURE.md`.
- Treat `docs/ARCHITECTURE.md` as the product architecture source of truth.
- For privacy/OCR work, also read `docs/OCR_PROJECT_STATE.md` and `docs/CUSTOM_OCR_PIPELINE.md`.
- Treat `docs/OCR_PROJECT_STATE.md` as the operational source of truth for what is implemented, what is proven, the current blockers, and the single permitted next privacy/OCR step.
- Treat the privacy/OCR decisions and milestone order in `docs/CUSTOM_OCR_PIPELINE.md` as binding.
- If a requested task conflicts with `docs/ARCHITECTURE.md`, do not silently override it. Explain the conflict in the PR summary or ask for clarification.
- Do not treat older PR behavior as canonical if it conflicts with the current architecture document.

## 2. Development Style

- Make the smallest working change that satisfies the requested product step.
- Do not redesign unrelated code.
- Do not rewrite working flows unless the task explicitly asks for it.
- Do not remove working UX without explicit instruction.
- Prefer simple, readable Python.
- Prefer existing project patterns.
- Keep PRs reviewable.
- Avoid speculative abstractions.
- Avoid adding features that were not requested.
- Add dependencies only when clearly needed for the requested task.
- If adding a dependency, explain why the standard library or existing dependencies are insufficient.
- Refactor only when it directly supports the requested task or fixes a concrete bug.
- Target no more than 300 changed implementation lines per PR and treat 400 as the normal
  hard limit. Tests and documentation must remain proportional. If a larger PR is genuinely
  unavoidable, its handoff must include a second, independent diff and test review before merge.

## 3. Privacy and Data Handling

Raw contract photos, documents, or text containing PII must not be sent to Gemini, Google Vision, external OCR, or any external image/document API unless the task explicitly implements a privacy-approved anonymized pipeline.

Target privacy direction:

```text
raw image/document
→ local/browser/mobile PII masking
→ anonymized image/document
→ OCR
→ secondary text redaction
→ LLM audit
```

Preserve this architecture.

Do not add external OCR, Google Vision, Gemini image calls, cloud image processing, or raw image upload to an external service unless the task explicitly asks for that stage and the implementation respects the anonymization model in `docs/ARCHITECTURE.md`.

Do not require a mask on every uploaded page. Many middle pages of a lease may contain no personal data. Future privacy logic should detect likely personal-data rows by Hebrew field labels, layout, and known PII markers, while preserving monetary amounts and legal-risk text.

Airtable is a project knowledge base/admin table only. Do not store raw contracts, raw OCR text with PII, photos, names, IDs, addresses, phone numbers, emails, signatures, bank details, check numbers, or other identifying values in Airtable.

## 4. LLM Audit Architecture

- The LLM must not be treated as the source of truth.
- The uploaded contract text/images after preprocessing are the source of truth.
- Do not rely on LLM-generated exact Hebrew quotes.
- Future audit flow should use numbered evidence blocks and `evidence_block_ids`.
- Python should retrieve exact source text from evidence blocks if needed.
- User-facing reports should default to Russian explanations.
- Hebrew originals should be hidden by default and shown only on demand.
- The LLM extracts structured findings; Python validates schema, evidence, completeness, and final card aggregation.

## 5. Current Product Report Model

The target report model is:

1. Global completeness status.
2. Three traffic-light risk cards.
3. Optional detailed mode called `Разбор по пунктам`.

The three cards are:

- Money;
- Terms and eviction;
- Obligations.

Card statuses:

- Red;
- Yellow;
- Green;
- Incomplete.

Green must not mean that the contract is safe or that the user can sign. It means only that no obvious critical risk was found in that domain in the uploaded/analyzed materials.

Do not implement wording that tells the user whether to sign.

## 6. Image Redaction UX

Preserve the current test image redaction UX unless explicitly asked to change it.

Current expected behavior:

- upload image pages;
- press `Подготовить страницы к маскированию`;
- one main working image is shown;
- click-to-redact-row is the primary flow;
- full-width row mask is created from the clicked Y-coordinate;
- row height slider is available;
- `←` undoes the last mask on the current page;
- `Отменить изменения` resets masks on the current page;
- original image is hidden under `Показать оригинал`;
- manual Y-coordinate fallback remains available.

Do not revert this to numeric-only rectangle input unless explicitly requested.

The current manual image-redaction flow is a technical test. It is not the final automatic privacy layer.

## 7. Legal/Product Boundaries

- This product is not legal advice and does not replace a lawyer.
- It is a guided risk-audit and explanation tool.
- Do not implement an AI-lawyer positioning.
- Do not implement a `safe to sign` verdict.
- Do not say that a clause is illegal, void, enforceable, or unenforceable with certainty.
- Do not predict court outcomes.
- Do not implement a conflict-consultant mode unless explicitly requested.
- If conflict-consultant mode is ever added, it must avoid predicting who will win and focus on facts, missing evidence, weak points, documents to request, and when to contact a lawyer.

Use cautious wording such as:

- may create increased risk;
- appears to place broad responsibility on the tenant;
- worth clarifying before signing;
- consider discussing this with the landlord, agent, or a licensed lawyer.

## 8. Current Priority Order

The user has explicitly made automatic local PII detection and irreversible redaction the active image-processing track. Follow `docs/CUSTOM_OCR_PIPELINE.md` and the single next step in `docs/OCR_PROJECT_STATE.md`.

The MVP does not require a project-owned full Hebrew OCR recognizer. After the local privacy boundary has been passed, an approved external OCR/LLM service may receive only the anonymized image/document. Raw photos and recoverable PII must never cross that boundary.

The existing project-owned recognizer, CTC, synthetic-data, Gold, and CER work is preserved as paused research. Do not add a CRNN, training loop, weights, predictions, reviewer APK, or full-line transcription workflow unless the product owner explicitly reactivates that track and updates the binding documents in the same PR.

For work outside the active privacy track, prefer this order unless the user explicitly changes priority:

1. Structured text audit.
2. Evidence blocks.
3. Python validation.
4. Completeness audit.
5. Three-card report + `Разбор по пунктам`.
6. Privacy-safe anonymized image/OCR handoff.

Production integration with raw user photos must not outrun the privacy architecture. Offline research may continue only on synthetic, redacted, or locally controlled data and must not be presented as MVP-critical work.

Do not add runtime Airtable API integration before local JSON/YAML risk configuration is stable.

## 8.1 Privacy/OCR Continuity Protocol

- The repository, not a chat transcript or one agent's memory, is the durable project context.
- The product owner is not responsible for opening Codex work sessions or repeating project history to them. The orchestrating assistant owns session creation, bounded handoff, diff review, test review, and state updates.
- Give each Codex session exactly one bounded step with explicit input, output, allowed scope, prohibited detours, and validation.
- Only the single next step recorded in `docs/OCR_PROJECT_STATE.md` may be active. Changing it requires an explicit product decision and a state update in the same PR.
- Every privacy/OCR PR that changes implementation status, evidence, blockers, or the next step must update `docs/OCR_PROJECT_STATE.md`.
- Every 3–5 merged privacy/OCR PRs, run the cold-start audit defined in `docs/OCR_PROJECT_STATE.md` using a clean session that has only the repository as context.
- Never accept a session's claim that work is complete without inspecting its diff and validation results.

## 9. Tests and Validation

For code changes, run when practical:

```bash
python -m py_compile app.py contract_checker/*.py
python -m unittest discover -s tests
```

If the environment lacks `python` on PATH, use the available Python interpreter and report what was used.

For documentation-only changes, tests are not required, but the PR summary should say that the change is documentation-only.

## 10. Pull Request Behavior

- Create a Pull Request to `main`.
- Open privacy/OCR Pull Requests ready for review, not as drafts, unless the user explicitly requests a draft.
- In the PR summary, list changed files.
- State whether the change is code or documentation only.
- State whether tests were run.
- State explicitly if no external APIs, OCR, Gemini image calls, or new dependencies were added.
- Do not give the user local git commands instead of creating a PR.
