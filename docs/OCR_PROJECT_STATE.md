# OCR Project State & Continuity v0

Последнее обновление: 2026-09-09, PR #255, `question-engine-smart-analysis-corpus-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-security-provider-experiment-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #255 smart-analysis corpus v1

После owner review Codex batch audit сохранена ключевая продуктовая коррекция:

- продукт не должен становиться универсальным пересказчиком договора;
- очевидные пользователю facts не становятся пользовательским `CORE` только потому, что присутствуют в договоре;
- простой fact извлекается как support/dependency input только когда materially нужен для более глубокого анализа, deterministic calculation, statutory gate или cross-clause resolution;
- обнаруженное формальное несоответствие не обязано становиться finding, если оно не меняет существенный механизм для пользователя.

Post-audit corrective foundation теперь включает:

1. PR #251 — `analysis completeness` / document-type gate: unrelated/unconfirmed document type блокируется fail-closed; missing analysis-relevant documents делают только зависимые области `PARTIAL`.
2. PR #252 — answer-state separation: presence, value, evidence, source consistency и lifecycle представлены независимо.
3. PR #253 — repeatable mechanism identity: properties нескольких security instruments остаются привязаны к конкретному local `mechanism_id`.
4. PR #254 — finding resolution: candidate concern отделён от second-pass result и не становится финальным finding до cross-clause review.
5. PR #255 — первый smart-analysis evaluation corpus.

PR #255 добавляет `research/question_engine/smart_analysis_corpus_v1.json` как небольшой sanitized/synthetic oracle из 14 semantic counterexamples. Это не training data и не generic full-lease corpus.

Корпус покрывает:

- одинаковый security concern, который после related-clause review заканчивается `CONFIRMED`, `NARROWED` или `CLEARED`;
- несколько одновременно существующих security instruments с раздельной identity;
- missing security instrument / missing appendix dependency;
- одинаковый blank в `TEMPLATE` и `EXECUTED` lifecycle;
- handwriting dependency без реконструкции или угадывания рукописи;
- один security mechanism, размазанный по нескольким distant clauses;
- contradictory party-role wording;
- apparent option, которая требует landlord consent;
- materially relevant `ABSENT` early-exit route;
- condition/defect analysis, ограниченный отсутствующим appendix;
- repair concern, который сужается другой clause.

Для каждого case заранее зафиксирован ручной expected semantic oracle: presence/value/evidence/source state, optional finding outcome, expected mechanism IDs и refs, которые должны быть связаны анализом.

Focused integrity tests проверяют структуру corpus, уникальность case/ref IDs, coverage трёх finding outcomes, blank lifecycle pair, handwriting dependency, repeatable security identity, missing dependency, contradiction, materially relevant ABSENT case и отсутствие очевидного contact/identity payload.

PR #255 не добавляет provider/runtime calls, statutory runtime, OCR, Android, serverless, storage, network destinations, dependencies, permissions, workflows, ranking/UI или broad full-contract parser.

## 2. Canonical next step

`next_step_id = question-engine-security-provider-experiment-v1`

Следующий bounded-шаг — первый реальный contract-fact provider experiment, ограниченный security family и только sanitized/synthetic corpus material.

Цель эксперимента — не «проанализировать договор целиком», а проверить, может ли модель стабильно:

- различать несколько security instruments и сохранять их identity;
- возвращать значения вместе с правильными `AnswerState` axes;
- не угадывать handwriting/missing dependencies;
- связывать distant clauses;
- создавать candidate concern отдельно от `CONFIRMED / NARROWED / CLEARED` second-pass result;
- не превращать generic clause presence в user-facing finding без cross-clause review.

Эксперимент должен измерить реальные failure modes и только после этого решить, нужны ли дополнительные fields в LLM↔Python contract, например deterministic evidence refs, typed values или отдельный confidence signal.

Не проектировать эти расширения заранее без provider evidence.

## 3. Required reading order

Перед новым PR читать с актуального `main`:

1. `AGENTS.md`;
2. `SECURITY.md`;
3. `docs/ARCHITECTURE.md`;
4. `docs/CUSTOM_OCR_PIPELINE.md`;
5. `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`;
6. `docs/OCR_PROJECT_STATE.md`;
7. `docs/OCR_PROJECT_STATE.json`;
8. `docs/DOCUMENT_STATUS_INDEX.md`;
9. `docs/CODEX_WORKFLOW.md`.

