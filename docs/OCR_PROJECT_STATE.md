# OCR Project State & Continuity v0

Последнее обновление: 2026-09-08, PR #250, `question-engine-core-inventory-option-renewal-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-codex-batch-audit-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #250 option / renewal inventory

PR #250 завершает текущую six-family CORE inventory sequence шестым маленьким provider-independent pre-signing slice: `option / renewal mechanics`.

Новый inventory сохраняет отдельными вопросами:

- renewal mechanism, stated right holder и вид механизма без предположения, что любое продление является односторонней опцией;
- необходимость нового landlord consent/approval, если она прямо содержится в договоре;
- renewal duration и start/end mechanics;
- renewal rent amount, formula, increase cap или external economic dependency;
- activation actor, notice requirement, notice form, deadline и notice period;
- prerequisites, включая выполнение действующих обязательств, продление security и требуемые payment instruments;
- addendum/external-writing/reference dependencies и факт присутствия referenced document;
- cross-clause interaction между consent, notice, economics, prerequisites и security-continuity wording.

Missing/blank renewal facts остаются explicit contract facts/dependencies. Их содержание не реконструируется и не угадывается.

PR использует только существующие `QuestionSpec(question_id, domain, purpose, answer_fields)` и `QuestionInventory`. `AnswerState` и schema foundation не меняются.

Никаких conditional trigger runtime, evidence-target layer, statutory/case-law runtime, option-enforceability interpretation, court-outcome logic, post-dispute mode, provider/LLM integration, UI, OCR, Android, serverless, storage, dependencies, permissions, workflows или network destinations PR #250 не добавляет.

## 2. Canonical next step

`next_step_id = question-engine-codex-batch-audit-v1`

Все шесть текущих `CORE` inventory families теперь имеют populated provider-independent slices. До начала следующего implementation layer нужно провести owner-requested большой periodic Codex batch audit накопившегося Question Engine диапазона.

Audit должен следовать `docs/CODEX_WORKFLOW.md`. Минимальный scope:

- инспектировать накопившийся Question Engine pivot range, ориентировочно merged PRs #234–#250, и зафиксировать точные start/end SHA;
- перечитать binding/state documents на audit end SHA;
- проверить cross-PR integration, schema/inventory drift, duplicated or contradictory questions, stale tests и state continuity;
- проверить privacy/security regressions, restricted material/PII, credentials, dependencies, workflows, network/provider claims и unsupported runtime claims;
- запустить доступные focused/full tests и указать только реально выполненные проверки;
- сгруппировать findings как blocking, corrective или observation;
- явно указать, что остаётся unverified;
- выдать один outcome: `BATCH AUDIT CLEAR`, `CORRECTIVE PR REQUIRED` или `FREEZE AFFECTED AREA`;
- любые исправления после аудита оформлять отдельными bounded corrective PR.

Codex audit ещё не запущен. Следующий implementation layer не выбирается до результата этого checkpoint.

Parent sequence `question-engine-question-inventory-v1` имеет полное текущее CORE inventory coverage, но остаётся operationally незавершённой до batch audit и решения по следующему слою.

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

После PR #250 реализованы все шесть текущих bounded provider-independent `CORE` inventory slices:

1. `ECONOMIC_CORE_INVENTORY_V1` — monthly-rent baseline + security/enforcement contract facts;
2. `EARLY_EXIT_CORE_INVENTORY_V1` — continuing liability + replacement route + approval standard + assignment/subletting interaction + release consequences;
3. `FINANCIAL_SANCTIONS_CORE_INVENTORY_V1` — late-payment additions + holdover compensation + fixed agreed damages + other explicit sanctions + overlap;
4. `CONDITION_DEFECTS_CORE_INVENTORY_V1` — entry baseline + AS-IS/inspection + pre-existing defects + damage/wear allocation + repair mechanics + return condition + referenced evidence documents;
5. `TERMINATION_CURE_CORE_INVENTORY_V1` — breach triggers + fundamental-breach classification + notice/cure + cancellation + contractual vacancy demand + cross-clause interaction;
6. `OPTION_RENEWAL_CORE_INVENTORY_V1` — renewal right structure + period + economics + activation + prerequisites + external dependencies + cross-clause interaction.

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

