# OCR Project State & Continuity v0

Последнее обновление: 2026-09-09, PR #256, `question-engine-smart-analysis-corpus-oracle-v2`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-security-provider-experiment-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #256 smart-analysis corpus oracle v2

Ключевая продуктовая рамка не меняется:

- приложение не является универсальным пересказчиком договора;
- пользователь считается способным самостоятельно понять очевидные факты вроде своей роли, обычной суммы аренды и явных дат;
- простой fact извлекается только если он нужен как input для более глубокого smart-analysis вывода, расчёта, statutory gate или cross-clause resolution;
- найденная странность не обязана становиться user-facing finding, если она не меняет существенный механизм;
- ценность продукта — замечать неочевидные связи, рисковые механизмы, missing evidence и практические последствия, которые легко пропустить при обычном чтении.

После PR #255 был проведён узкий semantic audit только качества `smart_analysis_corpus_v1.json`. Аудит не требовал расширять продукт до полного парсера; наоборот, он подтвердил selective-intelligence подход, но выявил, что corpus v1 слишком легко проходится поверхностным matcher и местами имеет слишком грубый oracle.

PR #256 — owner-authorized bounded corrective exception перед первым provider experiment.

Главные исправления:

- единый global expected state заменён на sparse assertions, привязанные к конкретным `question_id`, при необходимости `mechanism_id` и конкретному answer field;
- oracle теперь проверяет фактическое содержание: instrument type, amount, blank field, notice/cure, trigger, return deadline, overlap relationship и другие только реально нужные tested values;
- `CONFIRMED / NARROWED / CLEARED` всегда относится к явно заданному candidate claim, а не к case name;
- package completeness, missing documents и handwriting/redaction signals вынесены из Hebrew clauses в structured corpus metadata;
- `ABSENT` допустим только если case явно объявляет полный relevant search scope для этого question;
- исправлен ранний exit case: continuing liability теперь `PRESENT`, а replacement route отдельно `ABSENT` только при complete scope;
- прежний псевдо-conflict двух party roles заменён на настоящий mutually exclusive completion-authority conflict;
- linking cases содержат distractors, поэтому стратегия «вернуть все refs» больше не должна проходить;
- multi-instrument cases проверяют, что суммы, blank states, notice rules и return rules не мигрируют между security instruments;
- добавлен scoped case, где notice применяется к одному security instrument, но не к другому;
- добавлен cumulative recovery-overlap case для rent cheque + security cheque;
- добавлен case, где referenced security document присутствует, но ожидаемая сумма в нём отсутствует.

Artifact сохраняет историческое имя `research/question_engine/smart_analysis_corpus_v1.json`, но его внутренний `schema_version` теперь `2`. Это corpus oracle v2, не новый production schema.

Corpus содержит 16 bounded synthetic/sanitized cases. Это evaluation oracle, не training data и не generic full-contract dataset.

PR #256 не добавляет provider/runtime calls, statutory runtime, OCR, Android, serverless, storage, network destinations, dependencies, permissions, workflows, ranking/UI или broad full-contract parser.

## 2. Canonical next step

`next_step_id = question-engine-security-provider-experiment-v1`

Следующий bounded-шаг — первый реальный provider experiment, ограниченный security family и только sanitized/synthetic corpus material.

Цель эксперимента — проверить, может ли модель стабильно:

- различать несколько security instruments и сохранять их identity;
- извлекать только нужные tested values без смешивания между instruments;
- правильно различать blank, missing dependency и handwriting dependency;
- связывать distant clauses и игнорировать distractors;
- понимать, к какому instrument относится notice/cure/return rule;
- распознавать cumulative recovery overlap;
- создавать candidate concern отдельно от second-pass `CONFIRMED / NARROWED / CLEARED` result;
- не выдумывать missing document contents или handwritten values.

Эксперимент должен дать реальные failure modes. Только после него решается, нужны ли изменения LLM↔Python contract. Не проектировать дополнительные fields, confidence, typed-value framework или broad ontology заранее без provider evidence.

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

