# OCR Project State & Continuity v0

Последнее обновление: 2026-09-15, PR #270, `question-engine-security-provider-37-menu-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-security-provider-37-comparison-run-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления. Binding architecture/security/privacy documents остаются выше по приоритету; `active_track` и `next_step_id` выбираются state-файлами.

## 1. Provider harness status

Corrective chain #266 → #268 → #269 завершена и слита. Она ограничила provider route Flash-моделями, добавила bounded retry/routing, fail-closed parsing/schema validation, response-size bounds, run-scoped unavailable-model memory, attempt ledger, redaction/report integrity и terminal lifecycle. Воспроизводимый HIGH с ложным `COMPLETED` при exhaustion route на последнем case исправлен; LOW observations по HTTP-date `Retry-After` и jitter остаются out of scope.

Local provider experiment v6 выполнен на десяти synthetic/sanitized security cases:

- total duration: `705.02s`;
- cases completed: `8/10`;
- provider attempts: `14`;
- `gemini-3.6-flash`: 10 attempts, 8 successful cases;
- `gemini-3.5-flash`: 4 fallback attempts, 0 successful cases;
- provider failures: 2 × `model_output_invalid_json` from 3.6, 4 × `provider_overloaded`/HTTP 503 from 3.5;
- hard failures in completed semantic cases: `0`.

The local JSON/TXT report is runtime evidence only and is not committed to the repository.

## 2. PR #270 bounded model-selection change

Product owner explicitly authorized adding Gemini 3.7 for comparison while excluding 3.8.

PR #270 adds a local launcher menu with selectable primary models:

- `gemini-3.6-flash`;
- `gemini-3.7-flash`;
- `gemini-3.5-flash`.

Routing remains bounded to at most two models. For 3.6 or 3.7 primary, the only fallback is existing `gemini-3.5-flash`. Selecting 3.5 produces a single-model route. The underlying provider harness retry logic, schema, scorer, corpus and network destination are unchanged. No 3.8 route is introduced.

## 3. Canonical next step

`next_step_id = question-engine-security-provider-37-comparison-run-v1`

After PR #270 passes focused validation and is merged, run the same ten-case synthetic/sanitized provider experiment with `gemini-3.7-flash` as primary. Compare against the v6 3.6 baseline using:

- total latency and per-attempt latency;
- completed cases;
- provider failure classes;
- fallback frequency/success;
- exact/value/state/ref/resolution semantic metrics;
- hard failures.

Do not add 3.8 or expand the automatic route beyond one fallback during this comparison.

## 4. Current Question Engine architecture

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

Core invariants: handwriting не угадывается; different security instruments remain distinct; missing/blank dependencies are explicit; candidate finding is not final finding; user-facing output does not issue sign/don't-sign advice, court predictions, or categorical enforceability claims without a separately approved deterministic rule.

## 5. Provider/privacy invariants

Diagnostic provider experiments may use only synthetic or privacy-validated sanitized material. Real contracts, raw PDF/page images, raw OCR, names, IDs, phones, email, addresses, signatures, bank/check identifiers, guarantor PII and other recoverable PII must not enter Gemini prompts, GitHub, CI, logs or committed fixtures.

The eight newly available real PDF contracts may be used only after local extraction/OCR and privacy validation produce sanitized derivatives. Raw originals stay local and are not committed.

Provider host remains the fixed Google GenerateContent endpoint already used by the harness. Current bounds remain timeout 120 seconds, pacing 30 seconds, attempt cap 2/model and 4/global, bounded HTTP-200 body, fail-closed structured parsing and report secret redaction. PR #270 adds no dependency, workflow, permission, storage path, OCR/Android/serverless path or production data flow.

Repository remains pre-production. Production use with real contracts remains blocked by the binding security/privacy requirements in `SECURITY.md` and architecture documents.

## 6. Stable recovery anchors

Current smart CORE families: security/enforcement, early exit/replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/damage evidence, termination/cure/notice, option/renewal. Corpus oracle v2 remains an evaluation representation, not production runtime schema.

Statutory anchor: 2017 residential-rental reform effective `2017-09-17`; maintained baseline includes 2026 amendment timing for section `25י`; when freshness/applicability is insufficient, runtime degrades to contract-only analysis.

Frozen OCR anchor: Surya/cloud OCR remains frozen research; Tesseract full-page Hebrew OCR on the target phone remains `NO-GO`; Android geometry/preprocessing work remains deferred unless explicitly reopened.

Last completed Question Engine batch audit marker: 2026-09-08, start `cbbb8e0905c1fda8610260d4046b51952a9f636c`, end `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`, principal PR range `#234–#250`, outcome `CORRECTIVE PR REQUIRED`. Provider audit after #265 is separate and its bounded corrective chain is complete.

## 7. Recovery/work rules

Before a new PR read from current base: `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`, both state files, `docs/DOCUMENT_STATUS_INDEX.md`, and `docs/CODEX_WORKFLOW.md`.

Every PR: exactly one Context Gate v1; both state files updated; final checks apply to the exact final head; actual paths exactly match the Context Gate; mandatory final-diff security review; auto-merge disabled.
