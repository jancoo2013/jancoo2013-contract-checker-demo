# OCR Project State & Continuity v0

Последнее обновление: 2026-09-07, PR #244, `question-engine-cross-contract-practice-classification-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-core-inventory-economic-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #244 cross-contract dispute/practice classification

PR #244 — bounded documentation/research update after the second full dispute/practice pass over an independent sanitized residential lease.

Он не меняет runtime, schema foundation или canonical implementation order. Он фиксирует результат сравнения первых двух договоров:

- `docs/QUESTION_ENGINE_DISPUTE_PRACTICE_CLASSIFICATION_V1.md` классифицирует recurring product mechanism families как `CORE`, `CONDITIONAL`, `CORE_FACTS_CONDITIONAL_PRACTICE` или `RESEARCH_ONLY`;
- `CORE` означает только устойчивый продуктовый механизм после двух независимых договоров, а не подтверждённую законность/незаконность, enforceability или прогноз суда;
- recurring CORE: security/enforcement, early exit + replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/damage evidence, termination/cure/notice/physical-eviction distinction, option/renewal mechanics;
- utilities/occupancy charges — `CORE_FACTS_CONDITIONAL_PRACTICE`: fact extraction постоянен, deeper practice включается только при специальной механике;
- high-value conditional: broad no-setoff, shared-meter accounting, landlord access, alterations/restoration, third-party indemnity, inventory/handwriting dependencies;
- `research/question_engine/dispute_practice/cross_contract_mechanism_matrix_v1.json` хранит sanitized machine-readable comparison only and explicitly не является legal authority;
- обычный pre-signing Question Engine остаётся минимальным: post-dispute вопросы не продвигаются только потому, что они важны в судебном споре;
- future contracts теперь должны использоваться primarily как coverage test существующей taxonomy и источник genuinely new families, а не начинать классификацию с нуля.

PR #244 не добавляет raw contract material, raw OCR, user identifiers, signatures, guarantor identifying data, bank/account/check images, dependencies, provider/API integration, network destination, workflow logic, storage, OCR/Android/serverless work или case-law runtime.

## 2. Canonical next step

`next_step_id = question-engine-core-inventory-economic-v1`

Следующий owner-authorized bounded implementation остаётся прежним и должен использовать merged schema foundation PR #242.

Scope следующего slice:

- определить первый маленький набор deterministic recurring economic questions;
- для каждого вопроса задать только `question_id`, `domain`, `purpose`, `answer_fields`;
- сохранить states `FOUND`, `NOT_FOUND`, `AMBIGUOUS`, `HANDWRITING_DEPENDENCY`, `CLAUSE_PRESENT_VALUE_BLANK`;
- сохранить contract-defined party-role granularity;
- использовать существующий sanitized golden contract как fixture;
- учитывать dispute/practice classification only to keep the inventory aligned with confirmed mechanism families;
- не реализовывать conditional triggers, evidence-target layer, statutory/remediation runtime, dispute-practice runtime, live case-law research, UI или Hebrew remediation subsystem;
- не добавлять production LLM/provider integration без отдельного разрешения;
- не reopening OCR/Android/serverless infrastructure.

Следующий inventory slice должен оставаться маленьким и independently testable.

## 3. Required pre-Codex reading order

Codex/executor читает текущие файлы с base branch, а не prompt history.

Always-read governance:

1. `AGENTS.md`;
2. `SECURITY.md`;
3. `docs/ARCHITECTURE.md`;
4. `docs/CUSTOM_OCR_PIPELINE.md`;
5. `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`;
6. `docs/OCR_PROJECT_STATE.md`;
7. `docs/OCR_PROJECT_STATE.json`;
8. `docs/DOCUMENT_STATUS_INDEX.md`;
9. `docs/CODEX_WORKFLOW.md`.

Task-specific for `question-engine-core-inventory-economic-v1`:

- `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`;
- `docs/QUESTION_ENGINE_DISPUTE_PRACTICE_LAYER_V0.md` for the responsibility boundary;
- `docs/QUESTION_ENGINE_DISPUTE_PRACTICE_CLASSIFICATION_V1.md` for current cross-contract mechanism classification;
- `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md` for reserved statutory boundaries/terminology only;
- `docs/statutory/README.md` and current snapshots only where needed for schema-boundary coherence;
- `research/question_engine/golden_contracts/contract_001_he.txt`;
- `research/question_engine/golden_contracts/contract_001.meta.json`.