Question Engine context, когда применимо:

- `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`;
- `docs/QUESTION_ENGINE_DISPUTE_PRACTICE_LAYER_V0.md`;
- `docs/QUESTION_ENGINE_DISPUTE_PRACTICE_CLASSIFICATION_V1.md`;
- `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md`;
- `research/question_engine/golden_contracts/contract_001_he.txt`;
- `research/question_engine/golden_contracts/contract_001.meta.json`;
- `research/question_engine/smart_analysis_corpus_v1.json`.

Research-only dispute/practice artifacts не являются authority и не могут переопределять verified contract evidence, current law, binding docs или canonical state.

## 4. Current Question Engine architecture

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

Главные invariants:

- продукт предназначен прежде всего для нормального заключения договора и предотвращения будущих конфликтов;
- Question Engine не обязан извлекать или показывать банальный fact, если он не нужен для более глубокого анализа;
- обнаруженность mechanism/inconsistency сама по себе не является основанием показывать её пользователю;
- contract facts, statutory rules, dispute/practice research, Question Engine decisions и product explanation остаются разными слоями;
- cross-clause analysis обязателен;
- candidate finding не является final finding;
- handwriting никогда не реконструируется и не угадывается;
- different security instruments остаются семантически различными;
- blanks, missing references и missing appendices не исправляются молча;
- incomplete package сужает только те выводы, которым не хватает evidence, когда остальной анализ безопасно возможен;
- production output не выдаёт `safe to sign`, не советует подписывать/не подписывать, не прогнозирует исход суда и не даёт категорических enforceability/invalidity выводов без отдельно одобренного deterministic rule.

## 5. Current schema and smart inventories

После PR #250 реализованы шесть provider-independent smart `CORE` inventory slices:

1. security and enforcement + monthly-rent support baseline;
2. early exit + replacement tenant;
3. financial sanctions and overlap;
4. condition / AS-IS / defects / damage evidence;
5. termination + cure + notice + vacancy wording;
6. option / renewal mechanics.

Supporting contracts после corrective PRs:

```text
AnswerState
  presence: PresenceStatus
  value: ValueStatus
  evidence: EvidenceStatus
  source: SourceStatus
  lifecycle: DocumentLifecycle
```

```text
MechanismCollection(domain, mechanisms)
MechanismInstance(mechanism_id, mechanism_type, properties)
MechanismProperty(name, value, state)
```

```text
FindingCandidate(finding_id, domain, subject_refs)
FindingResolution(candidate, outcome, reviewed_refs, resolution_summary)
FindingOutcome = CONFIRMED | NARROWED | CLEARED
```

`QuestionSpec` и `QuestionInventory` остаются static question definitions; provider execution пока отсутствует.

Model confidence, statutory applicability result, deterministic evidence refs, provenance graph и typed monetary/date values пока не входят в bounded runtime schema.

## 6. Mechanism classification

Current smart `CORE`:

1. security and enforcement;
2. early exit + replacement tenant;
3. financial sanctions and overlap;
4. condition / AS-IS / defects / damage evidence;
5. termination + cure + notice + physical-eviction distinction;
6. option / renewal mechanics.

`CORE_FACTS_CONDITIONAL_PRACTICE`:

- utilities and occupancy charges только когда механизм становится non-obvious/material, например shared meter, landlord-calculated allocation, open utility cheques или unusual reconciliation.

High-value `CONDITIONAL`:

- broad no-setoff;
- shared-meter accounting;
- landlord access;
- alterations/restoration;
- third-party indemnity;
- inventory/handwriting evidence dependency.

Universal basic `parties/term/rent schedule/notices` user-facing CORE explicitly rejected. Такие facts остаются analysis-support inputs только когда smart mechanism действительно в них нуждается.

## 7. Statutory source status

Current statutory authority должен разрешаться из актуального официального законодательства с effective-date logic.

2017 residential-rental reform — Amendment No. 1, effective `2017-09-17`. Repository snapshot 2017 года является historical engineering snapshot, а не current-law authority сам по себе.

Maintained baseline предупреждает о 2026 amendment timing для section `25י`; future runtime должен version statutory rules by effective date.

