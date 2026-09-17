# OCR Project State & Continuity v0

Последнее обновление: 2026-09-17, PR #277, `single-contract-runner-no-web-ui-cache-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-single-contract-real-rerun-v4`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления. Binding architecture/security/privacy documents остаются выше по приоритету; `active_track` и `next_step_id` выбираются state-файлами.

## 1. Provider baseline

Corrective chain #266 → #268 → #269 завершена и слита: bounded retry/routing, fail-closed parsing/schema validation, response-size bounds, run-scoped unavailable-model memory, attempt ledger, redaction/report integrity и terminal lifecycle.

Local provider experiment v6 на 10 synthetic/sanitized security cases дал `705.02s`, `8/10` completed, 14 provider attempts; 3.6 succeeded on 8 cases, 3.5 succeeded on 0/4 fallback attempts. PR #270 added 3.7 for experimental Flash routing while excluding 3.8.

Current real-contract automatic route after PR #273 is cyclic:

```text
gemini-3.6-flash
→ on retryable provider/rate/response failure: gemini-3.7-flash
→ on retryable provider/rate/response failure: gemini-3.5-flash
→ if the full cycle fails: wait 30 seconds
→ restart at gemini-3.6-flash
→ repeat until success or user Ctrl+C
```

The user does not select a model. Routing is reactive failover based on actual request success/failure, not a server-load percentage API. Authentication/configuration failures remain terminal and do not loop.

## 2. Real-contract runner and privacy boundary

PR #271 is merged and provides `run_single_contract_analysis.cmd` for one local PDF at a time.

Current flow:

```text
choose exactly one PDF
→ local text-layer extraction
→ remove identity-heavy preamble/header and signature tail
→ redact recurring header-derived party names
→ existing deterministic PII redaction
→ residual-PII + contract-usability gate
→ cyclic automatic Gemini Flash routing
→ guarded local structured JSON report
```

Real PDF originals remain local and are never committed. The persisted report does not contain the source filename or raw/sanitized contract text. Image-only/scanned PDFs remain fail-closed and require a future explicitly approved OCR/privacy path. PR #274 does not reopen OCR.

## 3. First real full-contract run

The March–August 2025 text-layer lease was run successfully after PR #271:

- `gemini-3.6-flash` completed on the first attempt;
- provider elapsed time: `35.334s`;
- document quality returned `usable=true`, `completeness=high`;
- local sanitization had already passed the reviewed privacy smoke before the provider call.

The model correctly located many major mechanisms: rent/term, replacement-tenant early exit, security instruments, utilities, repairs, landlord access, holdover sanction, broad fundamental-breach wording and set-off restriction.

The same run exposed important report-control defects:

- the 20,000 NIS security cheque was recognized, but its realization mechanics were underweighted versus amount/market-comparison prose;
- broad fundamental-breach wording was not fully reconciled with the contract's specific 7-day cure for rent arrears;
- AS-IS remained a warning despite related landlord repair/hidden-defect protections;
- the useful 21-day pre-return inspection / 10-day defect-correction procedure was underemphasized while the holdover sanction was surfaced;
- `missing_clauses` drifted into a wishlist such as renewal option/building insurance;
- the model invented unsupported market norms and numeric remediation examples such as 2–3 months, 14 days, 48 hours, and 2,000–3,000 NIS.

Conclusion: the model is useful as a semantic reader, but the final report needs deterministic Question Engine inventory, second-pass cross-clause resolution, materiality/suppression, statutory gating and remediation gating.

## 4. PR #272 corrective scope

PR #272 wires the already-existing deterministic core inventories into the whole-contract model prompt instead of asking the model to choose its own review agenda. The review inventory covers security/enforcement, early exit/replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/repairs, termination/cure/notice, and option/renewal.

Prompt guardrails require:

- a second pass before retaining red/yellow findings;
- complete per-instrument security mechanics, including notice/cure and return;
- reconciliation of broad breach definitions with specific cure rules;
- reconciliation of AS-IS with repair, hidden-defect and ordinary-wear provisions;
- combined analysis of handover protocol, correction period and holdover sanction;
- literal set-off wording to remain separate from statutory effect;
- no unsupported market-practice claims or invented numeric limits/deadlines;
- absence of an optional/wishlist clause not to become a risk automatically.

