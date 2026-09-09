# OCR Project State & Continuity v0

Последнее обновление: 2026-09-09, PR #253, `question-engine-repeatable-mechanism-identity-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-finding-resolution-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #253 repeatable mechanism identity

Owner-requested Codex batch audit диапазона `cbbb8e0905c1fda8610260d4046b51952a9f636c` → `ee66e0063e270abd5eb7992f2be73c89dbec3a5d` завершён с итогом `CORRECTIVE PR REQUIRED`.

После product-owner review audit findings были сужены. Сохраняется ключевая продуктовая коррекция:

- продукт не должен становиться универсальным пересказчиком договора;
- очевидные пользователю facts не становятся пользовательским `CORE` только потому, что они присутствуют в договоре;
- простой fact извлекается как support/dependency input только когда materially нужен для более глубокого анализа, deterministic calculation, statutory gate или cross-clause resolution;
- обнаруженное формальное несоответствие не обязано становиться finding, если оно не меняет существенный механизм для пользователя.

PR #251 добавил provider-independent `analysis completeness` gate: unrelated/unconfirmed document type блокируется fail-closed; отсутствующие analysis-relevant дополнительные документы делают только зависимые области `PARTIAL`.

PR #252 разделил перегруженный answer state на независимые оси:

- `PresenceStatus`;
- `ValueStatus`;
- `EvidenceStatus`;
- `SourceStatus`;
- `DocumentLifecycle`.

PR #253 реализует третий accepted corrective slice: стабильную локальную identity/cardinality для повторяющихся smart mechanisms.

Минимальный reusable contract:

```text
MechanismCollection
  domain
  mechanisms[]
  cardinality

MechanismInstance
  mechanism_id
  mechanism_type
  properties[]

MechanismProperty
  name
  value
  state: AnswerState
```

Главный semantic effect:

- несколько security instruments больше не должны представляться только как независимые parallel arrays;
- amount, blank state, payee, trigger, return mechanics и другие properties могут быть привязаны к конкретному `mechanism_id`;
- IDs уникальны внутри `MechanismCollection`;
- property names уникальны внутри одного instance;
- identity-only instance разрешён для первого inventory pass, до заполнения properties;
- typed values, evidence refs и provider output contract в этом PR намеренно не добавляются.

Security используется как stress-test family, но schema остаётся reusable для других repeatable smart mechanisms. Существующие six smart inventories в PR #253 массово не мигрируются.

PR #253 не добавляет provider/runtime integration, statutory runtime, finding resolution, ranking/UI, OCR, Android, serverless, storage, network destinations, dependencies, permissions или workflows.

## 2. Canonical next step

`next_step_id = question-engine-finding-resolution-v1`

Следующий bounded corrective slice должен превратить архитектурный принцип `CONFIRMED / NARROWED / CLEARED` в минимальный structured result contract.

Минимальный scope следующего PR:

- представить candidate finding отдельно от результата second-pass review;
- разрешить три outcomes: `CONFIRMED`, `NARROWED`, `CLEARED`;
- сохранить ссылки на то, какие related mechanism facts/clauses изменили исход кандидата, без universal relation graph;
- не считать найденную пугающую фразу автоматически финальным finding;
- не добавлять provider runtime, statutory runtime, ranking/UI, OCR или инфраструктуру;
- не строить широкую remediation/legal ontology.

Дальнейшая accepted corrective sequence после этого шага:

1. smart-analysis corpus с различными способами выражения/маскировки одного механизма;
2. первый bounded contract-fact provider experiment.

## 3. Required reading order

Перед следующим PR читать с актуального `main`:

1. `AGENTS.md`;
2. `SECURITY.md`;
3. `docs/ARCHITECTURE.md`;
4. `docs/CUSTOM_OCR_PIPELINE.md`;
5. `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`;
6. `docs/OCR_PROJECT_STATE.md`;
7. `docs/OCR_PROJECT_STATE.json`;
8. `docs/DOCUMENT_STATUS_INDEX.md`;
9. `docs/CODEX_WORKFLOW.md`.

Question Engine task context, когда применимо:

- `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`;
- `docs/QUESTION_ENGINE_DISPUTE_PRACTICE_LAYER_V0.md`;
- `docs/QUESTION_ENGINE_DISPUTE_PRACTICE_CLASSIFICATION_V1.md`;
- `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md`;
- `docs/statutory/README.md` и versioned snapshots, когда statutory comparison входит в scope;
- `research/question_engine/golden_contracts/contract_001_he.txt`;
- `research/question_engine/golden_contracts/contract_001.meta.json`.

Research-only dispute/practice JSON artifacts не являются authority и не могут переопределять verified contract evidence, current law, binding docs или canonical state.

## 4. Current Question Engine architecture

