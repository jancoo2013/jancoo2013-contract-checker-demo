# OCR Project State & Continuity v0

Последнее обновление: 2026-09-08, PR #245, `question-engine-core-inventory-economic-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-core-inventory-early-exit-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #245 core economic/security inventory

PR #245 implements the first populated provider-independent Question Engine inventory on top of the immutable schema foundation from PR #242.

The bounded inventory is intentionally pre-signing and contract-fact focused:

- one monthly-rent baseline question for deterministic economic context;
- distinct security-instrument inventory and cumulative/alternative relationship;
- per-instrument amounts and blank date/amount/payee checks;
- printed authority to complete missing instrument particulars;
- linkage to obligations, periods, and separately referenced security documents;
- realization chain kept as separate trigger / amount-basis / notice / cure fields;
- recovery-overlap question for multiple instruments addressing the same underlying obligation;
- option/renewal continuity, return mechanics, and guarantor scope;
- no generic `deposit` collapse across cheque, promissory note, guarantor, bank guarantee, cash/deposit, rent cheque, or open utility cheque mechanisms.

The inventory uses only the existing `QuestionSpec(question_id, domain, purpose, answer_fields)` schema. It adds no answer-value model, conditional trigger runtime, evidence-target layer, statutory/case-law runtime, provider/LLM integration, UI, OCR, Android, serverless, storage, dependencies, permissions, or network destinations.

The existing sanitized golden fixture remains the grounding development source; no raw contract image/OCR, recoverable PII, handwriting, cheque image, guarantor identity, or bank/account identifier is added.

The current five `AnswerState` values remain unchanged. The research distinction between an intentionally blank template field and a still-blank field in a completed/signed document remains a future schema decision and is not silently encoded in this inventory PR.

## 2. Canonical next step

`next_step_id = question-engine-core-inventory-early-exit-v1`

The next owner-authorized bounded implementation should apply the same small deterministic pattern to the recurring `early exit + replacement tenant` CORE mechanism family.

Scope of that next slice:

- capture continuing rent liability after early departure;
- capture any replacement-tenant route;
- capture the landlord approval standard;
- capture assignment/subletting wording only where it affects that route;
- capture contractual termination consequences that compose with early exit;
- keep post-dispute facts such as an already proposed candidate, keys later returned, actual re-letting, or a lawsuit outside ordinary pre-signing inventory;
- continue using only the existing schema unless a separate explicit schema decision is authorized;
- do not add statutory/case-law runtime, conditional execution engine, provider integration, UI, OCR/Android/serverless work, dependencies, storage, or network access.

The parent `question-engine-question-inventory-v1` sequence remains incomplete after PR #245.

## 3. Required reading order

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

Current Question Engine task context, as applicable:

- `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`;
- `docs/QUESTION_ENGINE_DISPUTE_PRACTICE_LAYER_V0.md`;
- `docs/QUESTION_ENGINE_DISPUTE_PRACTICE_CLASSIFICATION_V1.md`;
- `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md`;
- `docs/statutory/README.md` and versioned snapshots when statutory comparison is in scope;
- `research/question_engine/golden_contracts/contract_001_he.txt`;
- `research/question_engine/golden_contracts/contract_001.meta.json`.

Research-only dispute/practice JSON artifacts remain non-authoritative and cannot override verified contract evidence, current law, binding documents, or canonical state.

## 4. Current Question Engine invariants

- deterministic core inventory + LLM semantic reader + later conditional follow-ups + cross-clause checks + bounded catch-all + Python/schema/evidence validation;
- candidate findings may become `CONFIRMED`, `NARROWED`, or `CLEARED` after second pass;
- handwriting is never semantically guessed or reconstructed;
- role granularity follows operative contract text;
- different security instruments remain distinct;
- security analysis separates instrument mechanics, authority to complete/realize, underlying obligation/amount, and any later execution procedure;
- contract facts, statutory rules, dispute/practice research, Question Engine decisions, and product explanation remain separate layers;
- two-contract recurrence can promote a product mechanism family, never a legal proposition by itself;
- ordinary pre-signing Question Engine includes only questions whose answers materially change present contract analysis;
- post-dispute questions such as execution warning, later key return, actual re-letting, lawsuit filing, or post-move-out damage remain outside ordinary pre-signing inventory;
- statutory output remains gated by applicability, effective-date, and non-derogation checks;
- user-facing product does not issue `safe to sign`, predict court outcomes, instruct suit/refusal-to-pay/sign/not-sign, or present generated wording as uniquely correct.

Current UX hierarchy remains: Screen 1 orientation, Screen 2 Russian essay analysis, Screen 3 Russian discussion/action plan. Hebrew discussion text remains optional/on-demand.

