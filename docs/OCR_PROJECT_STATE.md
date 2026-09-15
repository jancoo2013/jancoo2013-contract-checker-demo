# OCR Project State & Continuity v0

Последнее обновление: 2026-09-15, PR #268, `question-engine-provider-parse-routing-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-provider-ledger-reporting-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current provider corrective chain

Provider experiment остаётся paused до завершения corrective chain и единого финального Codex review.

Relevant continuity:

- local run v3 after PR #261 дал первый usable semantic provider report: `9/10` cases, `12/33` exact assertions, `18/33` values, `18/33` states, `19/33` refs, `5/5` resolutions, `4` hard failures;
- PR #262 попытался включить provider-enforced structured output, но local run v4 получил `10/10` HTTP 400 из-за неправильного request field;
- PR #263 исправил GenerateContent request на `responseMimeType + responseJsonSchema`;
- local run v5 после PR #263 подтвердил request shape, но занял `1196.61s` и завершил только `3/10` cases; затем primary 3.6 упёрлась в per-model daily free-tier quota;
- PR #264 увеличил pacing до 30 секунд;
- PR #265 различил daily-quota 429 и short-window 429 и временно добавил Pro;
- provider audit после #265 выявил повторные запросы к exhausted model, неверную обработку auth errors, malformed-output gaps, unbounded response read, overly broad quota detection, retry-hint defects, отсутствие attempt provenance и слабую report/checkpoint integrity;
- владелец решил не использовать `gemini-3.1-pro-preview` через API до подтверждения бесплатного API tier.

PR #266 закрыл первую bounded-часть:

- route только `gemini-3.6-flash → gemini-3.5-flash`;
- unsupported model override блокируется до provider request;
- confirmed daily quota и stable HTTP 404 model-unavailable запоминаются на весь run;
- следующие cases пропускают remembered unavailable model;
- HTTP 401/403 считаются global auth/permission failure и прекращают run без model fallback;
- Pro отсутствует в executable route.

PR #268 закрывает вторую bounded-часть:

- HTTP 200 response body читается с hard byte bound до JSON parse;
- malformed outer JSON/envelope, malformed model JSON и local schema-invalid output не идут в semantic scorer и получают bounded fallback;
- JSON `NaN/Infinity` отклоняются; finite-number contract проверяется локально;
- `resolution.outcome` и остальные structured fields валидируются fail-closed без uncaught type errors;
- malformed nested provider error metadata не может ломать quota/retry parser;
- structured `QuotaFailure`/`RetryInfo` поддерживаются, daily detector использует узкие daily identifiers вместо generic `perDay`;
- retry hints принимаются только finite/non-negative и выбирается наиболее консервативная доступная задержка;
- retry/routing budget разделён на bounded per-model attempts и global hard cap;
- prompt semantics, selected ten cases, target assertions, corpus oracle и strict semantic scorer не меняются;
- реальных Gemini requests для проверки PR не выполнялось.

## 2. Canonical next step

`next_step_id = question-engine-provider-ledger-reporting-v1`

Следующий и последний provider-harness corrective перед финальным Codex review:

- attempt ledger для каждой provider попытки без prompt/contract text;
- per-model attempts/successes/failure-class reporting отдельно от semantic score;
- recursive secret redaction перед persistence/rendering либо отказ от unsafe raw output persistence;
- exhausted route должен завершать run без дальнейших 30-секундных sleeps и не помечаться `COMPLETED`;
- partial report checkpoint должен переживать case/global failure;
- JSON/TXT terminal publication должна быть согласована так, чтобы canonical JSON не переходил в terminal status раньше companion TXT;
- корректный report label при single-model override;
- no Pro, no semantic prompt/corpus/oracle changes.

После этого следующий шаг — один final Codex review цепочки `#266 → #268 → final reporting PR`. Только при отсутствии реального HIGH/BLOCKER можно последовательно merge и запускать local Gemini run v6.

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

Core product invariants сохраняются: basic facts не извлекаются ради полноты; handwriting не угадывается; разные security instruments не сливаются; missing/blank dependencies не исправляются молча; candidate finding не является final finding; user-facing output не выдаёт `safe to sign`, sign/don't-sign advice, court prediction или categorical enforceability claim без отдельно одобренного deterministic rule.

## 4. Provider/privacy invariants

