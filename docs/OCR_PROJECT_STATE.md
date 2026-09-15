# OCR Project State & Continuity v0

Последнее обновление: 2026-09-15, PR #266, `question-engine-provider-resilience-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-provider-robust-fallback-ledger-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #266 run-scoped Flash model memory

PR #266 — первый из нескольких owner-authorized bounded corrective шагов после provider audit. Реальный Gemini run до завершения последующих corrective не выполняется.

Provider experiment continuity, релевантная текущему исправлению:

- локальный run v5 после PR #263 подтвердил рабочий `responseMimeType + responseJsonSchema`, но завершил только `3/10` cases за `1196.61s`; после case 4 primary 3.6 упёрлась в per-model daily free-tier quota;
- PR #264 увеличил inter-case pacing до 30 секунд;
- PR #265 различил daily-quota 429 и short-window 429 и временно добавил `gemini-3.1-pro-preview`;
- последующий статический provider audit выявил, что daily-exhausted model не запоминается между cases, malformed/provider-shape failures не получают robust fallback, attempt provenance/report persistence недостаточны, общий retry budget смешивает retry и routing, а `401/403` нельзя трактовать как обычную недоступность одной модели;
- владелец продукта решил пока не использовать `gemini-3.1-pro-preview` через API из-за отсутствия подтверждённого бесплатного API tier для этого проекта.

PR #266 меняет только route scope, run-scoped model memory и глобальную обработку authentication/permission failures:

- diagnostic route ограничен `gemini-3.6-flash → gemini-3.5-flash`; Pro исключён из runtime route/report;
- неподдерживаемый `GEMINI_MODEL` override блокируется до provider request;
- confirmed per-model daily quota и stable `404` model-unavailable запоминаются в общем run-scoped set;
- последующие cases не обращаются повторно к модели, уже признанной недоступной в этом run;
- HTTP `401/403` теперь считаются global authentication/permission failure: текущий run прекращается без fallback на вторую модель и без повторных provider requests;
- 503/timeout/short-window 429 поведение, structured-output request, semantic prompt, corpus oracle, strict scorer, 30-second pacing и 120-second timeout остаются без semantic изменений;
- malformed-output fallback, structured quota/retry parsing, separate retry/routing budgets, attempt ledger, report redaction и checkpoint persistence намеренно остаются следующими bounded corrective.

Provider payload остаётся synthetic/sanitized; real contracts, raw OCR и recoverable PII не используются.

## 2. Canonical next step

`next_step_id = question-engine-provider-robust-fallback-ledger-v1`

Следующий bounded шаг до любого нового Gemini run:

- fallback на вторую Flash-модель для malformed HTTP-200 envelope/model JSON/local schema failure;
- локальная валидация response contract до semantic scorer;
- structured parsing quota/retry metadata;
- bounded retry policy, в которой routing не теряется из-за ранних retries;
- attempt ledger/per-model summary;
- гарантированное сохранение partial report;
- prompt/corpus/oracle/scorer semantics не менять; Pro не добавлять.

После завершения corrective chain evidence gate возвращается к `question-engine-security-provider-experiment-local-run-v6`.

## 3. Current Question Engine architecture

```text
privacy-validated sanitized contract material
→ analysis-completeness / document-type gate
→ deterministic smart core question inventory
→ support/dependency facts only when required by a smart mechanism
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

Ключевые invariants сохраняются: не извлекать базовый факт ради полноты; handwriting не угадывать; разные security instruments не сливать; missing/blank dependencies не исправлять молча; candidate finding не считать final finding; user-facing output не выдаёт `safe to sign`, sign/don't-sign advice, court prediction или categorical enforceability claim без отдельно одобренного deterministic rule.

## 4. Provider/privacy invariants

Provider experiment отправляет только synthetic/sanitized corpus material. Local API key читается из environment/Desktop `.env.local`, не входит в prompt и scrubbed из HTTP error detail. `.env.local` остаётся вне repository tree и игнорируется `.gitignore`.

PR #266 сохраняет тот же fixed Google GenerateContent host, case count 10, timeout 120 секунд, attempt cap 4 на case и pacing 30 секунд. Новых dependencies, workflows, permissions, storage, OCR/Android/serverless paths или statutory runtime нет.

Repository остаётся pre-production. Production use с real contracts blocked до отдельно проверенных consent, authorization, encryption/key lifecycle, Israel-only restricted-data processing, deletion/retention, logging, provider terms, abuse/resource controls и incident response.

## 5. Audit continuity

Последний завершённый Question Engine batch audit, который должен сохраняться как recovery marker:

- дата: `2026-09-08`;
- start SHA: `cbbb8e0905c1fda8610260d4046b51952a9f636c`;
- end SHA: `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`;
- principal PR range: `#234–#250`;
- outcome: `CORRECTIVE PR REQUIRED`;
- privacy/security regression в этом range не был отмечен.

