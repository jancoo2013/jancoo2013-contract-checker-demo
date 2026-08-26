# OCR Project State & Continuity v0

Последнее обновление: 2026-08-26, PR #239, `question-engine-discovery-consolidation-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-question-inventory-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущий `active_track` и `next_step_id` выбираются только этими state-файлами.

> PR #239 компактирует этот state-документ после завершения длинной исследовательской фазы Question Engine. Подробная историческая запись PR до #238 остаётся доступна в Git history; здесь сохранено текущее состояние, доказанные ограничения, незакрытые блокеры и сведения, необходимые для безопасного продолжения разработки.

## 1. Current change — PR #239 Question Engine discovery consolidation

PR #239 завершает накопительный исследовательский этап перед реализацией `question-engine-question-inventory-v1`.

Он консолидирует `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`, устраняя исторические противоречия между ранними и более поздними working conclusions.

Текущие зафиксированные решения:

- Question Engine начинается с deterministic core inventory, затем использует LLM как semantic reader, conditional follow-ups, cross-clause checks, bounded catch-all и Python/schema/evidence validation;
- candidate finding обязан проходить second pass и может быть `CONFIRMED`, `NARROWED` или `CLEARED`; система не должна только накапливать red flags;
- `FOUND`, `NOT_FOUND`, `AMBIGUOUS`, `HANDWRITING_DEPENDENCY`, `CLAUSE_PRESENT_VALUE_BLANK` остаются отдельными states;
- handwriting не транскрибируется, не реконструируется и не угадывается;
- role granularity определяется operative contract text, а не количеством имён в шапке;
- разные security instruments не сворачиваются в один generic deposit;
- cross-clause composition обязательна для early exit, security, repairs, definitions, remedies, standard-vs-special terms и internal references;
- broken references, blanks, external economic dependencies, ratio/penalty calculations и bespoke obligations являются first-class findings;
- statutory layer отделён от contract facts и product explanation;
- applicability/effective date/non-derogation проверяются до statute-grounded user output;
- current law, а не память о редакции 2017 года, является authority; при stale/unverified statutory state анализ деградирует до contract-only;
- публичные templates/blogs useful only for topic/pattern discovery, не как источник statutory truth;
- source recency и template-family recognition не доказывают semantic/statutory alignment;
- remediation является отдельным слоем: `CHANGE_OR_CLARIFY`, `ACTION_WITHOUT_REWRITE`, `NO_CHANGE_NEEDED`;
- statute-grounded discussion text блокируется без deterministic statutory gate;
- Russian UX избегает слов с корнями `юрист-` / `юрид-`; internal English identifiers могут оставаться в engineering schema;
- текущая UX-иерархия: Screen 1 orientation, Screen 2 Russian essay analysis, Screen 3 Russian discussion/action plan; Hebrew discussion text показывается только по запросу, с copy/share action;
- продукт не выдаёт `safe to sign`, не предсказывает исход спора и не превращает model-generated wording в якобы единственную правильную редакцию.

PR #239 — docs/state-only. Он не добавляет contract source text/images, raw OCR, PII, handwriting values, runtime model/API integration, dependency, provider, network destination, workflow, storage или production behavior.

## 2. Active Question Engine development pipeline

```text
owner-controlled rental contracts
→ reliable printed-text ground truth outside production OCR dependency
→ exclude handwriting from semantic transcription
→ de-identify recoverable PII while preserving contract-defined roles
→ sanitized golden contract corpus
→ recurring-question inventory + conditional branches
→ LLM structured semantic reading
→ cross-clause checks + bounded catch-all
→ Python/schema/evidence validation
→ statutory applicability/effective-date comparison where relevant
→ confirmed/narrowed/cleared findings
→ Russian report and discussion plan
```

Question Engine must remain OCR-provider-independent.

The next PR must implement only the bounded first inventory/schema/evidence-target layer unless the product owner explicitly changes `next_step_id`.

## 3. Canonical next step

`next_step_id = question-engine-question-inventory-v1`

Expected bounded scope:

- define the first deterministic recurring question inventory;
- define conditional follow-ups needed by the existing sanitized golden contract and the stable discoveries recorded in `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`;
- define topic-specific structured answer fields and evidence targets;
- preserve the existing status distinctions and handwriting rule;
- reserve clean boundaries for later statutory/remediation layers;
- do not add production LLM/provider integration unless separately authorized;
- do not reopen OCR infrastructure.

The first implementation should be small enough to review and test independently. It must not attempt the complete Question Engine, full statutory engine, final UI, or Hebrew-generation subsystem in one PR.

## 4. Existing Question Engine assets

Merged assets before PR #239:

- PR #234 — pivoted active development from Surya/cloud OCR infrastructure to Question Engine;
- PR #235 — synchronized binding docs to that pivot;
- PR #236 — added first sanitized golden contract fixture while preserving printed legal values, source inconsistencies and only contract-required individual role distinctions;
- PR #237 — added dedicated Question Engine discovery log;
- PR #238 — added template-family/statutory discoveries and `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md`.

