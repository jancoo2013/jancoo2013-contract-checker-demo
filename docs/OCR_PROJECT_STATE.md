# OCR Project State & Continuity v0

Последнее обновление: 2026-08-26, PR #240, `question-engine-statutory-source-snapshot-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-question-inventory-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущий `active_track` и `next_step_id` выбираются только этими state-файлами.

Подробная историческая запись PR до #238 остаётся в Git history. PR #239 компактировал текущий state и discovery log; PR #240 добавляет versioned statutory source snapshot поверх уже merged PR #239.

## 1. Current change — PR #240 versioned 2017 statutory snapshot

PR #240 добавляет первый immutable, source-attributed, machine-readable historical snapshot реформы жилой аренды 2017 года:

- `docs/statutory/README.md` — source hierarchy, versioning and maintenance rules;
- `docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2017_V1.json` — normalized historical rule snapshot grounded to official Knesset amendment/publication metadata;
- `docs/OCR_PROJECT_STATE.md` and `docs/OCR_PROJECT_STATE.json` — canonical state sync.

Snapshot относится к `חוק השכירות והשאילה (תיקון), התשע״ז-2017`, Amendment No. 1 к `חוק השכירות והשאילה, התשל״א-1971`.

Recorded source metadata:

- Knesset law item: `2006776`;
- publication: `ספר החוקים 2649`, starting p. 1028;
- publication date: `2017-07-19`;
- effective date: `2017-09-17`;
- official Knesset publication/page URLs stored in the snapshot/README.

The snapshot is a normalized engineering representation, not a copied full statute and not current-law authority by itself.

Later amendments must be resolved separately by effective date. Historical snapshots are immutable once merged; later changes get new snapshots/overlays rather than silently rewriting the 2017 object.

PR #240 does not change `active_track` or `next_step_id` and does not implement runtime statutory comparison yet.

## 2. Statutory source hierarchy

For Question Engine statutory work:

1. official current Knesset legislation database is authority for current consolidated law and amendment history;
2. official `ספר החוקים` publications are authority for historical amendment text/commencement;
3. repository JSON snapshots are deterministic engineering representations used by code/tests;
4. public templates, rental sites, blogs, generators, LLM memory, and prior chat summaries are not statutory truth sources.

A repository snapshot must never be treated as current merely because it exists.

Required future runtime order remains:

```text
contract fact
→ candidate statutory topic
→ applicability gate
→ contract/relevant date
→ effective-date-correct statutory snapshot/overlay
→ non-derogation / tenant-favor rule where relevant
→ comparison outcome
→ certainty class
→ allowed user-facing explanation/remediation class
```

If the required current/effective statutory version cannot be verified, the system must degrade to contract-only analysis instead of asserting a stale rule.

## 3. Canonical next step

`next_step_id = question-engine-question-inventory-v1`

Expected bounded scope after PR #240:

- define the first deterministic recurring question inventory;
- define conditional follow-ups needed by the existing sanitized golden contract and stable discoveries in `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`;
- define topic-specific structured answer fields and evidence targets;
- preserve `FOUND`, `NOT_FOUND`, `AMBIGUOUS`, `HANDWRITING_DEPENDENCY`, `CLAUSE_PRESENT_VALUE_BLANK` distinctions;
- reserve clean boundaries for later statutory/remediation layers;
- do not implement the whole statutory engine simply because the 2017 snapshot now exists;
- do not add production LLM/provider integration unless separately authorized;
- do not reopen OCR infrastructure.

## 4. Current Question Engine decisions from merged PR #239

The consolidated discovery log is `docs/QUESTION_ENGINE_DISCOVERY_LOG.md`.

Current decisions include:

- deterministic core inventory + LLM semantic reader + conditional follow-ups + cross-clause checks + bounded catch-all + Python/schema/evidence validation;
- candidate findings may be `CONFIRMED`, `NARROWED`, or `CLEARED` after second pass;
- handwriting is never semantically guessed;
- role granularity follows operative contract text;
- security instruments remain distinct;
- public template/source recency does not prove statutory alignment;
- contract facts, statutory rules, and product explanation stay separate;
- statute-grounded discussion text is blocked until applicability/effective-date/non-derogation checks pass;
- remediation outcomes include `CHANGE_OR_CLARIFY`, `ACTION_WITHOUT_REWRITE`, `NO_CHANGE_NEEDED`;
- UX hierarchy: Screen 1 orientation, Screen 2 Russian essay analysis, Screen 3 Russian discussion/action plan;
- Hebrew discussion text is optional/on-demand with copy/share;
- production Russian avoids words built from `юрист-` / `юрид-`; internal English `LEGAL_*` identifiers must not leak to rendered Russian copy;
- the product does not issue `safe to sign`, predict dispute outcomes, tell the user to sue/refuse payment/sign/not sign, or present model-generated wording as the uniquely correct final clause.

