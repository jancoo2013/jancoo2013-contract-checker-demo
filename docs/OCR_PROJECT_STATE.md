# OCR Project State & Continuity v0

Последнее обновление: 2026-08-26, PR #241, `question-engine-pre-codex-governance-sync-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-question-inventory-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #241 pre-Codex governance synchronization

PR #241 — documentation/process corrective перед запуском Codex на `question-engine-question-inventory-v1`.

Он не меняет продуктовую архитектуру или следующий implementation step. Цель — убрать неоднозначность repository context:

- `AGENTS.md` теперь явно требует брать current track/next step только из canonical state;
- historical/frozen/component documents не могут стать current direction лишь потому, что существуют в repository;
- новый `docs/DOCUMENT_STATUS_INDEX.md` классифицирует binding/current, Question Engine task-specific, frozen/deferred, historical UX/workflow и optional audit/reference documents;
- для будущего Question Engine Codex-task явно определён task-specific context после binding sources: discovery log, statutory references/snapshots when relevant, sanitized golden fixture/meta;
- Hebrew source evidence отделено от optional generated Hebrew discussion wording: model-generated discussion text не может выдаваться за source quotation;
- `.github/pull_request_template.md` больше не смешивает разрешённый privacy-reviewed sanitized golden text с запрещёнными raw/unsanitized contracts/PII;
- старые Streamlit, mobile Tesseract, mobile-backend, Gold/reviewer и cloud-OCR scenario docs сохранены как historical/frozen context, а не переписаны задним числом.

PR #241 не добавляет runtime code, dependencies, provider/API integration, network destination, workflow logic, storage, OCR implementation, user contract material, raw OCR, handwriting values, credentials или recoverable PII.

## 2. Canonical next step

`next_step_id = question-engine-question-inventory-v1`

После merge PR #241 следующий bounded implementation должен:

- определить первый deterministic recurring question inventory;
- определить необходимые conditional follow-ups;
- определить topic-specific structured answer fields;
- определить deterministic evidence targets/references;
- сохранить состояния `FOUND`, `NOT_FOUND`, `AMBIGUOUS`, `HANDWRITING_DEPENDENCY`, `CLAUSE_PRESENT_VALUE_BLANK`;
- сохранить contract-defined party-role granularity;
- зарезервировать чистые границы для будущих statutory/remediation layers;
- использовать существующий sanitized golden contract как первый fixture;
- не реализовывать весь statutory engine, финальный UI или Hebrew remediation subsystem;
- не добавлять production LLM/provider integration без отдельного разрешения;
- не reopening OCR/Android/serverless infrastructure.

Первый implementation PR должен оставаться маленьким и independently testable.

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

Task-specific for `question-engine-question-inventory-v1`:

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

PRs #239–#241 are docs/state/process changes and add no new runtime/provider evidence.

A new Codex implementation run for `question-engine-question-inventory-v1` is an executor task, not a substitute for the orchestrating assistant's final per-PR audit/security review.

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

## 12. PR #241 validation target

Before Ready, PR #241 must verify:

- changed paths exactly match its Context Gate;
- `AGENTS.md` no longer hard-codes a current active track/next step and explicitly reads them from state;
- the document-status index exists and classifies the known stale scenario documents without making them binding;
- source Hebrew evidence and optional generated Hebrew discussion wording are explicitly separated;
- PR template permits explicitly scoped privacy-reviewed sanitized golden fixtures while still prohibiting raw/unsanitized material and recoverable PII;
- both state files identify PR #241 / `question-engine-pre-codex-governance-sync-v1`;
- `active_track = question-engine-development` and `next_step_id = question-engine-question-inventory-v1` remain unchanged;
- no runtime/provider/workflow/dependency/network/storage/privacy-boundary change is introduced;
- final documentation/process security review is `PASS`.