Research-only artifacts не являются authority и не могут переопределять verified contract evidence, current law, binding docs или canonical state.

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

- продукт ориентирован прежде всего на нормальное заключение договора и предотвращение будущих конфликтов;
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

После PR #250 реализованы шесть provider-independent smart `CORE` families:

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

Corpus oracle v2 является evaluation representation, а не production runtime schema. Он намеренно sparse и описывает только assertions, нужные конкретному testcase.

Model confidence, statutory applicability result, production deterministic evidence refs, provenance graph и universal typed monetary/date framework пока не входят в bounded runtime schema.

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

PR #256 statutory runtime/current-law claims не добавляет.

## 8. Privacy and security invariants

Restricted material включает original contract photos/pages, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers or images, guarantor identifying data и другую recoverable PII.

Restricted material не должен попадать в GitHub/CI, analytics/crash reports, general logs, downstream LLM prompts или unrelated services без отдельно одобренной privacy architecture.

Persistent fixtures/research artifacts должны быть sanitized до commit. Handwriting не угадывается. Monetary amounts, dates, clause numbers, notice periods и legally relevant printed wording не являются PII по умолчанию, когда безопасно отделены от identifiers.

PR #256 содержит только synthetic/sanitized Hebrew clauses, structured synthetic package/redaction metadata, expected semantic assertions, focused tests и state metadata. Он не добавляет raw contracts, raw OCR, user identifiers, credentials, provider configuration, persistence, network behavior или новый privacy boundary.

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
- PR #255 — smart-analysis evaluation corpus v1;
- PR #256 — corpus oracle v2 semantic correction after narrow corpus audit.

The narrow post-#255 corpus audit found no reason to broaden the product into generic lease parsing. Its actionable result was to make the evaluation oracle harder and more semantically precise before the provider experiment.

Ни один из этих PR не доказывает production provider/runtime behavior.

## 11. Recovery/work rules

Перед новым PR:

1. read current binding/state/index documents from `main`;
2. check overlapping open PRs;
3. publish exactly one Context Gate v1;
4. implement only the permitted bounded step or explicit owner-authorized bounded exception;
5. open PR as Draft;
6. update both state files after PR number exists;
7. run final validation on exact final head;
8. compare actual paths with Context Gate;
9. perform mandatory final-diff security review;
10. mark Ready only with `Security review: PASS` and no blocking conflict;
11. merge only under explicit product-owner authorization.

Current owner authorization permits the orchestrating assistant to merge subsequent project PRs after final validation/security review. Auto-merge remains disabled.

Implementation-size rule: target <=300 changed implementation lines per PR; 400 is the normal hard limit. Corpus fixture data is not implementation code, but test/implementation code should remain bounded.

## 12. PR #256 validation target

Before Ready/merge, PR #256 must verify:

- changed paths exactly match Context Gate;
- branch is based on merged PR #255 / current `main`;
- both state files identify PR #256 and `question-engine-smart-analysis-corpus-oracle-v2`;
- next step remains `question-engine-security-provider-experiment-v1`;
- corpus JSON parses with `schema_version = 2`;
- every assertion targets an existing current `QuestionSpec` and valid answer field in the same domain;
- omitted state axes inherit explicit corpus defaults and all effective states use current enum values;
- `ABSENT` assertions require declared complete scope;
- every resolution has an explicit candidate claim and valid source refs;
- package/handwriting signals are structured outside Hebrew clauses;
- template blank and executed blank remain a controlled pair;
- multiple security instruments preserve distinct amounts/blanks/notice/return properties;
- linking stress case contains distractors and does not reward returning every input ref;
- corrected early-exit and true contradiction cases are represented;
- security recovery overlap and present-but-incomplete referenced document cases are represented;
- all corpus material is synthetic/sanitized and contains no recoverable PII;
- no provider/runtime call, statutory runtime, ranking/UI, OCR, storage, network, dependency, permission or workflow change is introduced;
- corpus JSON, focused tests and Python compilation pass on exact final head;
- final security review passes on exact final head.