Текущая целевая цепочка после accepted audit corrections:

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
→ CONFIRMED / NARROWED / CLEARED
→ materiality / suppression
→ Safe Output
```

Главные invariants:

- продукт предназначен прежде всего для нормального заключения договора и предотвращения будущих конфликтов;
- Question Engine не обязан извлекать или показывать банальный fact, если он не нужен для более глубокого анализа;
- ordinary Question Engine содержит только вопросы, ответы на которые materially меняют анализ договора до подписания;
- обнаруженность механизма или inconsistency сама по себе не является основанием показывать её пользователю;
- contract facts, statutory rules, dispute/practice research, Question Engine decisions и product explanation остаются разными слоями;
- cross-clause analysis обязателен;
- candidate finding может быть `CONFIRMED`, `NARROWED` или `CLEARED` после второго прохода;
- handwriting никогда не реконструируется и не угадывается;
- different security instruments остаются семантически различными;
- internal contradictions, blanks, missing references и missing appendices не исправляются молча;
- incomplete package должен сужать только те выводы, которым не хватает evidence, когда остальной анализ безопасно возможен;
- production output не выдаёт `safe to sign`, не советует подписывать/не подписывать, не прогнозирует исход суда и не даёт категорических enforceability/invalidity выводов без отдельно одобренного deterministic rule.

## 5. Current schema and inventories

После PR #250 реализованы шесть provider-independent smart `CORE` inventory slices:

1. `ECONOMIC_CORE_INVENTORY_V1` — monthly-rent baseline only as useful dependency + security/enforcement facts;
2. `EARLY_EXIT_CORE_INVENTORY_V1` — continuing liability + replacement route + approval standard + assignment/subletting interaction + release consequences;
3. `FINANCIAL_SANCTIONS_CORE_INVENTORY_V1` — late-payment additions + holdover compensation + fixed agreed damages + other explicit sanctions + overlap;
4. `CONDITION_DEFECTS_CORE_INVENTORY_V1` — entry baseline + AS-IS/inspection + pre-existing defects + damage/wear allocation + repair mechanics + return condition + referenced evidence documents;
5. `TERMINATION_CURE_CORE_INVENTORY_V1` — breach triggers + fundamental-breach classification + notice/cure + cancellation + contractual vacancy demand + cross-clause interaction;
6. `OPTION_RENEWAL_CORE_INVENTORY_V1` — renewal right structure + period + economics + activation + prerequisites + external dependencies + cross-clause interaction.

PR #251 добавляет gate перед этими inventories.

Текущий answer-state contract после PR #252:

```text
AnswerState
  presence: PresenceStatus
  value: ValueStatus
  evidence: EvidenceStatus
  source: SourceStatus
  lifecycle: DocumentLifecycle