Research-only dispute/practice JSON artifacts are not authority or mandatory runtime input. If task-specific sources conflict with binding/current rules, implementation stops and reports the conflict.

## 4. Current Question Engine decisions

Merged PR #239 consolidated product/UX discovery. PR #242 added only immutable schema foundation. PR #243 reserved the Dispute / Practice layer boundary. PR #244 adds the first cross-contract mechanism classification.

Key invariants:

- deterministic core inventory + LLM semantic reader + conditional follow-ups + cross-clause checks + bounded catch-all + Python/schema/evidence validation;
- candidate findings may become `CONFIRMED`, `NARROWED`, or `CLEARED` after second pass;
- handwriting is never semantically guessed or reconstructed;
- role granularity follows operative contract text;
- different security instruments remain distinct;
- security analysis separates instrument mechanics, completion/realization authority, underlying debt/amount, and execution/opposition procedure;
- contract facts, statutory rules, dispute/practice research, Question Engine decisions, and product explanation remain separate layers;
- two-contract recurrence can promote a product mechanism family, never a legal proposition by itself;
- model-assisted or secondary-source case/practice research is not authority until source and proposition are independently verified;
- ordinary pre-signing Question Engine asks only questions whose answers materially change analysis now;
- post-dispute questions such as execution warning, later key return, actual re-letting, lawsuit filing, or post-move-out damage remain outside ordinary pre-signing inventory;
- user-facing output ranks mechanisms instead of giving every clause equal visual weight;
- case names, court citations, procedural detail and deep evidence patterns remain internal by default;
- statutory discussion is blocked until applicability/effective-date/non-derogation checks pass;
- production Russian avoids words built from `юрист-` / `юрид-`; internal English legal identifiers must not leak into rendered Russian copy;
- product does not issue `safe to sign`, predict dispute outcomes, instruct suit/refusal-to-pay/sign/not-sign, or present generated wording as uniquely correct.

Current UX hierarchy remains: Screen 1 orientation, Screen 2 Russian essay analysis, Screen 3 Russian discussion/action plan. Hebrew discussion text remains optional/on-demand.

## 5. Current mechanism classification

`CORE` product mechanism families after two contracts:

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

Detailed definitions and promotion boundaries live in `docs/QUESTION_ENGINE_DISPUTE_PRACTICE_CLASSIFICATION_V1.md`.

## 6. Statutory source status

Current statutory authority must be resolved from the current official legislation source with effective-date logic.

The 2017 residential-rental reform is Amendment No. 1, effective `2017-09-17`, not a separate evergreen law.

Merged PR #240 added:

- `docs/statutory/README.md` — source hierarchy/versioning rules;
- `docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2017_V1.json` — immutable normalized historical 2017 snapshot.

The historical snapshot is not current-law authority by itself. Later amendments/overlays must be resolved by effective date. If required statutory freshness cannot be verified, future runtime must degrade to contract-only analysis rather than assert stale law.

Neither current inventory work nor PR #244 implements full statutory or dispute-practice runtime.

## 7. Privacy and data-handling invariants

Restricted material includes original contract photos/pages, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers/images, guarantor identifying data, and other recoverable PII.

Restricted material must not enter GitHub/CI, Airtable, analytics/crash reports, general logs, downstream LLM prompts, or unrelated services unless an explicitly approved privacy architecture says otherwise.

Persistent fixtures/research artifacts must be sanitized before commit.

Handwriting must not be semantically reconstructed or guessed. If a result depends on handwriting, return an explicit unresolved dependency.

Monetary amounts, dates, clause numbers, notice periods, and legally relevant printed wording are not PII by default when safely separable from identifying data.

PR #244 adds only a generalized comparison matrix and classification document; it includes no raw images/OCR or identifying source-contract details.

## 8. Production security status

Repository remains pre-production.

Production use with real contracts remains blocked pending implementation/verification of applicable controls including:

