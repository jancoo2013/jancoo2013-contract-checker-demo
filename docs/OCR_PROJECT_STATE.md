# OCR Project State & Continuity v0

Последнее обновление: 2026-09-10, PR #261, `question-engine-security-provider-fallback-35-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-security-provider-experiment-local-run-v3`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current change — PR #261 Gemini 3.5 fallback corrective

Ключевая продуктовая рамка не меняется:

- приложение не является универсальным пересказчиком договора;
- пользователь считается способным самостоятельно понять очевидные факты вроде своей роли, обычной суммы аренды и явных дат;
- простой fact извлекается только если он нужен как input для более глубокого smart-analysis вывода, расчёта, statutory gate или cross-clause resolution;
- найденная странность не обязана становиться user-facing finding, если она не меняет существенный механизм;
- ценность продукта — замечать неочевидные связи, рисковые механизмы, missing evidence и практические последствия, которые легко пропустить при обычном чтении.

Первый локальный запуск harness из PR #257 достиг Gemini API, но не дал semantic provider evidence: `0/10` cases completed. Ранние запросы получили HTTP `503` high-demand responses, затем сработал HTTP `429` free-tier request-rate limit.

PR #259 переключил diagnostic harness на `gemini-3.6-flash`, добавил 15-секундный pacing и bounded retry для HTTP `429/503`.

Второй локальный запуск после PR #259 дошёл до case `7/10`. На case `3/10` HTTP `503` был успешно пережит повтором. На case `7/10` после временного `503` следующий request завершился `The read operation timed out`; эксперимент аварийно завершился до cases 8–10 и до записи итогового report.

PR #260 увеличил per-request timeout до 120 секунд и сделал direct/URL-wrapped timeouts bounded per-case retry/failure вместо experiment-wide crash.

PR #261 — owner-authorized bounded corrective только provider-routing уровня diagnostic harness:

- основной model остаётся `gemini-3.6-flash`;
- fallback model — stable `gemini-3.5-flash`;
- HTTP `503` на primary переключает оставшиеся attempts этого case на fallback;
- direct read timeout или timeout-like `URLError` на primary также переключает оставшиеся attempts на fallback;
- HTTP `429` не переключает модель и остаётся same-model quota/rate-limit retry;
- после переключения fallback не происходит автоматического возврата на primary внутри того же case;
- общий cap остаётся максимум 4 provider attempts на case;
- successful case сохраняет `model_used`, а report отдельно показывает primary/fallback и число успешно завершённых fallback cases;
- prompt, 10-case corpus selection, semantic scoring, evidence refs, instrument identity, handwriting/missing-dependency checks и local report destination не меняются.

Current official Google model/deprecation documentation проверена 2026-09-10: `gemini-3.6-flash` и `gemini-3.5-flash` являются stable Gemini API models; shutdown date для них не объявлена.

В PR нет real contracts, raw OCR, recoverable PII, statutory runtime, OCR/Android/serverless изменений, production storage, UI behavior, нового provider, dependency, workflow или production quality claim.

## 2. Canonical next step

`next_step_id = question-engine-security-provider-experiment-local-run-v3`

Следующий шаг — повторный локальный запуск исправленного harness двойным щелчком и разбор generated JSON/TXT. При transient `503`/timeout primary 3.6 может автоматически уступить конкретный case fallback 3.5; report должен показать, какая модель реально ответила на каждый successful case.

После реального успешного provider run нужно разобрать:

- какие exact semantic assertions модель поняла правильно;
- где смешала разные security instruments;
- где перепутала amount/blank/notice/return properties;
- где incorrectly linked evidence refs или distractors;
- различила ли BLANK, MISSING_DEPENDENCY и HANDWRITING_DEPENDENCY;
- правильно ли выполнила candidate resolution;
- какие cases обработаны primary 3.6, а какие fallback 3.5;
- были ли hard failures: guessed unavailable value, unsupported ref, duplicate/unrequested assertion или malformed provider output.

Только реальные semantic failure modes успешного запуска определят следующий LLM↔Python corrective. Не добавлять confidence, broad typed-value framework, universal ontology или новые schema fields заранее без provider evidence.

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

