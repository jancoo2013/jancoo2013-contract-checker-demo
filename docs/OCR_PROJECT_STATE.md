# OCR Project State & Continuity v0

Последнее обновление: 2026-09-15, PR #267, `question-engine-provider-robust-fallback-ledger-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-provider-corrective-codex-review-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current corrective stack — PR #266 + PR #267

Provider experiment остаётся на паузе до независимой проверки обоих unmerged corrective PR.

Предыстория текущего исправления:

- local run v5 после PR #263 подтвердил рабочий `responseMimeType + responseJsonSchema`, но завершил только `3/10` cases за `1196.61s`; после case 4 primary 3.6 упёрлась в per-model daily free-tier quota;
- PR #264 увеличил inter-case pacing до 30 секунд;
- PR #265 различил daily-quota 429 и short-window 429 и временно добавил `gemini-3.1-pro-preview`;
- последующий provider batch audit выявил cross-PR defects: exhausted model не запоминается между cases; malformed/provider-shape failures не получают корректный fallback; quota detection опирается на строку; retry и routing делят один непрозрачный budget; отчёт смешивает transport/provider/semantic evidence и может потеряться при позднем сбое;
- владелец продукта решил пока не использовать `gemini-3.1-pro-preview` через API. Через API route остаются только Flash 3.6 и Flash 3.5.

PR #266 — `question-engine-provider-resilience-v1`:

- route ограничен `gemini-3.6-flash → gemini-3.5-flash`;
- unsupported `GEMINI_MODEL` блокируется до provider access;
- confirmed daily quota и stable 403/404 unavailability запоминаются на весь run;
- последующие cases пропускают уже недоступную модель;
- prompt, structured-output request, corpus oracle и semantic scorer не меняются.

PR #267 — `question-engine-provider-robust-fallback-ledger-v1`:

- malformed HTTP-200 envelope, malformed model JSON и locally schema-invalid structured output классифицируются как provider/model-output failures и могут перейти на следующую Flash-модель;
- локальная response-contract validation выполняется до semantic scorer;
- Google `QuotaFailure` и `RetryInfo` разбираются структурированно, с bounded text fallback;
- retry budget разделён на per-model attempts и global hard cap;
- каждый provider attempt получает provenance: case, model, attempt, status/failure class, duration и relevant HTTP/wait metadata;
- report summary показывает provider attempts/failure classes отдельно от semantic scores;
- JSON/TXT checkpoint пишется во время run атомарно, чтобы partial evidence переживал поздний case/provider failure;
- provider-wide HTTP 400 configuration failure прекращает run после сохранения partial report вместо расходования quota на остальные cases;
- Pro не добавляется обратно.

Оба PR остаются unmerged. Новый реальный Gemini run до Codex review запрещён.

## 2. Canonical next step

`next_step_id = question-engine-provider-corrective-codex-review-v1`

Следующий шаг — Codex audit именно двух незамёрженных corrective PR:

1. PR #266 относительно `main`;
2. stacked PR #267 относительно PR #266 base branch;
3. отдельно проверить combined resulting behavior после последовательного применения #266 + #267;
4. не вызывать Gemini API и не расходовать provider quota;
5. по результату либо исправить concrete findings до merge, либо признать stack mergeable;
6. только после merge и повторной final validation вернуть evidence gate к `question-engine-security-provider-experiment-local-run-v6`.

## 3. Current Question Engine architecture

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

Ключевые invariants не меняются: не извлекать базовый факт ради полноты; handwriting не угадывать; разные security instruments не сливать; missing/blank dependencies не исправлять молча; candidate finding не считать final finding; user-facing output не выдаёт `safe to sign`, sign/don't-sign advice, court prediction или categorical enforceability claim без отдельно одобренного deterministic rule.

## 4. Provider/privacy invariants

Provider experiment отправляет только synthetic/sanitized corpus material. Local API key читается из environment/Desktop `.env.local`, не входит в prompt/report и scrubbed из error detail. `.env.local` остаётся вне repository tree и игнорируется `.gitignore`.

Corrective stack сохраняет тот же Google GenerateContent host, те же 10 synthetic/sanitized security cases, prompt, target slots, structured-output request, corpus oracle, 30-second inter-case pacing, 120-second request timeout и local report destination. Новых dependencies, workflows, permissions, storage, OCR/Android/serverless paths или statutory runtime нет.

Repository остаётся pre-production. Production use с real contracts blocked до отдельно проверенных consent, authorization, encryption/key lifecycle, Israel-only restricted-data processing, deletion/retention, logging, provider terms, abuse/resource controls и incident response.

## 5. Audit continuity

Provider batch audit после PR #265 дал `FREEZE AFFECTED AREA` только для provider experiment до corrective work. Старый опубликованный API key уже был заблокирован Google; новый key не входит в current tree/diff.

PR #266 и PR #267 являются ответом на runtime/resource/reporting findings этого audit. Product owner требует ещё один Codex review именно этих двух PR до merge.

## 6. Recovery/work rules

Перед новым implementation PR читать с актуального base: `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`, оба state-файла, `docs/DOCUMENT_STATUS_INDEX.md`, `docs/CODEX_WORKFLOW.md`.

Каждый PR: ровно один Context Gate v1; оба state-файла обновляются; final checks относятся к exact final head; actual paths совпадают с Context Gate; mandatory security review; auto-merge запрещён.

## 7. PR #267 validation target

Перед merge stack должен подтвердить:

- #266 changed paths exactly match its Context Gate and remains based on main `00f2ebc7f64ccf28a9a0ad4876591901adc9df71`;
- #267 changed paths exactly match its Context Gate and is stacked only on final #266 head;
- route после combined stack ровно `gemini-3.6-flash → gemini-3.5-flash`; Pro runtime identifier отсутствует;
- daily quota/403/404 unavailable model memory survives across later cases;
- malformed HTTP-200 envelope/model JSON/schema-invalid output cannot become semantic `OK` and receives bounded next-model fallback;
- 429 daily quota и short-window limit различаются; structured RetryInfo используется when present;
- 503/timeout/rate-limit retries и routing bounded per model and globally;
- attempt ledger does not expose API key or prompt/contract text;
- semantic scorer runs only on locally contract-valid model output;
- partial JSON/TXT report survives case failure and provider-wide configuration abort;
- provider-wide repeated 400 does not burn the remaining 10-case quota;
- summary distinguishes provider attempts/failures from semantic quality and model provenance;
- prompt, corpus oracle и semantic/evidence scorer не изменены ради score;
- no raw/recoverable user data, dependency, workflow, permission, new provider host, production storage, OCR/Android/serverless path or statutory runtime is introduced;
- no real Gemini request is used for pre-merge validation;
- exact final diff receives Security review: PASS;
- Codex reviews both PRs and combined behavior before merge.