- user consent for any remote raw-processing path;
- authentication/account-scoped authorization;
- encryption/key lifecycle;
- Israel-only provider/runtime behavior for restricted material;
- retention, cleanup, deletion and backup-expiry guarantees;
- log/analytics scrubbing;
- provider terms/subprocessors;
- abuse/resource controls and incident response.

Question Engine documentation/research changes none of these production gates.

## 9. Frozen OCR/Android status

Surya/cloud OCR infrastructure remains frozen research, not active implementation.

The targeted-region CPU attempt after PR #233 stopped at Cloud Build `PERMISSION_DENIED` before container build/OCR execution. There is no measured CPU latency/quality result and no evidence that Surya CPU itself failed.

Tesseract full-page Hebrew OCR on the target phone remains `NO-GO`.

Historical Android geometry/preprocessing remains frozen/deferred. Before reuse as production/OCR input, two audit findings remain:

1. prepared-document session/cache atomicity under overlapping selection/prepare operations;
2. stale TypeScript prepared-result contract that historically advertised crop output after destructive crop was disabled.

These do not block current Question Engine work.

## 10. Document-status continuity

`docs/DOCUMENT_STATUS_INDEX.md` is the repository map for avoiding stale-context mistakes.

Important classifications:

- binding/current governance: AGENTS, SECURITY, architecture/privacy/state, Codex workflow/context-gate enforcement;
- current Question Engine task context: discovery log, dispute/practice boundary, cross-contract classification, statutory map/snapshots as relevant, sanitized golden fixture/meta;
- research-only/non-authoritative: first dispute-practice JSON and cross-contract mechanism matrix;
- frozen/deferred component references: OCR, preprocessing, serverless worker, recognizer/PII research;
- historical UX/workflow scenarios: old Streamlit/mobile/OCR/Gold/cloud-OCR flows;
- optional/non-binding: Gemini external-audit prompt, future-ideas document, canary docs.

Historical/component/research-only files cannot override canonical current state or verified sources.

## 11. Audit continuity

Last completed periodic Codex batch audit before Question Engine pivot covered merged PRs #216–#224 and returned `CORRECTIVE PR REQUIRED` with no blocking findings. Worker-contract finding #1 was addressed by PR #225; the two Android findings above remain deferred.

PRs #239–#241 are docs/state/process changes. PR #242 adds schema-only Python definitions/tests. PR #243 adds documentation plus one sanitized unverified research index. PR #244 adds documentation plus one sanitized cross-contract comparison matrix. None adds runtime/provider evidence.

A future Codex implementation run for `question-engine-core-inventory-economic-v1` is an executor task, not a substitute for the orchestrating assistant's final per-PR audit/security review.

## 12. Recovery/work rules

Before a new PR:

1. read current binding/state/index documents from base;
2. check overlapping open PRs;
3. publish exactly one Context Gate v1;
4. implement only the permitted bounded step;
5. open PR as Draft;
6. update both state files after PR number exists;
7. run final validation on exact final head;
8. compare actual paths with Context Gate;
9. perform mandatory final-diff security review;
10. mark Ready only on `Security review: PASS` with no blocking conflict;
11. leave merge/auto-merge to explicit product-owner decision.

Documentation-only PRs do not require application tests but must validate references, JSON syntax/state consistency, declared paths, absence of restricted material/credentials, and final security metadata.

## 13. PR #244 validation target

Before Ready, PR #244 must verify:

- changed paths exactly match its Context Gate;
- branch is based on merged PR #243 / current `main`;
- both state files identify PR #244 / `question-engine-cross-contract-practice-classification-v1` and preserve `next_step_id = question-engine-core-inventory-economic-v1`;
- `CORE` is defined only as recurring product mechanism classification, not legal authority or outcome prediction;
- the comparison matrix is sanitized and explicitly research-only/non-authoritative;
- post-dispute questions are not promoted into ordinary pre-signing Question Engine;
- no raw/unsanitized contract material, raw OCR, handwriting reconstruction, party identifiers, exact address, phone/email/ID, signatures, guarantor identifying data, bank/account/check images, credentials or secrets are added;
- no dependency, external API/network destination, workflow, storage, OCR/Android/serverless, LLM/provider, schema behavior, runtime behavior or privacy-boundary change is introduced;
- final documentation/research security review passes on the exact final head.