Until dedicated deterministic/statutory/remediation layers are wired into this local real-contract path, the persisted report additionally suppresses model-owned `proposed_changes`, generic `missing_clauses`, per-risk rewrite requests, and market-comparison prose. Source-grounded clause analysis, risks, questions, unclear fragments and financial facts remain.

Provider route, PII gate, PDF scope, dependencies, permissions and network destinations were unchanged by PR #272.

## 5. Failed same-contract rerun and PR #273 correction

After PR #272 merged, the same March–August 2025 contract was launched again. The runner attempted the configured Flash route once and then stopped with:

```text
All configured Gemini Flash models failed for this contract
```

That behavior did not match the product-owner requirement. PR #273 changed only retry orchestration in the local real-contract runner:

- retryable `GeminiRateLimitError` and `GeminiResponseError` outcomes move to the next model;
- after 3.6, 3.7 and 3.5 have all failed, the runner waits 30 seconds and starts again at 3.6;
- cycles continue until one model returns a valid `ContractAuditResult` or the user stops with Ctrl+C;
- authentication/configuration failures remain terminal;
- console status shows only cycle number, model, safe error class and elapsed seconds;
- the attempt ledger records the cycle for every attempt and is persisted only if a model eventually succeeds;
- no raw provider exception body, API key or contract text is printed.

Prompt, output guardrails, privacy boundary, OCR scope, model list, dependencies, permissions, endpoint set and network destinations were unchanged.

## 6. Successful post-#273 rerun and remaining defects

The same reviewed contract later completed after cyclic routing:

- cycles 1–3: all three configured Flash models returned retryable `GeminiResponseError` outcomes;
- cycle 4: `gemini-3.6-flash` completed successfully in `36.599s`;
- total attempts: `10`;
- no raw contract material from this run is committed.

The #272 guardrails materially improved the semantic result:

- AS-IS was read together with landlord repair/hidden-defect protections and remained `normal`;
- the 21-day pre-return inspection, 10-day correction window and double-daily holdover mechanism were read together;
- invented market comparisons and numeric rewrite suggestions disappeared;
- generic `missing_clauses` and `proposed_changes` were absent;
- the 20,000 NIS security cheque was recognized as having incomplete realization mechanics rather than being treated mainly as a large amount.

Two important gaps remained:

1. the 20,000 NIS security-cheque mechanism produced only a subset of the required questions; completion authority, realization grounds/amount basis, cure details and the cheque-specific return mechanism were not all forced into explicit output;
2. the broad fundamental-breach finding still did not fully reconcile the contract's specific 7-day rent cure/notice mechanics, despite the prompt-only second-pass instruction.

Conclusion: a prompt-only internal inventory is insufficient because a model can silently skip an inventory item or one of its required fields while still returning a schema-valid legacy audit.

## 7. PR #274 explicit Question Engine answer coverage

PR #274 converts the core inventory from an internal checklist into a mandatory structured extraction layer.

Each provider result must now include `question_engine_answers` with:

- exactly one object for every core `question_id`;
- one controlled status: `FOUND`, `NOT_FOUND`, `AMBIGUOUS`, `HANDWRITING_DEPENDENCY`, or `CLAUSE_PRESENT_VALUE_BLANK`;
- a compact positional `values` list whose length and order exactly match that question's declared `answer_fields`;
- source `evidence_block_ids` for non-`NOT_FOUND` answers.

Python validates the extraction before the provider result is accepted. It rejects:

- missing core question IDs;
- duplicate or unknown question IDs;
- the wrong number of positional values;
- `NOT_FOUND` paired with non-null extracted values;
- non-`NOT_FOUND` answers without evidence;
- evidence block IDs that do not exist in the sanitized source evidence set;
- a `FOUND` answer that contains no actual value.

A rejected extraction becomes the existing controlled `GeminiResponseError`, so the already-merged cyclic provider route can move to the next model without exposing contract text or provider exception bodies.

This PR does not yet make the legacy narrative report a full deterministic `FindingResolution` renderer. Its bounded purpose is to ensure the semantic extraction layer cannot silently omit core Question Engine questions or answer fields. The explicit answers are persisted in the local sanitized report and become the input for later deterministic resolution/materiality logic.