The detailed product discoveries are now consolidated in `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`.

## 5. Statutory baseline direction

The statutory source is the current `חוק השכירות והשאילה, התשל״א-1971`.

The reform commonly called `שכירות הוגנת` is treated as Amendment No. 1 from 2017, effective `2017-09-17`, not as an evergreen standalone statute.

Required comparison order:

```text
contract fact
→ statutory topic
→ applicability gate
→ effective-date-correct rule
→ non-derogation / tenant-favor rule where relevant
→ comparison outcome
→ certainty class
→ user-facing explanation
```

`docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md` is the maintained engineering map. It is not by itself proof that a rule remains current.

PR #240 is an overlapping Draft at the time PR #239 is prepared. It adds the first immutable, source-attributed 2017 statutory snapshot and must be rebased/stacked on the final merged PR #239 state before it can be Ready. PR #240 does not change `active_track` or `next_step_id`.

## 6. Privacy and data-handling invariants

Restricted material includes original contract photos, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers, guarantor identifying data, and other recoverable PII.

Restricted material must not enter:

- GitHub or CI;
- Airtable;
- analytics or crash reports;
- general logs;
- downstream LLM prompts;
- unrelated services.

Persistent Question Engine fixtures must be sanitized before commit.

Handwriting must not be semantically reconstructed or guessed. If a result depends on handwriting, return an explicit unresolved dependency.

Monetary amounts, dates, clause numbers, notice periods, and legally relevant printed wording are not PII by default when safely separable from identifying data.

## 7. Production security status

The repository remains pre-production.

Production use with real contracts remains blocked pending implementation/verification of, as applicable:

- user consent for any remote raw processing path;
- authentication and exact account-scoped authorization;
- encryption/key lifecycle;
- Israel-only provider/runtime behavior for restricted material;
- retention, cleanup and deletion guarantees;
- log/analytics scrubbing;
- backup expiry and account/report deletion;
- provider terms/subprocessors;
- abuse/resource limits and incident response.

No PR in the current Question Engine docs/research phase changes those production gates.

## 8. Frozen OCR infrastructure block

Surya/cloud OCR infrastructure is frozen research, not the active implementation track.

The attempted targeted-region CPU runtime after PR #233 did not reach container build or OCR execution because Cloud Build job creation stopped at `PERMISSION_DENIED`. Therefore there is no measured CPU latency/quality result and no evidence that Surya CPU itself failed.

Reopen OCR infrastructure only if automatic OCR becomes a concrete product blocker or real usage justifies renewed infrastructure work.

Any reopened restricted-data processing must preserve the binding Israel-only, retention/deletion, logging and no-raw-Gemini constraints in `SECURITY.md`.

Tesseract full-page OCR on the target phone remains a proven `NO-GO` and must not be restored as an active fallback without new evidence and explicit state change.

## 9. Deferred Android preprocessing findings

Historical Android geometry/preprocessing work remains frozen/deferred while Question Engine is the active track.

Two post-audit findings remain deferred before that Android preprocessing path may be reused as production/OCR input:

1. prepared-document session/cache atomicity under overlapping selection/prepare operations;
2. stale TypeScript prepared-result contract that historically advertised crop output after destructive crop was disabled.

These findings do not block the current Question Engine inventory work because that work uses sanitized golden text and is OCR-provider-independent.

## 10. Audit continuity

Last completed periodic Codex batch audit before the Question Engine pivot covered merged PRs #216–#224 and returned `CORRECTIVE PR REQUIRED` with no blocking findings. Worker-contract finding #1 was addressed by PR #225; the two Android findings above remain deferred.

No new runtime/provider/security evidence is claimed by PR #239.

Before any PR is marked Ready, the orchestrating assistant must inspect the exact final diff and provide the mandatory `SECURITY.md` verdict.

## 11. Recovery and work rules

Before a new branch/PR:

1. read current `AGENTS.md`, `SECURITY.md`, architecture/privacy docs and both state files from the PR base;
2. check overlapping open PRs;
3. publish exactly one Context Gate v1 block;
4. implement only the allowed bounded step;
5. update both state files after the PR number exists;
6. run final validation on the exact final head;
7. inspect actual changed paths against Context Gate;
8. perform mandatory final-diff security review;
9. leave merge/auto-merge to explicit product-owner decision.

Documentation-only PRs do not require application tests, but must validate referenced files, JSON state parse/consistency, declared paths, absence of restricted material/credentials/generated artifacts, and final security metadata.

## 12. PR #239 final validation target

Required before Ready:

- changed files exactly match the PR #239 Context Gate;
- `docs/QUESTION_ENGINE_DISCOVERY_LOG.md` contains the consolidated current decisions and no unresolved contradictory production UX instruction;
- both state files identify PR #239 and `question-engine-discovery-consolidation-v1`;
- `active_track = question-engine-development` unchanged;
- `next_step_id = question-engine-question-inventory-v1` unchanged;
- no raw contract/PII/handwriting values or copied public contract text are introduced;
- security impact is documentation/state only;
- final security review is `PASS` if the exact final diff satisfies these conditions.
