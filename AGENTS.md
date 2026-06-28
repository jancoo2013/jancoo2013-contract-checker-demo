# AGENTS.md

## 1. Read This First

- Before making changes, read `docs/ARCHITECTURE.md`.
- Treat `docs/ARCHITECTURE.md` as the product architecture source of truth.
- If a requested task conflicts with `docs/ARCHITECTURE.md`, do not silently override it. Explain the conflict in the PR summary or ask for clarification.

## 2. Development Style

- Make the smallest working change that satisfies the task.
- Do not redesign unrelated code.
- Do not rewrite working flows unless the task explicitly asks for it.
- Do not remove working UX without explicit instruction.
- Prefer simple, readable Python.
- Prefer existing project patterns.
- Keep PRs small and reviewable.
- Avoid speculative abstractions.
- Avoid adding features that were not requested.
- Add dependencies only when clearly needed for the requested task.
- If adding a dependency, explain why the standard library or existing dependencies are insufficient.
- Refactor only when it directly supports the requested task or fixes a concrete bug.

## 3. Privacy and Data Handling

Raw contract photos or documents containing PII must not be sent to Gemini, Google Vision, external OCR, or any external image/document API unless the task explicitly implements a privacy-approved anonymized pipeline.

Current privacy direction:

```text
raw image/document
→ local/browser/mobile masking
→ anonymized image/document
→ OCR
→ secondary text redaction
→ LLM audit
```

Preserve this architecture.

Do not add external OCR, Google Vision, Gemini image calls, cloud image processing, or raw image upload to an external service unless the task explicitly asks for that stage and the implementation respects the anonymization model in `docs/ARCHITECTURE.md`.

## 4. LLM Audit Architecture

- The LLM must not be treated as the source of truth.
- The uploaded contract text/images after preprocessing are the source of truth.
- Do not rely on LLM-generated exact Hebrew quotes.
- Future audit flow should use numbered evidence blocks and `evidence_block_ids`.
- Python should retrieve exact source text from evidence blocks if needed.
- User-facing reports should default to Russian explanations.
- Hebrew originals should be hidden by default and shown only on demand.

## 5. Image Redaction UX

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

## 6. Legal/Product Boundaries

- This product is not legal advice and does not replace a lawyer.
- It is a guided risk-audit and explanation tool.
- Do not implement a conflict-consultant mode unless explicitly requested.
- If conflict-consultant mode is ever added, it must avoid predicting who will win and focus on facts, missing evidence, weak points, documents to request, and when to contact a lawyer.

## 7. Tests and Validation

For code changes, run when practical:

```bash
python -m py_compile app.py contract_checker/*.py
python -m unittest discover -s tests
```

If the environment lacks `python` on PATH, use the available Python interpreter and report what was used.

For documentation-only changes, tests are not required, but the PR summary should say that the change is documentation-only.

## 8. Pull Request Behavior

- Create a Pull Request to `main`.
- In the PR summary, list changed files.
- State whether the change is code or documentation only.
- State whether tests were run.
- State explicitly if no external APIs, OCR, Gemini image calls, or new dependencies were added.
- Do not give the user local git commands instead of creating a PR.
