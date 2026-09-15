# OCR Project State & Continuity v0

Последнее обновление: 2026-09-15, PR #269, `question-engine-provider-ledger-reporting-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-provider-corrective-codex-review-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления проекта. Binding architecture/security/privacy documents задают обязательные границы; текущие `active_track` и `next_step_id` выбираются только state-файлами.

## 1. Current provider corrective chain

Provider experiment остаётся paused. Реальный Gemini run запрещён до одного финального combined Codex review всей corrective chain.

Relevant continuity:

- local run v3 после PR #261 дал первый usable semantic provider report: `9/10` cases, `12/33` exact assertions, `18/33` values, `18/33` states, `19/33` refs, `5/5` resolutions, `4` hard failures;
- PR #262 добавил provider-enforced structured output, но local run v4 получил `10/10` HTTP 400 из-за неправильного request field;
- PR #263 исправил GenerateContent request на `responseMimeType + responseJsonSchema`;
- local run v5 подтвердил request shape, но занял `1196.61s` и завершил только `3/10` cases; затем primary 3.6 упёрлась в per-model daily free-tier quota;
- PR #264 увеличил pacing до 30 секунд;
- PR #265 различил daily-quota 429 и short-window 429 и временно добавил Pro;
- provider audit после #265 выявил повторные запросы к exhausted model, неверную обработку auth errors, malformed-output gaps, unbounded response read, слишком широкий quota detector, retry-hint defects, отсутствие attempt provenance и слабую report/checkpoint integrity;
- владелец решил не использовать `gemini-3.1-pro-preview` через API до подтверждения бесплатного API tier.

PR #266 закрывает первую bounded-часть:

- executable route только `gemini-3.6-flash → gemini-3.5-flash`;
- unsupported model override блокируется до provider request;
- confirmed daily quota и stable HTTP 404 model-unavailable запоминаются на весь run;
- следующие cases пропускают remembered unavailable model;
- HTTP 401/403 считаются global auth/permission failure и прекращают run без model fallback;
- восстановлены batch-audit marker и compact recovery anchors, потерянные ранней версией draft.

PR #268 закрывает вторую bounded-часть:

- HTTP 200 response body bounded до JSON parse;
- malformed outer JSON/envelope, malformed model JSON и local schema-invalid output не идут в semantic scorer и получают bounded fallback;
- JSON `NaN/Infinity` и non-finite values отклоняются;
- structured fields, включая `resolution.outcome`, валидируются fail-closed;
- malformed nested provider error metadata не ломает quota/retry parser;
- structured `QuotaFailure`/`RetryInfo` поддерживаются;
- daily detector использует narrow daily identifiers вместо generic `perDay`;
- retry hints только finite/non-negative, используется наиболее консервативный valid hint;
- retry/routing budget разделён на per-model cap `2` и global cap `4`;
- prompt semantics, selected ten cases, target assertions, corpus oracle и strict semantic scorer не меняются.

PR #269 закрывает третью и последнюю bounded-часть:

- каждая provider попытка получает attempt-ledger запись с `case_id`, model, attempt number, status, duration и bounded failure/http/wait metadata;
- attempt ledger не хранит prompt, contract text, raw provider body, API key или authorization header;
- report отдельно показывает attempts/successes по моделям и provider failure classes, не смешивая их с semantic score;
- `model_route` отражает фактический route; при single-model override `fallback_model = null`, поэтому ложного fallback label нет;
- recursive redaction удаляет API key даже если hostile provider вернёт его внутри nested structured output;
- report JSON сериализуется с `allow_nan=False`;
- initial/partial checkpoints сохраняются локально; global provider failure checkpointed перед propagation, internal abort checkpointed с отдельным status;
- если все модели run-scoped unavailable, run завершается `ABORTED_ROUTE_EXHAUSTED` до следующего 30-second sleep и не получает ложный `COMPLETED`;
- TXT и JSON сначала полностью stage-ятся; TXT публикуется первым, canonical JSON — последним как terminal commit marker;
- реальных Gemini requests для проверки PR #269 не выполнялось.

Старый PR #267 (`Add robust Flash fallback and attempt ledger`) superseded: он был основан на старом head #266, превышал size guidance и не должен мержиться. Его функциональность заменена bounded chain `#268 + #269` поверх исправленного #266.

## 2. Canonical next step

`next_step_id = question-engine-provider-corrective-codex-review-v1`

Следующий и единственный permitted step — один combined Codex review цепочки:

`main 00f2ebc7… → #266 → #268 → #269`

Review не должен менять код, вызывать Gemini, расходовать quota или создавать новый PR. Он проверяет закрытие конкретных provider-audit findings и governance каждого bounded PR.

Если review не находит воспроизводимого `HIGH/BLOCKER` или binding-governance violation, наблюдения/LOW не открывают новый corrective loop: #266, #268 и #269 последовательно мержатся обычным manual merge, после чего evidence gate возвращается к `question-engine-security-provider-experiment-local-run-v6`.

Если найден конкретный воспроизводимый HIGH/BLOCKER, исправляется только этот bounded defect.

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

Local API key читается из environment/Desktop `.env.local`; `.env.local` игнорируется repository. Provider host остаётся fixed Google GenerateContent host. Новых dependencies, workflows, permissions, provider hosts, production storage, OCR/Android/serverless paths или statutory runtime в corrective chain нет.

Route после #269 остаётся только `gemini-3.6-flash → gemini-3.5-flash`; timeout 120 секунд; pacing 30 секунд; per-model attempt cap 2; global attempt cap 4; HTTP-200 response body bounded до local parse. Pro отсутствует в executable route.

Repository остаётся pre-production. Production use с real contracts blocked до отдельно проверенных consent, authorization, encryption/key lifecycle, Israel-only restricted-data processing, deletion/retention, logging, provider terms, abuse/resource controls и incident response.

## 5. Audit continuity

Последний завершённый Question Engine batch audit recovery marker:

- дата: `2026-09-08`;
- start SHA: `cbbb8e0905c1fda8610260d4046b51952a9f636c`;
- end SHA: `ee66e0063e270abd5eb7992f2be73c89dbec3a5d`;
- principal PR range: `#234–#250`;
- outcome: `CORRECTIVE PR REQUIRED`;
- privacy/security regression в этом range не был отмечен.

Отдельный provider audit после #265 относится только к provider experiment corrective chain. Старый опубликованный API key уже заблокирован Google и не является новым blocker текущих PR. Новый/live credential в corrective diff не допускается.

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

## 8. PR #269 validation target

Перед Ready/merge проверить:

- base exact PR #268 final head;
- changed paths exactly match Context Gate;
- state files идентифицируют PR #269 и `question-engine-provider-ledger-reporting-v1`;
- next step — `question-engine-provider-corrective-codex-review-v1`;
- route только `3.6 Flash → 3.5 Flash`, Pro отсутствует;
- attempt ledger содержит только non-sensitive bounded metadata и корректно разделён по cases;
- per-model attempts/successes/failure classes отделены от semantic metrics;
- recursive key redaction применяется до persistence/rendering;
- exhausted route aborts before additional pacing/request and не помечается `COMPLETED`;
- global/internal terminal failure имеет сохранённый partial checkpoint;
- canonical JSON terminal status публикуется только после companion TXT;
- single-model override не получает fake fallback label;
- prompt, target assertions, selected cases, corpus oracle и strict scorer семантически не меняются;
- focused tests и Python compilation pass на exact final code/test blobs;
- implementation/test additions остаются ниже normal 400-line hard limit;
- Markdown/JSON state согласованы;
- реальный Gemini run остаётся запрещён до final combined Codex review.
