# OCR Project State & Continuity v0

Последнее обновление: 2026-09-16, PR #271, `question-engine-single-contract-local-pdf-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-single-contract-real-run-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления. Binding architecture/security/privacy documents остаются выше по приоритету; `active_track` и `next_step_id` выбираются state-файлами.

## 1. Provider baseline already established

Corrective chain #266 → #268 → #269 завершена и слита: bounded retry/routing, fail-closed parsing/schema validation, response-size bounds, run-scoped unavailable-model memory, attempt ledger, redaction/report integrity и terminal lifecycle.

Local provider experiment v6 на 10 synthetic/sanitized security cases дал:

- total duration `705.02s`;
- `8/10` cases completed;
- `14` provider attempts;
- `gemini-3.6-flash`: 10 attempts, 8 successful cases;
- `gemini-3.5-flash`: 4 fallback attempts, 0 successful cases;
- two 3.6 responses were invalid JSON;
- four 3.5 attempts returned provider overload / HTTP 503;
- hard failures in completed semantic cases: `0`.

PR #270 added `gemini-3.7-flash` as an available experimental Flash model while excluding 3.8.

## 2. Product-owner direction change: real contracts one at a time

The product owner explicitly ended the planned synthetic 3.7 comparison as the immediate next step. Evaluation now moves to the available real rental contracts one contract at a time.

PR #271 adds a dedicated local Windows runner for this purpose.

User flow:

```text
launch runner
→ choose exactly one PDF
→ local text-layer extraction
→ remove high-risk identity zones
→ existing deterministic PII redaction
→ residual-PII + contract-usability gate
→ automatic Gemini Flash routing
→ local sanitized structured JSON report
```

There is no model-selection menu in this flow. The automatic route is:

```text
gemini-3.6-flash
→ on provider/rate/response failure: gemini-3.7-flash
→ on provider/rate/response failure: gemini-3.5-flash
```

This is reactive failover based on actual request success/failure. It is not a claim that Gemini exposes a reliable server-load percentage API. Authentication/configuration failures abort instead of falling through. No 3.8 route is added.

## 3. Privacy and PDF scope of PR #271

Real PDF originals remain local and are never committed.

For this first real-contract runner:

- only PDFs with a usable embedded text layer are accepted;
- PDF size, page count and extracted text size are bounded;
- image-only/scanned PDFs fail closed with an OCR-required message;
- raw extracted text is not persisted to the report;
- high-risk header/preamble identity material before the contract-body marker is excluded from cloud handoff;
- signature/footer material after the signature marker is excluded from cloud handoff;
- the remaining body is passed through the existing deterministic Hebrew PII redactor;
- a residual PII gate checks emails, Israeli-looking phones, compact ID values and sensitive field markers;
- if that gate or contract-text usability validation fails, no Gemini call is made;
- the persisted report contains only non-sensitive attempt metadata, redaction counts and the structured analysis result; it does not contain the selected source filename or raw/sanitized contract text.

This runner is a local research/evaluation path, not a production privacy certification. Scanned/image PDFs remain blocked until an approved OCR/privacy path is explicitly reopened.

## 4. Canonical next step

`next_step_id = question-engine-single-contract-real-run-v1`

After PR #271 focused validation and merge, run one chosen real text-layer contract with `run_single_contract_analysis.cmd` and inspect:

- whether the local privacy/usability gate passes;
- which Flash model actually completes the request;
- attempt latency/failure metadata;
- the structured whole-contract analysis;
- whether important cross-clause mechanisms such as security cheque mechanics, early exit/replacement tenant, AS-IS versus repair allocation, cure/termination interaction and handover/holdover are represented coherently.

The first preferred contract is the real March–August 2025 Habastilia/Fox lease because it has an embedded text layer and contains several interacting mechanisms already reviewed manually. Raw source material must remain outside GitHub/CI.

## 5. Current Question Engine architecture

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

## 6. Stable recovery anchors

Current smart CORE families: security/enforcement, early exit/replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/damage evidence, termination/cure/notice, option/renewal. Corpus oracle v2 remains an evaluation representation, not production runtime schema.

Statutory anchor: 2017 residential-rental reform effective `2017-09-17`; maintained baseline includes 2026 amendment timing for section `25י`; when freshness/applicability is insufficient, runtime degrades to contract-only analysis.

Frozen OCR anchor: Surya/cloud OCR remains frozen research; Tesseract full-page Hebrew OCR on the target phone remains `NO-GO`; Android geometry/preprocessing work remains deferred unless explicitly reopened.

Last completed Question Engine batch audit marker: 2026-09-08, start `cbbb8e0905c1fda8610260d4046b51952a9f636c`, end `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`, principal PR range `#234–#250`, outcome `CORRECTIVE PR REQUIRED`. Provider audit after #265 is separate and its bounded corrective chain is complete.

## 7. Recovery/work rules

Before a new PR read from current base: `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`, both state files, `docs/DOCUMENT_STATUS_INDEX.md`, and `docs/CODEX_WORKFLOW.md`.

Every PR: exactly one Context Gate v1; both state files updated; final checks apply to the exact final head; actual paths exactly match the Context Gate; mandatory final-diff security review; auto-merge disabled.
