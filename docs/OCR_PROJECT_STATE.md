# OCR Project State & Continuity v0

Последнее обновление: 2026-09-08, PR #247, `question-engine-core-inventory-financial-sanctions-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-core-inventory-condition-defects-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #247 financial-sanctions inventory

PR #247 расширяет существующий provider-independent Question Engine inventory третьим маленьким pre-signing slice: `financial sanctions and overlap`.

Новый inventory сохраняет отдельными вопросами:

- late-payment additions, при этом principal/rent не смешивается с процентами и индексацией;
- interest rate, period, partial-period rule, indexation formula и accrual timing;
- daily/periodic holdover compensation после договорной даты возврата квартиры;
- fixed agreed damages, привязанные к breach/cancellation или другому явно указанному событию;
- другие явные contractual monetary sanctions, если они не относятся к предыдущим типам;
- возможное наложение нескольких денежных механизмов на один trigger или один stated loss head;
- cumulative/interaction language самого договора.

Inventory намеренно не превращает размеры санкций в судебный прогноз и не кодирует правило `large penalty => court will reduce it`.

PR использует только существующие `QuestionSpec(question_id, domain, purpose, answer_fields)` и `QuestionInventory`. `AnswerState` и schema foundation не меняются.

Никаких conditional trigger runtime, evidence-target layer, statutory/case-law runtime, severity thresholds, provider/LLM integration, UI, OCR, Android, serverless, storage, dependencies, permissions, workflows или network destinations PR #247 не добавляет.

## 2. Canonical next step

`next_step_id = question-engine-core-inventory-condition-defects-v1`

Следующий owner-authorized bounded slice должен покрыть recurring CORE family `condition / AS-IS / defects / damage evidence`.

Минимальный scope следующего PR:

- извлекать entry-condition baseline и наличие AS-IS / inspection acknowledgments;
- различать known/pre-existing defects, ordinary wear и tenant-caused damage по тексту договора;
- фиксировать repair responsibility и связанные notice/repair obligations только как contract facts;
- извлекать return-condition / painting / restoration wording, когда оно определяет будущий damage exposure;
- фиксировать ссылки на condition protocol, defect list, inventory или другое отдельное приложение без угадывания отсутствующего документа;
- не добавлять statutory repair runtime, court-outcome logic, post-dispute evidence questions, provider integration или UI;
- использовать существующую schema foundation без расширения, если отдельное schema-решение не будет явно авторизовано.

Parent sequence `question-engine-question-inventory-v1` остаётся незавершённой.

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

Текущая целевая цепочка:

```text
privacy-validated sanitized contract material
→ deterministic core question inventory
→ LLM structured semantic extraction
→ deterministic conditional follow-ups
→ cross-clause interaction checks
→ bounded novel-issue catch-all
→ Python/schema/evidence/consistency validation
→ statutory comparison where applicable
→ CONFIRMED / NARROWED / CLEARED
→ Safe Output
```

Dispute/practice research нужен для того, чтобы определить, какие pre-signing contract facts действительно важны. Он не превращает основной продукт в адвоката после возникновения спора.

Главные invariants:

- продукт предназначен прежде всего для нормального заключения договора и предотвращения будущих конфликтов;
- ordinary Question Engine содержит только вопросы, ответы на которые materially меняют анализ договора до подписания;
- contract facts, statutory rules, dispute/practice research, Question Engine decisions и product explanation остаются разными слоями;
- два договора могут повысить mechanism family до `CORE`, но не превращают legal/case proposition в production rule;
- cross-clause analysis обязателен;
- candidate finding может быть `CONFIRMED`, `NARROWED` или `CLEARED` после второго прохода;
- handwriting никогда не реконструируется и не угадывается;
- different security instruments остаются семантически различными;
- internal contradictions, blanks, missing references и missing appendices не исправляются молча;
- production output не выдаёт `safe to sign`, не советует подписывать/не подписывать, не прогнозирует исход суда и не даёт категорических enforceability/invalidity выводов без отдельно одобренного deterministic rule.

## 5. Populated inventory status

После PR #247 реализованы три bounded provider-independent inventory slice:

1. `ECONOMIC_CORE_INVENTORY_V1` — monthly-rent baseline + security/enforcement contract facts;
2. `EARLY_EXIT_CORE_INVENTORY_V1` — continuing liability + replacement route + approval standard + assignment/subletting interaction + release consequences;
3. `FINANCIAL_SANCTIONS_CORE_INVENTORY_V1` — late-payment additions + holdover compensation + fixed agreed damages + other explicit sanctions + overlap.