```

Repeatable-mechanism contract после PR #253:

```text
MechanismCollection(domain, mechanisms)
MechanismInstance(mechanism_id, mechanism_type, properties)
MechanismProperty(name, value, state)
```

`QuestionSpec(question_id, domain, purpose, answer_fields)` и `QuestionInventory` остаются прежними. Existing inventories ещё являются static question definitions; provider execution отсутствует.

Model confidence, applicability, provenance, deterministic evidence refs и typed values пока не входят в bounded schema.

## 6. Current mechanism classification

Текущий smart `CORE` сохраняется после owner review batch audit:

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

Batch-audit proposal to promote a universal basic `parties/term/rent schedule/notices` skeleton into user-facing CORE был explicitly rejected by the product owner. Такие facts остаются analysis-support inputs, когда smart mechanism действительно в них нуждается.

## 7. Statutory source status

Current statutory authority должен разрешаться из актуального официального законодательства с effective-date logic.

2017 residential-rental reform — Amendment No. 1, effective `2017-09-17`, а не отдельный evergreen statute. Repository snapshot 2017 года является historical engineering snapshot, а не current-law authority сам по себе.

Maintained baseline отдельно предупреждает о 2026 amendment timing для section `25י`; future runtime должен version statutory rules by effective date.

Если freshness/applicability/effective date не могут быть безопасно установлены, future runtime должен деградировать к contract-only analysis, а не утверждать устаревшую норму.

PR #253 statutory runtime или current-law claims не добавляет.

## 8. Privacy and security invariants

Restricted material включает original contract photos/pages, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers or images, guarantor identifying data и другую recoverable PII.

Restricted material не должен попадать в GitHub/CI, Airtable, analytics/crash reports, general logs, downstream LLM prompts или unrelated services без отдельно одобренной privacy architecture.

Persistent fixtures/research artifacts должны быть sanitized до commit. Handwriting не угадывается. Monetary amounts, dates, clause numbers, notice periods и legally relevant printed wording не являются PII по умолчанию, когда их можно безопасно отделить от идентификаторов.

PR #253 меняет только provider-independent standard-library schema, focused tests и state metadata. Он не добавляет raw contract material, PII, credentials, provider configuration, persistence, network behavior или новый privacy boundary.

Repository остаётся pre-production. Production use с real contracts остаётся blocked до реализации и проверки applicable consent, authorization, encryption/key lifecycle, Israel-only restricted-data processing, deletion/retention, logging, provider terms, abuse/resource controls и incident response.

## 9. Frozen OCR / Android status

Surya/cloud OCR infrastructure остаётся frozen research и не является текущим active track.

Targeted-region CPU attempt после PR #233 остановился на Cloud Build `PERMISSION_DENIED` до build/OCR execution; это не является доказательством плохой CPU latency/quality Surya.

Tesseract full-page Hebrew OCR на target phone остаётся `NO-GO`.

Historical Android geometry/preprocessing findings deferred и не блокируют Question Engine development.

## 10. Document authority continuity

`docs/DOCUMENT_STATUS_INDEX.md` остаётся картой authority классов.

Binding/current governance, current Question Engine context, research-only artifacts, frozen/deferred OCR references и historical UX/workflow documents сохраняют ранее установленный статус. Historical/component/research-only files не могут переопределять canonical state или verified sources.

## 11. Audit continuity

Previous periodic Codex batch audit before Question Engine pivot covered merged PRs #216–#224 and returned `CORRECTIVE PR REQUIRED` with no blocking findings. Worker-contract finding #1 был закрыт PR #225; deferred Android findings остаются вне current track.

Question Engine batch audit completed on 2026-09-08:

- start SHA: `cbbb8e0905c1fda8610260d4046b51952a9f636c`;
- end SHA: `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`;
- principal PR range: #234–#250;
- outcome: `CORRECTIVE PR REQUIRED`;
- no privacy/security regression was reported in the audited range;
- reported focused Question Engine tests: 50/50 PASS;
- reported broader suite after one Windows symlink-privilege exclusion: 594/594 PASS, 3 skips;
- provider runtime, production OCR/privacy behavior and exact current-law consolidated wording remained unverified.

Owner review accepted: analysis completeness/document identity, minimal answer-state separation, stable identity for repeated smart mechanisms, structured finding resolution, and stronger smart-analysis corpus. The proposal to build a comprehensive basic-fact user-facing CORE was rejected as product drift toward a generic lease parser.

Question Engine continuity:

- PRs #234–#235 — active-track pivot / freeze of OCR infrastructure;
- PR #236 — first sanitized golden contract;
- PRs #237–#238 — Question Engine discovery and statutory/template discoveries;
- PRs #239–#241 — docs/state/process consolidation;
- PR #242 — initial schema foundation + tests;
- PR #243 — Dispute / Practice layer boundary;
- PR #244 — cross-contract mechanism classification;
- PR #245 — economic/security inventory;
- PR #246 — early-exit/replacement-tenant inventory;
- PR #247 — financial-sanctions/overlap inventory;
- PR #248 — condition/AS-IS/defects/damage-evidence inventory;
- PR #249 — termination/cure/notice/vacancy inventory;
- PR #250 — option/renewal inventory and completion of current six-family CORE coverage;
- PR #251 — analysis completeness/document-type gate;
- PR #252 — minimal orthogonal answer-state separation;
- PR #253 — stable local identity/cardinality for repeatable smart mechanisms.

Ни один из перечисленных Question Engine PR не доказывает production provider/runtime behavior.

## 12. Recovery/work rules

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
11. leave merge/auto-merge to explicit product-owner decision.

Implementation-size rule remains binding: target no more than 300 changed implementation lines per PR and treat 400 as the normal hard limit.

## 13. PR #253 validation target

Before Ready, PR #253 must verify:

- changed paths exactly match its Context Gate;
- branch is based on merged PR #252 / current `main`;
- both state files identify PR #253 / `question-engine-repeatable-mechanism-identity-v1` and select `question-engine-finding-resolution-v1` as next bounded step;
- repeatable mechanisms have unique collection-local `mechanism_id` values;
- each mechanism keeps its own `mechanism_type` and properties together;
- each property keeps its own `AnswerState`;
- duplicate mechanism IDs and duplicate property names are rejected;
- an identity-only first-pass mechanism instance is allowed;
- a security stress test proves that amount/blank/return values for two instruments do not collapse into parallel arrays or drift between instances;
- existing `AnswerState`, `QuestionSpec`, and `QuestionInventory` behavior remains intact;
- existing inventories are not mass-migrated in this PR;
- no provider/runtime integration, finding-resolution logic, statutory runtime, ranking/UI, OCR, storage, network, dependency, permission or workflow change is introduced;
- no raw/unsanitized contract material, raw OCR, handwriting reconstruction, party identifiers, exact address, phone/email/ID, signatures, guarantor identifying data, bank/account/check images, credentials or secrets are added;
- focused tests and Python compilation pass on exact final head content;
- final security review passes on exact final head.