## 5. Current mechanism classification

`CORE` product mechanism families after two independent sanitized contracts:

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

PR #245 is the first runtime-neutral populated inventory slice and covers only the bounded economic/security portion described above.

## 6. Statutory source status

Current statutory authority must be resolved from the current official legislation source with effective-date logic.

The 2017 residential-rental reform is Amendment No. 1, effective `2017-09-17`, not a separate evergreen law. The historical snapshot in the repository is not current-law authority by itself.

The maintained statutory baseline notes that section `25י` has 2026 amendment timing and therefore requires effective-date versioning. PR #245 does not implement statutory runtime or legal conclusions.

If statutory freshness cannot be verified in a future runtime, analysis must degrade to contract-only rather than assert stale law.

## 7. Privacy and data-handling invariants

Restricted material includes original contract photos/pages, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers or images, guarantor identifying data, and other recoverable PII.

Restricted material must not enter GitHub/CI, Airtable, analytics/crash reports, general logs, downstream LLM prompts, or unrelated services unless an explicitly approved privacy architecture says otherwise.

Persistent fixtures/research artifacts must be sanitized before commit. Handwriting must not be semantically reconstructed or guessed. Monetary amounts, dates, clause numbers, notice periods, and legally relevant printed wording are not PII by default when safely separable from identifying data.

PR #245 adds only schema-compatible question definitions, tests, and state metadata. It adds no contract text/image fixture, raw OCR, PII, credentials, provider configuration, storage, or network behavior.

## 8. Production security status

Repository remains pre-production.

Production use with real contracts remains blocked pending implementation/verification of applicable controls including user consent for any raw remote path, authentication/account-scoped authorization, encryption/key lifecycle, Israel-only provider behavior for restricted material, retention/deletion guarantees, log scrubbing, provider terms, abuse/resource controls, and incident response.

Question Engine inventory work changes none of these production gates.

## 9. Frozen OCR/Android status

Surya/cloud OCR infrastructure remains frozen research, not active implementation.

The targeted-region CPU attempt after PR #233 stopped at Cloud Build `PERMISSION_DENIED` before container build/OCR execution. There is no measured CPU latency/quality result and no evidence that Surya CPU itself failed.

Tesseract full-page Hebrew OCR on the target phone remains `NO-GO`.

Historical Android geometry/preprocessing findings remain deferred and do not block current Question Engine work.

## 10. Document-status continuity

`docs/DOCUMENT_STATUS_INDEX.md` remains the repository map for avoiding stale-context mistakes.

Binding/current governance, current Question Engine context, research-only artifacts, frozen/deferred OCR references, and historical UX/workflow documents keep their existing authority classes. Historical/component/research-only files cannot override canonical current state or verified sources.

## 11. Audit continuity

Last completed periodic Codex batch audit before the Question Engine pivot covered merged PRs #216–#224 and returned `CORRECTIVE PR REQUIRED` with no blocking findings. Worker-contract finding #1 was addressed by PR #225; deferred Android findings remain outside the current track.

PRs #239–#241 are docs/state/process changes. PR #242 adds schema-only Python definitions/tests. PR #243 adds documentation plus one sanitized unverified research index. PR #244 adds documentation plus one sanitized cross-contract comparison matrix. PR #245 adds the first populated schema-only economic/security inventory and focused tests. None adds provider/runtime integration evidence.

A future Codex implementation run is an executor task, not a substitute for the orchestrating assistant's final per-PR audit/security review.

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

## 13. PR #245 validation target

Before Ready, PR #245 must verify:

- changed paths exactly match its Context Gate;
- branch is based on merged PR #244 / current `main`;
- both state files identify PR #245 / `question-engine-core-inventory-economic-v1` and select `question-engine-core-inventory-early-exit-v1` as the next bounded step;
- populated inventory uses only the existing immutable schema foundation and contains no conditional trigger/evidence/statutory/provider runtime;
- security instruments remain semantically distinct and the realization chain preserves grounds, amount basis, notice, and cure as separate answer fields;
- ordinary pre-signing inventory does not introduce post-dispute questions;
- golden-fixture grounding remains sanitized and no raw/unsanitized contract material, raw OCR, handwriting reconstruction, party identifiers, exact address, phone/email/ID, signatures, guarantor identifying data, bank/account/check images, credentials or secrets are added;
- no dependency, external API/network destination, workflow, storage, OCR/Android/serverless, LLM/provider, or privacy-boundary change is introduced;
- focused Question Engine tests and Python compilation pass on the exact final head;
- final security review passes on the exact final head.