`QuestionSpec` и `QuestionInventory` остаются static question definitions. PR #257 добавил локальный diagnostic provider harness; PR #259–#261 меняют только provider/model-call robustness/routing этого experiment harness, не Question Engine schema.

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

PR #261 statutory runtime/current-law claims не добавляет и external law в provider prompt не передаёт.

## 8. Privacy and security invariants

Restricted material включает original contract photos/pages, raw OCR, names, Israeli IDs, phone/email/address data, signatures, bank/account/check identifiers or images, guarantor identifying data и другую recoverable PII.

Restricted material не должен попадать в GitHub/CI, analytics/crash reports, general logs, downstream LLM prompts или unrelated services без отдельно одобренной privacy architecture.

Persistent fixtures/research artifacts должны быть sanitized до commit. Handwriting не угадывается. Monetary amounts, dates, clause numbers, notice periods и legally relevant printed wording не являются PII по умолчанию, когда безопасно отделены от identifiers.

Provider experiment отправляет только synthetic/sanitized corpus material. Он не использует real user contracts, raw OCR, user identifiers, signatures, bank/check identifiers или recoverable PII. Local API key читается из environment/Desktop `.env.local`, не входит в prompt/report и scrubbed из HTTP error detail. `.env.local` остаётся вне repository tree и игнорируется `.gitignore`.

PR #261 добавляет fallback только между двумя stable model IDs на том же фиксированном Google Gemini API endpoint. Это не разрешение на provider fallback для restricted production material. Diagnostic harness остаётся synthetic/sanitized-only. Case count остаётся 10, общий cap — максимум 4 attempts на case; переход на fallback не увеличивает этот cap. HTTP 429 не используется как основание для model switching.

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
- PR #256 — corpus oracle v2 semantic correction after narrow corpus audit;
- PR #257 — bounded local Gemini security provider-experiment harness;
- first local PR #257 run — API reached, but 0/10 completed because of 503/429 transport/quota failures; no semantic provider conclusion;
- PR #259 — owner-authorized bounded corrective switching the experiment default to Gemini 3.6 Flash and adding bounded pacing/retries;
- second local run after PR #259 — reached 7/10, recovered one 503, then aborted on an uncaught read timeout before report persistence;
- PR #260 — owner-authorized bounded corrective adding timeout tolerance while preserving the same model, corpus and semantic contract;
- PR #261 — owner-authorized bounded corrective adding `gemini-3.5-flash` fallback for primary 3.6 transient 503/timeouts and explicit per-case model provenance.

No successful complete semantic provider report is recorded yet. PR #261 exists only to obtain that evidence more reliably without changing Question Engine semantics.

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

## 12. PR #261 validation target

Before Ready/merge, PR #261 must verify:

- changed paths exactly match Context Gate;
- branch is based on current `main` head `63cd47f9e69ce6be2691f412de6becf7f1f5e36e` and is not behind it;
- both state files identify PR #261 and `question-engine-security-provider-fallback-35-v1`;
- next step remains `question-engine-security-provider-experiment-local-run-v3`;
- primary default model remains exactly `gemini-3.6-flash`;
- fallback model is exactly `gemini-3.5-flash`;
- primary HTTP 503/direct timeout/timeout-like URLError can switch the remaining case attempts to fallback;
- HTTP 429 does not trigger model switching;
- total provider attempts remain capped at 4 per case;
- successful result records the actual `model_used`, and summary reports fallback usage;
- retry/error messages do not disclose the API key;
- experiment selection remains exactly the same 10 security-domain corpus cases;
- prompts, expected oracle isolation, semantic scoring, evidence refs and fail-closed missing/handwriting behavior remain unchanged;
- output reports remain local and contain no API key;
- no new dependency, workflow, permission, provider host, production storage, OCR/Android/serverless path or statutory runtime is introduced;
- focused tests and Python compilation pass on exact final code blobs;
- Markdown/JSON state agree;
- final security review passes on exact final head;
- actual Gemini 3.6→3.5 failover, latency, quota interaction and semantic quality remain unverified until the product owner performs local run v3.
