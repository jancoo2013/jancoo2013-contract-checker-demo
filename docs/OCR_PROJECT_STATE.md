# OCR Project State & Continuity v0

Последнее обновление: 2026-08-26, PR #242, `question-engine-schema-foundation-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-core-inventory-economic-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #242 Question Engine schema foundation

PR #242 — первый owner-authorized bounded slice внутри `question-engine-question-inventory-v1`.

Он добавляет только immutable, standard-library-only schema foundation для будущего inventory:

- строковый enum `AnswerState` ровно с canonical states `FOUND`, `NOT_FOUND`, `AMBIGUOUS`, `HANDWRITING_DEPENDENCY`, `CLAUSE_PRESENT_VALUE_BLANK`;
- frozen `QuestionSpec` только с полями `question_id`, `domain`, `purpose`, `answer_fields`;
- frozen `QuestionInventory` только с полями `schema_version`, `questions`;
- deterministic validation для поддерживаемой версии schema, непустого inventory, уникальных dotted question IDs и непустых уникальных snake_case answer fields.

PR #242 не добавляет actual question inventory, contract analysis, statutory conclusion, remediation wording, UI, OCR/Android/serverless work, LLM/provider integration, dependency, external API/network destination, storage, raw contract material, raw OCR, handwriting values, credentials или recoverable PII.

Parent step `question-engine-question-inventory-v1` не завершён: PR #242 предоставляет только его узкий schema foundation.

## 2. Canonical next step

`next_step_id = question-engine-core-inventory-economic-v1`

После merge PR #242 следующий owner-authorized bounded slice должен использовать schema foundation и определить только economic core inventory:

- определить первый bounded набор deterministic recurring economic questions;
- для каждого вопроса задать только `question_id`, `domain`, `purpose`, `answer_fields`;
- сохранить состояния `FOUND`, `NOT_FOUND`, `AMBIGUOUS`, `HANDWRITING_DEPENDENCY`, `CLAUSE_PRESENT_VALUE_BLANK`;
- сохранить contract-defined party-role granularity;
- использовать существующий sanitized golden contract как первый fixture;
- не реализовывать conditional, evidence-target, statutory/remediation, финальный UI или Hebrew remediation subsystem;
- не добавлять production LLM/provider integration без отдельного разрешения;
- не reopening OCR/Android/serverless infrastructure.

Следующий inventory slice должен оставаться маленьким и independently testable.

## 3. Required pre-Codex reading order

Codex/executor должен читать текущие файлы с base branch, а не полагаться на prompt history.

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
- `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md` for reserved statutory boundaries/terminology only, not full runtime statutory implementation;
- `docs/statutory/README.md` and current snapshots only where needed to keep schema boundaries coherent;
- `research/question_engine/golden_contracts/contract_001_he.txt`;
- `research/question_engine/golden_contracts/contract_001.meta.json`.

If these sources conflict on a binding/current rule, implementation stops and the conflict is reported.

## 4. Current Question Engine decisions

Merged PR #239 consolidated the current design in `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`.

Key invariants:

- deterministic core inventory + LLM semantic reader + conditional follow-ups + cross-clause checks + bounded catch-all + Python/schema/evidence validation;
- a candidate finding may become `CONFIRMED`, `NARROWED`, or `CLEARED` after second pass;
- handwriting is never semantically guessed or reconstructed;
- role granularity follows operative contract text;
- different security instruments remain distinct;
- contract facts, statutory rules, and product explanation are separate layers;
- source recency/template recognition is not proof of semantic or statutory alignment;
- statute-grounded discussion wording is blocked until applicability/effective-date/non-derogation checks pass;
- remediation outcomes include `CHANGE_OR_CLARIFY`, `ACTION_WITHOUT_REWRITE`, `NO_CHANGE_NEEDED`;
- UX hierarchy: Screen 1 orientation, Screen 2 Russian essay analysis, Screen 3 Russian discussion/action plan;
- Hebrew discussion text is optional/on-demand with copy/share;
- production Russian avoids words built from `юрист-` / `юрид-`; internal English `LEGAL_*` identifiers must not leak into rendered Russian copy;
- product does not issue `safe to sign`, predict dispute outcomes, instruct suit/refusal-to-pay/sign/not-sign, or present generated wording as the uniquely correct clause.

## 5. Statutory source status

The statutory authority is the current `חוק השכירות והשאילה, התשל״א-1971` from the official Knesset legislation database.

The 2017 reform is Amendment No. 1, effective `2017-09-17`, not a separate evergreen law.

Merged PR #240 added:

- `docs/statutory/README.md` — source hierarchy/versioning rules;
- `docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2017_V1.json` — immutable normalized historical 2017 snapshot.