Если freshness/applicability/effective date не могут быть безопасно установлены, runtime должен деградировать к contract-only analysis, а не утверждать устаревшую норму.

PR #255 statutory runtime/current-law claims не добавляет.

## 8. Privacy and security invariants

Restricted material включает original contract photos/pages, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers or images, guarantor identifying data и другую recoverable PII.

Restricted material не должен попадать в GitHub/CI, analytics/crash reports, general logs, downstream LLM prompts или unrelated services без отдельно одобренной privacy architecture.

Persistent fixtures/research artifacts должны быть sanitized до commit. Handwriting не угадывается. Monetary amounts, dates, clause numbers, notice periods и legally relevant printed wording не являются PII по умолчанию, когда безопасно отделены от identifiers.

PR #255 содержит только synthetic/sanitized Hebrew clauses, expected semantic metadata, focused tests и state metadata. Он не добавляет raw contracts, raw OCR, user identifiers, credentials, provider configuration, persistence, network behavior или новый privacy boundary.

Repository остаётся pre-production. Production use с real contracts blocked до реализации и проверки applicable consent, authorization, encryption/key lifecycle, Israel-only restricted-data processing, deletion/retention, logging, provider terms, abuse/resource controls и incident response.

## 9. Frozen OCR / Android status

Surya/cloud OCR infrastructure остаётся frozen research и не является current active track.

Tesseract full-page Hebrew OCR на target phone остаётся `NO-GO`.

Historical Android geometry/preprocessing findings deferred и не блокируют Question Engine development.

## 10. Audit continuity

Question Engine batch audit completed on 2026-09-08:

- start SHA: `cbbb8e0905c1fda8610260d4046b51952a9f636c`;
- end SHA: `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`;
- principal PR range: #234–#250;
- outcome: `CORRECTIVE PR REQUIRED`;
- no privacy/security regression reported in audited range.

Owner review accepted: analysis completeness/document identity, minimal answer-state separation, stable identity for repeated smart mechanisms, structured finding resolution, stronger smart-analysis corpus. Universal basic-fact user-facing CORE rejected as product drift.

Question Engine continuity:

- PRs #234–#250 — pivot, research, schema foundation and six smart CORE inventories;
- PR #251 — analysis completeness/document-type gate;
- PR #252 — orthogonal answer-state separation;
- PR #253 — repeatable mechanism identity;
- PR #254 — structured finding resolution;
- PR #255 — smart-analysis evaluation corpus v1.

Ни один из этих PR не доказывает production provider/runtime behavior.

## 11. Recovery/work rules

Перед новым PR:

1. read current binding/state/index documents from `main`;
2. check overlapping open PRs;
3. publish exactly one Context Gate v1;
4. implement only the permitted bounded step;
5. open PR as Draft;
6. update both state files after PR number exists;
7. run final validation on exact final head;
8. compare actual paths with Context Gate;
9. perform mandatory final-diff security review;
10. mark Ready only with `Security review: PASS` and no blocking conflict;
11. merge only under explicit product-owner authorization.

Current owner authorization permits the orchestrating assistant to merge subsequent project PRs after final validation/security review. Auto-merge remains disabled.

Implementation-size rule: target <=300 changed implementation lines per PR; 400 is the normal hard limit.

## 12. PR #255 validation target

Before Ready/merge, PR #255 must verify:

- changed paths exactly match Context Gate;
- branch is based on merged PR #254 / current `main`;
- both state files identify PR #255 and `question-engine-smart-analysis-corpus-v1`;
- next step is `question-engine-security-provider-experiment-v1`;
- corpus contains 12–15 bounded cases with unique IDs;
- all corpus material is synthetic/sanitized and contains no recoverable PII;
- `CONFIRMED`, `NARROWED`, `CLEARED` are all represented;
- template blank and executed blank are separate cases with identical clause text but different lifecycle;
- handwriting case remains unresolved and contains no reconstructed handwriting;
- multiple security instruments preserve distinct mechanism IDs;
- missing dependency, contradiction, distant-clause composition and materially relevant ABSENT behavior are represented;
- no provider/runtime call, statutory runtime, ranking/UI, OCR, storage, network, dependency, permission or workflow change is introduced;
- corpus JSON parses and focused tests pass on exact final head;
- final security review passes on exact final head.
