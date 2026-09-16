# OCR Project State & Continuity v0

Последнее обновление: 2026-09-16, PR #273, `question-engine-provider-cycle-retry-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-single-contract-real-rerun-v3`.

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

Real PDF originals remain local and are never committed. The persisted report does not contain the source filename or raw/sanitized contract text. Image-only/scanned PDFs remain fail-closed and require a future explicitly approved OCR/privacy path. PR #273 does not reopen OCR.

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

That behavior does not match the product-owner requirement. A transiently overloaded provider should not terminate the whole user run merely because all three models failed once.

PR #273 changes only retry orchestration in the local real-contract runner:

- retryable `GeminiRateLimitError` and `GeminiResponseError` outcomes move to the next model;
- after 3.6, 3.7 and 3.5 have all failed, the runner waits 30 seconds and starts again at 3.6;
- cycles continue until one model returns a valid `ContractAuditResult` or the user stops with Ctrl+C;
- authentication/configuration failures remain terminal;
- console status shows only cycle number, model, safe error class and elapsed seconds;
- the attempt ledger records the cycle for every attempt and is persisted only if a model eventually succeeds;
- no raw provider exception body, API key or contract text is printed.

Prompt, output guardrails, privacy boundary, OCR scope, model list, dependencies, permissions, endpoint set and network destinations are unchanged.

## 6. Canonical next step

`next_step_id = question-engine-single-contract-real-rerun-v3`

After PR #273 focused validation and merge, rerun the same reviewed March–August 2025 contract and allow cyclic provider retries to continue until one model succeeds or the run is manually stopped. Then compare the new report against the first real run. Specifically verify:

- the 20,000 NIS cheque is discussed through its complete mechanism rather than mainly its size;
- broad fundamental-breach wording is reconciled with the existing 7-day rent cure;
- AS-IS is narrowed by the related repair/hidden-defect allocation where supported;
- the 21-day inspection and 10-day correction process survives alongside the holdover sanction;
- no generic missing warnings for renewal option/building insurance appear;
- no invented 2–3 month, 14-day, 48-hour, or 2,000–3,000 NIS recommendations appear.

Do not move to the other real contracts until this same-contract before/after comparison is inspected.

## 7. Current Question Engine architecture

```text
privacy-validated sanitized contract material
→ analysis-completeness / document-type gate
→ deterministic smart core question inventory
→ support/dependency facts only when required
→ LLM structured semantic extraction
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

## 8. Stable recovery anchors

Current smart CORE families: security/enforcement, early exit/replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/damage evidence, termination/cure/notice, option/renewal. Corpus oracle v2 remains an evaluation representation, not production runtime schema.

Statutory anchor: 2017 residential-rental reform effective `2017-09-17`; maintained baseline includes 2026 amendment timing for section `25י`; when freshness/applicability is insufficient, runtime degrades to contract-only analysis.

Frozen OCR anchor: Surya/cloud OCR remains frozen research; Tesseract full-page Hebrew OCR on the target phone remains `NO-GO`; Android geometry/preprocessing work remains deferred unless explicitly reopened.

Last completed Question Engine batch audit marker: 2026-09-08, start `cbbb8e0905c1fda8610260d4046b51952a9f636c`, end `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`, principal PR range `#234–#250`, outcome `CORRECTIVE PR REQUIRED`. Provider audit after #265 is separate and its bounded corrective chain is complete.

## 9. Recovery/work rules

Before a new PR read from current base: `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`, both state files, `docs/DOCUMENT_STATUS_INDEX.md`, and `docs/CODEX_WORKFLOW.md`.

Every PR: exactly one Context Gate v1; both state files updated; final checks apply to the exact final head; actual paths exactly match the Context Gate; mandatory final-diff security review; auto-merge disabled.