После PR #265 отдельный provider audit остановил только provider experiment до corrective work. Старый опубликованный API key уже был ранее заблокирован Google и не является новым blocker для PR #266. Runtime findings требуют убрать повторные обращения к exhausted models, не маршрутизировать global auth/project failures как model fallback, добавить robust malformed-output fallback, attempt provenance и partial-report persistence.

PR #266 закрывает только первую часть: удаляет Pro из API route по решению владельца, добавляет run-scoped memory для daily-quota/404 model-unavailable Flash-моделей и прекращает run на global `401/403` без fallback.

Provider experiment остаётся paused. Следующий implementation gate — `question-engine-provider-robust-fallback-ledger-v1`; только после всей corrective chain local run v6 может расходовать Gemini quota.

## 6. Stable recovery anchors

Current provider-independent schema foundation:

```text
AnswerState
  presence: PresenceStatus
  value: ValueStatus
  evidence: EvidenceStatus
  source: SourceStatus
  lifecycle: DocumentLifecycle

MechanismCollection(domain, mechanisms)
MechanismInstance(mechanism_id, mechanism_type, properties)
MechanismProperty(name, value, state)

FindingCandidate(finding_id, domain, subject_refs)
FindingResolution(candidate, outcome, reviewed_refs, resolution_summary)
FindingOutcome = CONFIRMED | NARROWED | CLEARED
```

Current smart CORE families: security/enforcement, early exit/replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/damage evidence, termination/cure/notice, option/renewal. Corpus oracle v2 остаётся evaluation representation, а не production runtime schema.

Statutory recovery anchor: 2017 residential-rental reform effective `2017-09-17`; maintained baseline также учитывает 2026 amendment timing для section `25י`. Если current-law freshness/applicability/effective date не установлены безопасно, runtime должен деградировать к contract-only analysis, а не утверждать устаревшую норму.

Frozen OCR recovery anchor: Surya/cloud OCR infrastructure остаётся frozen research; Tesseract full-page Hebrew OCR на target phone остаётся `NO-GO`; historical Android geometry/preprocessing findings deferred и не блокируют Question Engine development.

## 7. Recovery/work rules

Перед новым PR читать с актуального `main`: `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`, оба state-файла, `docs/DOCUMENT_STATUS_INDEX.md`, `docs/CODEX_WORKFLOW.md`.

Каждый PR: ровно один Context Gate v1; оба state-файла обновляются; финальные checks относятся к exact final head; actual paths совпадают с Context Gate; mandatory security review; auto-merge запрещён.

## 8. PR #266 validation target

Перед Ready/merge проверить:

- changed paths exactly match Context Gate;
- branch основан на `main` head `00f2ebc7f64ccf28a9a0ad4876591901adc9df71`;
- state files идентифицируют PR #266 и `question-engine-provider-resilience-v1`;
- next step — `question-engine-provider-robust-fallback-ledger-v1`;
- route ровно `gemini-3.6-flash → gemini-3.5-flash`; Pro model identifier отсутствует в provider runtime/report;
- unsupported model override fails before provider access;
- daily quota или `404` model unavailability remembered across later cases; later cases skip remembered model;
- `401/403` abort the run globally with no model fallback;
- 503, timeout и short-window 429 остаются bounded;
- timeout 120 секунд, attempt cap 4, pacing 30 секунд;
- structured-output request, prompt, target assertions, corpus selection и semantic/evidence scorer не меняются;
- focused tests и Python compilation pass на exact final code/test blobs;
- Markdown/JSON state согласованы;
- final security review passes;
- malformed-output fallback, structured quota metadata parsing, attempt ledger, report redaction и checkpoint persistence остаются deferred только до следующих bounded corrective перед local run v6.