Provider experiment отправляет только synthetic/sanitized corpus material. Real contracts, raw OCR, names/IDs/signatures/bank identifiers и recoverable PII в Gemini diagnostic harness не передаются.

Local API key читается из environment/Desktop `.env.local`; `.env.local` игнорируется repository. Provider host остаётся fixed Google GenerateContent host. Новых dependencies, workflows, permissions, provider hosts, production storage, OCR/Android/serverless paths или statutory runtime в #268 нет.

Route после #268 остаётся только `gemini-3.6-flash → gemini-3.5-flash`; timeout 120 секунд; pacing 30 секунд; per-model attempt cap 2; global attempt cap 4; response body bounded до local parse.

Repository остаётся pre-production. Production use с real contracts blocked до отдельно проверенных consent, authorization, encryption/key lifecycle, Israel-only restricted-data processing, deletion/retention, logging, provider terms, abuse/resource controls и incident response.

## 5. Audit continuity

Последний завершённый Question Engine batch audit recovery marker:

- дата: `2026-09-08`;
- start SHA: `cbbb8e0905c1fda8610260d4046b51952a9f636c`;
- end SHA: `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`;
- principal PR range: `#234–#250`;
- outcome: `CORRECTIVE PR REQUIRED`;
- privacy/security regression в этом range не был отмечен.

Отдельный provider audit после #265 относится только к provider experiment corrective chain. Старый опубликованный API key уже заблокирован Google и не является новым blocker текущих PR.

## 6. Stable recovery anchors

Current provider-independent schema foundation:

```text
AnswerState
  presence: PresenceStatus
  value: ValueStatus
  evidence: EvidenceStatus
  source: SourceStatus
  lifecycle: DocumentLifecycle

MechanismCollection(domain, mechanisms)
MechanismInstance(mechanism_id, mechanism_type, properties)
MechanismProperty(name, value, state)

FindingCandidate(finding_id, domain, subject_refs)
FindingResolution(candidate, outcome, reviewed_refs, resolution_summary)
FindingOutcome = CONFIRMED | NARROWED | CLEARED
```

Current smart CORE families: security/enforcement, early exit/replacement tenant, financial sanctions/overlap, condition/AS-IS/defects/damage evidence, termination/cure/notice, option/renewal. Corpus oracle v2 остаётся evaluation representation, не production runtime schema.

Statutory recovery anchor: 2017 residential-rental reform effective `2017-09-17`; maintained baseline учитывает 2026 amendment timing для section `25י`. Если current-law freshness/applicability/effective date не установлены безопасно, runtime деградирует к contract-only analysis.

Frozen OCR recovery anchor: Surya/cloud OCR infrastructure остаётся frozen research; Tesseract full-page Hebrew OCR на target phone остаётся `NO-GO`; historical Android geometry/preprocessing findings deferred и не блокируют Question Engine development.

## 7. Recovery/work rules

Перед новым PR читать с актуальной base ветки: `AGENTS.md`, `SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md`, `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`, оба state-файла, `docs/DOCUMENT_STATUS_INDEX.md`, `docs/CODEX_WORKFLOW.md`.

Каждый PR: ровно один Context Gate v1; оба state-файла обновляются; final checks относятся к exact final head; actual paths совпадают с Context Gate; mandatory security review; auto-merge запрещён.

## 8. PR #268 validation target

Перед Ready/merge проверить:

- base exact PR #266 final head;
- changed paths exactly match Context Gate;
- state files идентифицируют PR #268 и `question-engine-provider-parse-routing-v1`;
- next step — `question-engine-provider-ledger-reporting-v1`;
- route только `3.6 Flash → 3.5 Flash`, Pro отсутствует;
- 400/401/403 abort globally; 404/daily quota remain run-scoped unavailable;
- malformed outer/model/schema output получает bounded fallback и не semantic scoring;
- HTTP 200 body bounded до parse;
- daily detector не срабатывает на generic `perDay`/RPM;
- retry hints finite/bounded и structured RetryInfo не проигрывает меньшему header hint;
- обе модели получают bounded шанс в пределах per-model/global caps;
- prompt, target assertions, selected cases, corpus oracle и strict scorer семантически не меняются;
- focused tests и Python compilation pass на exact final code/test blobs;
- Markdown/JSON state согласованы;
- report/ledger/checkpoint/redaction work остаётся только следующему bounded PR;
- реальный Gemini run остаётся запрещён до завершения corrective chain и final Codex review.