Все используют существующую immutable schema foundation из PR #242 и пока только определяют вопросы. Они не исполняют их против Gemini или другого provider.

Текущие `AnswerState` остаются:

```text
FOUND
NOT_FOUND
AMBIGUOUS
HANDWRITING_DEPENDENCY
CLAUSE_PRESENT_VALUE_BLANK
```

Различие между intentionally blank template field и still-blank field в оформленном/подписанном договоре остаётся отдельным будущим schema-решением и не кодируется неявно.

## 6. Current mechanism classification

`CORE` после cross-contract comparison:

1. security and enforcement;
2. early exit + replacement tenant;
3. financial sanctions and overlap;
4. condition / AS-IS / defects / damage evidence;
5. termination + cure + notice + physical-eviction distinction;
6. option / renewal mechanics.

`CORE_FACTS_CONDITIONAL_PRACTICE`:

- utilities and occupancy charges.

High-value `CONDITIONAL`:

- broad no-setoff;
- shared-meter accounting;
- landlord access;
- alterations/restoration;
- third-party indemnity;
- inventory/handwriting evidence dependency.

`security/enforcement`, `early exit/replacement tenant` и `financial sanctions/overlap` уже получили первые populated inventory slices. Следующий — `condition / AS-IS / defects / damage evidence`.

## 7. Statutory source status

Current statutory authority должен разрешаться из актуального официального законодательства с effective-date logic.

2017 residential-rental reform — Amendment No. 1, effective `2017-09-17`, а не отдельный evergreen statute. Repository snapshot 2017 года является historical engineering snapshot, а не current-law authority сам по себе.

Maintained baseline отдельно предупреждает о 2026 amendment timing для section `25י`; therefore future runtime must version statutory rules by effective date.

Если freshness/applicability/effective date не могут быть безопасно установлены, future runtime должен деградировать к contract-only analysis, а не утверждать устаревшую норму.

PR #247 statutory runtime и правила о судебном уменьшении санкций не добавляет.

## 8. Privacy and security invariants

Restricted material включает original contract photos/pages, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers or images, guarantor identifying data и другую recoverable PII.

Restricted material не должен попадать в GitHub/CI, Airtable, analytics/crash reports, general logs, downstream LLM prompts или unrelated services без отдельно одобренной privacy architecture.

Persistent fixtures/research artifacts должны быть sanitized до commit. Handwriting не угадывается. Monetary amounts, dates, clause numbers, notice periods и legally relevant printed wording не являются PII по умолчанию, когда их можно безопасно отделить от идентификаторов.

PR #247 меняет только static question definitions, focused tests и state metadata. Он не добавляет raw contract material, PII, credentials, provider configuration, persistence, network behavior или новый privacy boundary.

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

Last completed periodic Codex batch audit before Question Engine pivot covered merged PRs #216–#224 and returned `CORRECTIVE PR REQUIRED` with no blocking findings. Worker-contract finding #1 был закрыт PR #225; deferred Android findings остаются вне current track.

Question Engine continuity:

- PRs #239–#241 — docs/state/process consolidation;
- PR #242 — immutable schema foundation + tests;
- PR #243 — Dispute / Practice layer boundary;
- PR #244 — cross-contract mechanism classification;
- PR #245 — first populated economic/security inventory;
- PR #246 — early-exit/replacement-tenant inventory;
- PR #247 — financial-sanctions/overlap inventory.

Ни один из этих PR не доказывает production provider/runtime behavior.

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

## 13. PR #247 validation target

Before Ready, PR #247 must verify:

- changed paths exactly match its Context Gate;
- branch is based on merged PR #246 / current `main`;
- both state files identify PR #247 / `question-engine-core-inventory-financial-sanctions-v1` and select `question-engine-core-inventory-condition-defects-v1` as next bounded step;
- financial-sanctions inventory uses only existing schema foundation;
- late-payment, holdover, fixed agreed damages, other explicit sanctions and overlap remain separate questions;
- late-payment extraction keeps principal reference, interest rate/period, indexation and accrual timing distinct;
- overlap extraction keeps shared trigger, shared loss head, cumulative language and interaction rule distinct;
- no `large penalty => court will reduce` or equivalent court-outcome rule is introduced;
- no post-dispute facts, raw/unsanitized contract material, raw OCR, handwriting reconstruction, party identifiers, exact address, phone/email/ID, signatures, guarantor identifying data, bank/account/check images, credentials or secrets are added;
- no dependency, external API/network destination, workflow, storage, OCR/Android/serverless, LLM/provider or privacy-boundary change is introduced;
- focused Question Engine tests and Python compilation pass on exact final head content;
- final security review passes on exact final head.