## 5. Existing Question Engine assets

Merged assets:

- PR #234 — active-track pivot from Surya/cloud OCR infrastructure to Question Engine;
- PR #235 — binding-doc synchronization;
- PR #236 — first sanitized golden contract fixture;
- PR #237 — dedicated Question Engine discovery log;
- PR #238 — template-family/statutory baseline discoveries + `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md`;
- PR #239 — consolidated discovery decisions/current state.

PR #240 adds the first versioned historical statutory snapshot but no runtime integration.

## 6. Privacy and data-handling invariants

Restricted material includes original contract photos, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers, guarantor identifying data, and other recoverable PII.

Restricted material must not enter GitHub/CI, Airtable, analytics/crash reports, general logs, downstream LLM prompts, or unrelated services.

Persistent Question Engine fixtures must be sanitized before commit.

Handwriting must not be semantically reconstructed or guessed. If a result depends on handwriting, return an explicit unresolved dependency.

Monetary amounts, dates, clause numbers, notice periods, and legally relevant printed wording are not PII by default when safely separable from identifying data.

PR #240 contains public statutory metadata/normalized rules only and no user contract material.

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

PR #240 changes none of these runtime/data-flow gates.

## 8. Frozen OCR infrastructure block

Surya/cloud OCR infrastructure remains frozen research, not the active implementation track.

The attempted targeted-region CPU runtime after PR #233 did not reach container build or OCR execution because Cloud Build job creation stopped at `PERMISSION_DENIED`. There is no measured CPU latency/quality result and no evidence that Surya CPU itself failed.

Reopen OCR infrastructure only if automatic OCR becomes a concrete product blocker or real usage justifies renewed infrastructure work.

Any reopened restricted-data processing must preserve the binding Israel-only, retention/deletion, logging and no-raw-Gemini constraints in `SECURITY.md`.

Tesseract full-page OCR on the target phone remains `NO-GO`.

## 9. Deferred Android preprocessing findings

Historical Android geometry/preprocessing work remains frozen/deferred while Question Engine is active.

Before that preprocessing path is reused as production/OCR input, two deferred findings remain:

1. prepared-document session/cache atomicity under overlapping selection/prepare operations;
2. stale TypeScript prepared-result contract that historically advertised crop output after destructive crop was disabled.

These findings do not block Question Engine inventory work.

## 10. Audit continuity

Last completed periodic Codex batch audit before the Question Engine pivot covered merged PRs #216–#224 and returned `CORRECTIVE PR REQUIRED` with no blocking findings. Worker-contract finding #1 was addressed by PR #225; the two Android findings above remain deferred.

PR #240 adds no runtime/provider behavior and claims none.

## 11. Recovery and work rules

Before a new PR:

1. read current `AGENTS.md`, `SECURITY.md`, architecture/privacy docs and both state files from the base;
2. check overlapping open PRs;
3. publish exactly one Context Gate v1 block;
4. implement only the allowed bounded step;
5. update both state files after PR number exists;
6. run final validation on exact final head;
7. inspect actual changed paths against Context Gate;
8. perform mandatory final-diff security review;
9. leave merge/auto-merge to explicit product-owner decision.

Documentation-only PRs do not require application tests, but must validate referenced files, machine-readable JSON syntax/consistency, declared paths, absence of restricted material/credentials/generated artifacts, and final security metadata.

## 12. PR #240 final validation target

Before Ready:

- changed paths must be exactly:
  - `docs/statutory/README.md`;
  - `docs/statutory/ISRAEL_RENTAL_AND_LOAN_AMENDMENT_2017_V1.json`;
  - `docs/OCR_PROJECT_STATE.md`;
  - `docs/OCR_PROJECT_STATE.json`;
- snapshot/README must identify the source as historical 2017 Amendment No. 1 and explicitly deny evergreen/current-law status;
- JSON must remain normalized rule metadata, not an unversioned full-law dump;
- both state files must identify PR #240 and `question-engine-statutory-source-snapshot-v1`;
- `active_track = question-engine-development` and `next_step_id = question-engine-question-inventory-v1` must remain unchanged;
- no user contract material, PII, handwriting values, credentials, runtime integration, provider/network destination, dependency, workflow, storage, or production data-flow change may be introduced;
- final documentation/state security review must be `PASS` before Ready.
