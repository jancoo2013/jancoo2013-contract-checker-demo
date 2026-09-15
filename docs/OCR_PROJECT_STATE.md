# OCR Project State & Continuity v0

Последнее обновление: 2026-09-15, PR #269, `question-engine-provider-ledger-reporting-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-security-provider-experiment-local-run-v6`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления. Binding architecture/security/privacy documents остаются выше по приоритету; `active_track` и `next_step_id` выбираются state-файлами.

## 1. Provider corrective chain

Provider corrective chain завершена:

- #266: route ограничен `gemini-3.6-flash → gemini-3.5-flash`; unsupported override блокируется до request; daily quota/404 запоминаются на run; 400/401/403 прекращают run как global provider/config/auth failure.
- #268: bounded HTTP-200 body; malformed envelope/model/schema output fail-closed; NaN/Infinity отклоняются; structured QuotaFailure/RetryInfo поддерживаются; retry caps `2/model`, `4/global`; prompt, selected cases, oracle и scorer не менялись.
- #269: attempt ledger, per-model reporting, recursive redaction перед persistence/rendering, checkpoint lifecycle, explicit route reporting и TXT-first/JSON-last terminal publication.
- После combined audit найден один воспроизводимый HIGH: exhaustion route на последнем/единственном case мог сохранить `COMPLETED`. Он исправлен в #269: после failing call, исчерпавшего весь route, status сразу становится `ABORTED_ROUTE_EXHAUSTED`. Regression test покрывает две structured daily-quota ошибки, две попытки, отсутствие sleep и terminal status в report/persisted JSON.

LOW observations по HTTP-date `Retry-After` и jitter остаются out of scope.

Старый #267 superseded и не должен мержиться; его функциональность заменена #268 + #269.

Relevant runtime history: local run v3 дал usable report; v4 получил 10/10 HTTP 400 из-за request field; #263 исправил request shape; v5 завершил 3/10 и упёрся в daily quota 3.6; #264 установил pacing 30 секунд; #265 различил daily/short-window 429, после чего provider audit запустил corrective chain.

## 2. Canonical next step

`next_step_id = question-engine-security-provider-experiment-local-run-v6`

Владелец явно завершил повторный Codex review loop после исправления воспроизводимого HIGH. Новый combined Codex review не является gate.

Permitted sequence:

1. На exact final #269 head выполнить local `py_compile` и focused unit suite без provider calls.
2. При PASS последовательно merge `#266 → #268 → #269`; auto-merge не включать.
3. Проверить merged `main`.
4. Только после этого выполнить local provider experiment v6 на synthetic/sanitized corpus.

Если final local validation не проходит, исправляется только конкретный воспроизводимый дефект; real provider run до PASS и merge chain запрещён.

## 3. Current Question Engine architecture

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

Core invariants: basic facts не извлекаются ради полноты; handwriting не угадывается; разные security instruments не сливаются; missing/blank dependencies не исправляются молча; candidate finding не является final finding; user-facing output не выдаёт sign/don't-sign advice, court prediction или categorical enforceability claim без отдельно одобренного deterministic rule.

## 4. Provider/privacy invariants

Provider experiment использует только synthetic/sanitized corpus material. Real contracts, raw OCR и recoverable PII в diagnostic harness не передаются.

Route после #269: `gemini-3.6-flash → gemini-3.5-flash`; timeout 120 секунд; pacing 30 секунд; attempt cap 2/model и 4/global; HTTP-200 body bounded. Pro отсутствует.

Новых dependencies, workflows, permissions, provider hosts, production storage, OCR/Android/serverless paths или statutory runtime corrective chain не вводит. Repository остаётся pre-production; production use с real contracts отдельно blocked binding security/privacy requirements.

## 5. Audit continuity

Последний завершённый Question Engine batch audit marker:

- дата `2026-09-08`;
- start `cbbb8e0905c1fda8610260d4046b51952a9f636c`;
- end `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`;
- principal PR range `#234–#250`;
- outcome `CORRECTIVE PR REQUIRED`.

Provider audit после #265 относится только к provider experiment corrective chain.

## 6. Stable recovery anchors

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

Current smart CORE families: security/enforcement, early exit/replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/damage evidence, termination/cure/notice, option/renewal. Corpus oracle v2 — evaluation representation, не production runtime schema.

Statutory anchor: 2017 residential-rental reform effective `2017-09-17`; maintained baseline учитывает 2026 amendment timing для section `25י`; при недостаточной freshness/applicability runtime деградирует к contract-only analysis.

Frozen OCR anchor: Surya/cloud OCR остаётся frozen research; Tesseract full-page Hebrew OCR на target phone остаётся `NO-GO`; Android geometry/preprocessing deferred.

## 7. Recovery/work rules

Перед новым PR читать с актуальной base: `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`, оба state-файла, `docs/DOCUMENT_STATUS_INDEX.md`, `docs/CODEX_WORKFLOW.md`.

Каждый PR: один Context Gate v1; оба state-файла обновляются; final checks относятся к exact final head; actual paths совпадают с Context Gate; mandatory security review; auto-merge запрещён.

## 8. PR #269 merge gate

Перед merge проверить exact #268 base, четыре Context Gate path, state agreement, route только `3.6 Flash → 3.5 Flash`, отсутствие Pro, bounded ledger/reporting/redaction, correct `ABORTED_ROUTE_EXHAUSTED` включая последний case, partial terminal checkpoints, JSON-after-TXT publication, single-model route reporting, semantic non-regression, focused tests и Python compilation на exact final head.

Реальный Gemini run запрещён до final local validation и последовательного merge `#266 → #268 → #269`.