### 7.1 PR #275 local runner warning cleanup

PR #275 was a bounded attempt to clean the command-line console:

- replace deprecated `fitz` compatibility import with `pymupdf` in the runner and its focused PDF test;
- suppress two known library advisory logger paths;
- keep runner retry status, controlled Gemini errors, authentication/configuration failures and other Python warnings/errors visible.

A fresh downloaded `main` showed that only the PyMuPDF warning was actually removed. The other two library warning sources remained noisy.

### 7.2 PR #276 warning cleanup correction

PR #276 tried a second logger-specific correction by initializing the old web UI framework before setting logger thresholds and by targeting the actual Google GenAI logger name. A fresh downloaded `main` still showed warning noise in the local CLI.

### 7.3 PR #277 remove web-UI warning plumbing from the CLI

PR #277 removes the previous web-UI import and all web-UI logger configuration from `tools/single_contract_analysis.py`.

The local runner now disables Python logging at `WARNING` level for its own process before shared analysis modules are imported. Runner-owned cycle/status/error output uses `print` and controlled exceptions, so it remains visible; logging at `ERROR` and `CRITICAL` remains enabled. This intentionally trades library warning verbosity for a clean operator console in this one command-line tool.

Provider routing, retry timing, Question Engine schema/prompt/validation, privacy boundary, OCR path, report payload, dependency set, permission set, workflows, endpoint set and network destinations are unchanged.

## 8. Canonical next step

`next_step_id = question-engine-single-contract-real-rerun-v4`

After PR #277 validation and merge, rerun the same reviewed March–August 2025 contract. Before broadening to any other contract, inspect the explicit answers for at least:

- `security.completion_authority`;
- `security.realization_chain`;
- `security.return_mechanics`;
- `termination.notice_cure`;
- `termination.cross_clause_interaction`.

The key acceptance question is no longer only whether the narrative sounds better. Verify that every core question ID is present, every declared answer field has a positional value/null, evidence references are grounded, and the security/termination interactions are explicitly extractable for later deterministic `FindingResolution`.

## 9. Current Question Engine architecture

```text
privacy-validated sanitized contract material
→ analysis-completeness / document-type gate
→ deterministic smart core question inventory
→ explicit LLM structured answers for every core question_id
→ Python question/field/evidence coverage validation
→ deterministic conditional follow-ups
→ cross-clause interaction checks
→ bounded novel-issue catch-all
→ Python/schema/evidence/consistency validation
→ statutory comparison where applicable
→ FindingResolution: CONFIRMED / NARROWED / CLEARED
→ materiality / suppression
→ Safe Output
```

Core invariants: handwriting is never guessed; different security instruments remain distinct; missing/blank dependencies are explicit; candidate finding is not final finding; user-facing output does not issue sign/don't-sign advice, court predictions, or categorical enforceability claims without a separately approved deterministic rule.

## 10. Stable recovery anchors

Current smart CORE families: security/enforcement, early exit/replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/damage evidence, termination/cure/notice, option/renewal. Corpus oracle v2 remains an evaluation representation, not production runtime schema.

Statutory anchor: 2017 residential-rental reform effective `2017-09-17`; maintained baseline includes 2026 amendment timing for section `25י`; when freshness/applicability is insufficient, runtime degrades to contract-only analysis.

Frozen OCR anchor: Surya/cloud OCR remains frozen research; Tesseract full-page Hebrew OCR on the target phone remains `NO-GO`; Android geometry/preprocessing work remains deferred unless explicitly reopened.

Last completed Question Engine batch audit marker: 2026-09-08, start `cbbb8e0905c1fda8610260d4046b51952a9f636c`, end `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`, principal PR range `#234–#250`, outcome `CORRECTIVE PR REQUIRED`. Provider audit after #265 is separate and its bounded corrective chain is complete.

## 11. Recovery/work rules

Before a new PR read from current base: `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`, both state files, `docs/DOCUMENT_STATUS_INDEX.md`, and `docs/CODEX_WORKFLOW.md`.

Every PR: exactly one Context Gate v1; both state files updated; final checks apply to the exact final head; actual paths exactly match the Context Gate; mandatory final-diff security review; auto-merge disabled.