The repository snapshot is not current-law authority by itself. Later amendments/overlays must be resolved by effective date. If required statutory freshness cannot be verified, future runtime must degrade to contract-only analysis rather than assert stale rules.

The first inventory PR does not implement the full statutory runtime merely because the historical snapshot exists.

## 6. Privacy and data-handling invariants

Restricted material includes original contract photos/pages, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers, guarantor identifying data, and other recoverable PII.

Restricted material must not enter GitHub/CI, Airtable, analytics/crash reports, general logs, downstream LLM prompts, or unrelated services.

Persistent Question Engine fixtures must be sanitized before commit.

Handwriting must not be semantically reconstructed or guessed. If a result depends on handwriting, return an explicit unresolved dependency.

Monetary amounts, dates, clause numbers, notice periods, and legally relevant printed wording are not PII by default when safely separable from identifying data.

The first golden fixture in `research/question_engine/golden_contracts/` is the current sanitized development input; source photos/raw values remain outside repository.

## 7. Production security status

Repository remains pre-production.

Production use with real contracts remains blocked pending implementation/verification of applicable controls including:

- user consent for any remote raw-processing path;
- authentication and account-scoped authorization;
- encryption/key lifecycle;
- Israel-only provider/runtime behavior for restricted material;
- retention, cleanup, deletion and backup-expiry guarantees;
- log/analytics scrubbing;
- provider terms/subprocessors;
- abuse/resource controls and incident response.

Question Engine inventory work changes none of these production gates.

## 8. Frozen OCR/Android status

Surya/cloud OCR infrastructure remains frozen research, not active implementation.

The targeted-region CPU attempt after PR #233 stopped at Cloud Build `PERMISSION_DENIED` before container build/OCR execution. There is no measured CPU latency/quality result and no evidence that Surya CPU itself failed.

Tesseract full-page Hebrew OCR on the target phone remains `NO-GO`.

Historical Android geometry/preprocessing remains frozen/deferred. Before that path can be reused as production/OCR input, two audit findings remain:

1. prepared-document session/cache atomicity under overlapping selection/prepare operations;
2. stale TypeScript prepared-result contract that historically advertised crop output after destructive crop was disabled.

These do not block current Question Engine inventory work.

## 9. Document-status continuity

`docs/DOCUMENT_STATUS_INDEX.md` is the repository map for avoiding stale-context mistakes.

Important classifications:

- binding/current governance: AGENTS, SECURITY, architecture/privacy/state, Codex workflow and context-gate enforcement;
- current Question Engine task sources: discovery log, statutory map/snapshots as relevant, sanitized golden fixture/meta;
- frozen/deferred component references: OCR, preprocessing, serverless worker, recognizer/PII research;
- historical UX/workflow scenarios: old Streamlit four-section flow, old mobile on-device OCR flow, old redacted-image backend slice, old Gold/reviewer workflow, old Cloud OCR plan;
- optional/non-binding: Gemini external-audit prompt, future-ideas document, canary docs.

A historical/component file may still be correct about its own experiment but cannot override canonical current state.

## 10. Audit continuity

Last completed periodic Codex batch audit before Question Engine pivot covered merged PRs #216–#224 and returned `CORRECTIVE PR REQUIRED` with no blocking findings. Worker-contract finding #1 was addressed by PR #225; the two Android findings above remain deferred.

PRs #239–#241 are docs/state/process changes and add no new runtime/provider evidence. PR #242 adds schema-only Python definitions/tests and no runtime/provider integration.

A new Codex implementation run for `question-engine-core-inventory-economic-v1` is an executor task, not a substitute for the orchestrating assistant's final per-PR audit/security review.

## 11. Recovery/work rules

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

Documentation-only PRs do not require application tests but must validate references, JSON state syntax/consistency, declared paths, absence of restricted material/credentials/generated artifacts, and final security metadata.

## 12. PR #242 validation target

Before Ready, PR #242 must verify:

- changed paths exactly match its Context Gate;
- `AnswerState` is a string Enum with exactly the five canonical answer states;
- frozen `QuestionSpec` and `QuestionInventory` expose only their authorized fields;
- deterministic validation rejects unsupported/non-positive schema versions, empty inventories, duplicate or malformed question IDs, empty domain/purpose, and empty, duplicate or malformed answer fields;
- no populated question inventory, contract-specific answer, source text/quote, statutory conclusion or remediation wording is added;
- both state files identify PR #242 / `question-engine-schema-foundation-v1`;
- `active_track = question-engine-development` and `next_step_id = question-engine-core-inventory-economic-v1` agree in both state files;
- no dependency, external API/network destination, workflow, storage, OCR/Android/serverless, LLM/provider or privacy-boundary change is introduced;
- focused compile/tests and final security review pass on the exact final head.