Все шесть текущих `CORE` families получили populated inventory slices. Следующий шаг — не расширение taxonomy и не новый runtime, а batch audit накопившегося Question Engine слоя.

## 7. Statutory source status

Current statutory authority должен разрешаться из актуального официального законодательства с effective-date logic.

2017 residential-rental reform — Amendment No. 1, effective `2017-09-17`, а не отдельный evergreen statute. Repository snapshot 2017 года является historical engineering snapshot, а не current-law authority сам по себе.

Maintained baseline отдельно предупреждает о 2026 amendment timing для section `25י`; therefore future runtime must version statutory rules by effective date.

Если freshness/applicability/effective date не могут быть безопасно установлены, future runtime должен деградировать к contract-only analysis, а не утверждать устаревшую норму.

PR #250 statutory/case-law runtime, option-enforceability conclusions и court-outcome logic не добавляет.

## 8. Privacy and security invariants

Restricted material включает original contract photos/pages, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers or images, guarantor identifying data и другую recoverable PII.

Restricted material не должен попадать в GitHub/CI, Airtable, analytics/crash reports, general logs, downstream LLM prompts или unrelated services без отдельно одобренной privacy architecture.

Persistent fixtures/research artifacts должны быть sanitized до commit. Handwriting не угадывается. Monetary amounts, dates, clause numbers, notice periods и legally relevant printed wording не являются PII по умолчанию, когда их можно безопасно отделить от идентификаторов.

PR #250 меняет только static question definitions, focused tests и state metadata. Он не добавляет raw contract material, PII, credentials, provider configuration, persistence, network behavior или новый privacy boundary.

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

- PRs #234–#235 — active-track pivot / freeze of OCR infrastructure;
- PR #236 — first sanitized golden contract;
- PRs #237–#238 — Question Engine discovery and statutory/template discoveries;
- PRs #239–#241 — docs/state/process consolidation;
- PR #242 — immutable schema foundation + tests;
- PR #243 — Dispute / Practice layer boundary;
- PR #244 — cross-contract mechanism classification;
- PR #245 — first populated economic/security inventory;
- PR #246 — early-exit/replacement-tenant inventory;
- PR #247 — financial-sanctions/overlap inventory;
- PR #248 — condition/AS-IS/defects/damage-evidence inventory;
- PR #249 — termination/cure/notice/vacancy inventory;
- PR #250 — option/renewal inventory and completion of current six-family CORE inventory coverage.

Owner-requested audit checkpoint is now canonical next step: после merge PR #250 провести большой periodic Codex batch audit accumulated Question Engine pivot range before beginning the next implementation layer. Exact audit start/end SHA must be recorded by the audit itself; PR range target is #234–#250 unless end-state inspection identifies a more precise boundary under `docs/CODEX_WORKFLOW.md`.

Codex audit has not yet been invoked. Ни один из перечисленных Question Engine PR не доказывает production provider/runtime behavior.

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

## 13. PR #250 validation target

Before Ready, PR #250 must verify:

- changed paths exactly match its Context Gate;
- branch is based on merged PR #249 / current `main`;
- both state files identify PR #250 / `question-engine-core-inventory-option-renewal-v1` and select `question-engine-codex-batch-audit-v1` as next bounded step;
- option/renewal inventory uses only existing schema foundation;
- renewal right structure, period, economics, activation, prerequisites, external dependencies and cross-clause interaction remain separate questions;
- landlord consent is represented as a contract fact rather than silently converting any renewal wording into a unilateral option;
- missing/blank renewal facts and referenced documents remain explicit dependencies without inferred contents;
- no statutory/case-law rule, option-enforceability conclusion, court-outcome rule, post-dispute question or provider/runtime behavior is introduced;
- no raw/unsanitized contract material, raw OCR, handwriting reconstruction, party identifiers, exact address, phone/email/ID, signatures, guarantor identifying data, bank/account/check images, credentials or secrets are added;
- no dependency, external API/network destination, workflow, storage, OCR/Android/serverless, LLM/provider or privacy-boundary change is introduced;
- focused Question Engine tests and Python compilation pass on exact final head content;
- final security review passes on exact final head.
