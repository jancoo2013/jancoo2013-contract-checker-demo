# OCR Project State & Continuity v0

Последнее обновление: 2026-08-20, Draft PR #230, `surya-cloud-run-cpu-benchmark-v1`.

Активный трек: `serverless-gpu-ocr-benchmark`.

Канонический следующий production-шаг после PR #230 не меняется: `surya-raw-fullframe-gpu-execution-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления privacy/OCR-проекта. Архитектурные документы задают обязательные границы, но текущий `next_step_id` выбирается только state-файлами.

## Current change — Draft PR #230 Cloud Run CPU latency experiment

PR #230 — явно разрешённое product-owner benchmark-исключение после того, как Google Batch T4 provisioning оставался в `SCHEDULED` более восьми минут до начала OCR. Оно проверяет только возможность использовать Surya 2 GGUF на CPU Cloud Run в Israel region `me-west1` и не заменяет каноническую serverless-GPU архитектуру.

Bounded experiment добавляет:

- CPU-only container с pinned llama.cpp commit `a30273376ef669023334fc20ad02ae4ed8196a65`;
- pinned Surya GGUF revision `6a3a4c30e5e74446d4f8b6afd05b2f2da970f470`, fixed SHA-256 verification двух model artifacts и model files, встроенные в image на build stage;
- runtime offline mode без Hugging Face/model downloads;
- один loopback-only `llama-server` и один reused Surya engine для cold/warm requests;
- standard-library HTTP wrapper с `GET /health` и одним bounded raw-PNG `POST /benchmark`;
- aggregate-only response с status/error code, page/success/block/recognized-character counts и OCR/worker/request/model-startup timing;
- opaque temporary input, explicit `finally` cleanup, safe bounded errors и отключённый request/backend content logging;
- Cloud Run template только для `me-west1`: 8 vCPU, 16 GiB, min instances 0, max instances 1, concurrency 1, startup CPU boost, no GPU и no cross-region fallback;
- static contract tests для build scope/pins, runtime offline boundary, region/resources, loopback binding, input/output bounds, startup bound, cleanup и engine reuse.

Разрешены только synthetic, public, owner-controlled redacted или иным образом non-identifying benchmark pages. PR не добавляет Android upload, production auth, encryption/key management, PII masking, Gemini/legal-analysis call, permanent storage, billing, deployment workflow или production CPU architecture decision.

Реальный Cloud Run deployment ещё не выполнялся. Cold/warm latency, OCR CPU performance, startup timing, RAM/OOM, provider logs, cleanup при termination, instance teardown, retention и actual regional behavior остаются unverified. Поэтому PR #230 должен оставаться Draft; runtime validation является blocker для Ready.

`active_track` и `next_step_id` намеренно не меняются. Канонический следующий шаг остаётся `surya-raw-fullframe-gpu-execution-v1`.

## Previous change — PR #227 PII block purpose and sanitized-image handoff

PR #227 — документационное product-direction исключение, явно разрешённое product owner. Оно не меняет активный serverless-GPU трек и не реализует новый runtime.

Зафиксированная цель PII-блока:

```text
raw full-page contract image
→ Surya/OCR/layout as transient trusted-boundary evidence
→ locate all sensitive regions
→ associate party/field role where safely possible
→ irreversibly remove original sensitive pixels
→ render stable semantic placeholders
→ privacy validation
→ sanitized full-page images
→ approved multimodal legal-analysis model
```

Ключевые решения:

- Surya остаётся serverless-GPU OCR/layout candidate внутри trusted processing boundary; перенос Surya на смартфон не является текущим направлением;
- цель PII-блока — не идеальная полная транскрипция договора до каждой буквы и знака препинания, а полный privacy coverage чувствительных областей;
- ошибки OCR в не-PII юридическом слове сами по себе не являются privacy failure; пропуск чувствительной области является;
- при известной роли чувствительное значение должно заменяться стабильным semantic marker, например `[АРЕНДОДАТЕЛЬ]`, `[АРЕНДАТОР 1]`, `[АРЕНДАТОР 2]`, `[ID АРЕНДАТОРА 1]`, а не оставляться как немаркированный белый прямоугольник;
- исходные PII pixels сначала удаляются необратимо, и только после этого поверх очищенного raster рисуется semantic placeholder;
- одна и та же сторона договора должна иметь один и тот же marker на всех страницах одного contract job;
- если область явно sensitive, но роль не удаётся определить безопасно, допустим generic safe placeholder; если неясно, полностью ли закрыто PII, downstream handoff блокируется;
- development overlay может оставаться полупрозрачным для визуальной проверки покрытия, но любой artifact, который может покинуть trusted worker, должен содержать opaque irreversible pixel replacement;
- privacy-validated sanitized full-page images являются primary downstream representation для approved multimodal legal-analysis model;
- raw OCR JSON/text остаётся restricted transient worker state и не является canonical LLM payload;
- sanitized structured text/evidence разрешается производить после privacy validation, если это понадобится deterministic validation/citation layer;
- PR #227 не добавляет runtime mask renderer, PII detector, provider, endpoint, dependency, upload path, LLM call или production privacy claim.

`active_track` и `next_step_id` намеренно не меняются. Следующий bounded implementation остаётся `surya-raw-fullframe-gpu-execution-v1`: выполнить существующий PR #226 worker на explicitly approved GPU infrastructure с approved non-identifying full-frame pages и собрать реальные quality/layout/PII-localization, latency, GPU/VRAM/OOM, cost, log hygiene, cleanup, region и retention evidence. Этот benchmark всё ещё не должен строить production masking или downstream LLM integration.

## Previous change — PR #226 Surya raw-fullframe benchmark worker

PR #226 реализует первый bounded Surya 2 worker поверх уточнённого PR #225 model-neutral contract, но пока не выполняет реальный GPU/provider benchmark.

Текущий worker:

```text
ordered local benchmark pages
→ encoded-size/page-count bounds
→ image header/dimension bounds
→ EXIF orientation normalization only
→ complete full-frame raster
→ Surya 2 full-page OCR in memory
→ validate image_bbox / reading order / bbox / confidence / output sizes
→ model-neutral transient page results
→ persist only non-sensitive aggregate metrics
```

Границы PR #226:

- отдельный benchmark dependency pin: `surya-ocr==0.22.1`; это не application dependency;
- максимум 10 страниц, 48 MiB encoded per page, 256 MiB encoded per job, long side <=8192, <=32M decoded pixels per page и <=160M pixels per job;
- максимум 4096 blocks/page, 200000 normalized chars/block и 2000000 chars/page;
- порядок страниц задаётся самим ordered input и превращается в opaque `p0000...` + contiguous `page_index`;
- до OCR выполняется только EXIF orientation normalization; deskew, crop, perspective correction и grayscale не являются prerequisite;
- worker использует current Surya 2 Python API (`SuryaInferenceManager` + `RecognitionPredictor`) и full-page OCR;
- Surya startup/request timeout фиксируется в 600 s, keep-alive выключен, retries в worker отсутствуют;
- raw OCR/layout остаётся только transient in-memory result; CLI выдаёт только aggregate counts/status/timing и не пишет raw OCR/geometry;
- exact per-page coverage сохраняется и при `partial_failure`; malformed geometry/confidence/order/output fails closed;
- backend exception text не выходит в result/error payload;
- focused tests используют synthetic injected engine, поэтому реальный Surya package/model/backend в repository validation не запускался;
- PR не добавляет Android upload/handoff, remote endpoint/provider configuration, production encryption/key management, PII implementation, Gemini/legal-analysis integration или persistent raw storage.

Следующий bounded step `surya-raw-fullframe-gpu-execution-v1` должен уже выполнить worker на explicitly approved GPU infrastructure и approved non-identifying full-frame test pages. Нужно измерить Hebrew OCR/layout quality, cold/warm latency, queue delay, GPU/VRAM/OOM, billed seconds/cost, log hygiene, backend cleanup и фактические region/retention свойства среды. Только после этого evidence решаем, нужен ли вообще deskew/crop/grayscale в OCR path.

Android audit findings #2 (session/cache atomicity) и #3 (stale TypeScript crop-result contract) остаются deferred и должны быть закрыты до повторного использования Android preprocessing path как OCR input/production handoff.

## Previous change — PR #225 worker contract corrective after Codex batch audit

После merge PR #224 product owner запустил cold-start Codex batch audit merged range after `b9527f046a0225c0e80f3f511e15b9a8b1eb0ea3` through `eee02d32a85cf867ac84b2141e29d8f57a0fabe4`, covering merged PRs #216, #217, #218, #219, #220, #221, #223 и #224; unmerged PR #222 был явно исключён.

Audit outcome: `CORRECTIVE PR REQUIRED`, blocking findings: none.

Codex вернул три corrective findings:

1. model-neutral worker contract требовал важных implementation guesses по page order/correlation, exact result coverage, error envelopes, EXIF coordinate semantics и transient raw-OCR evaluation boundary;
2. Android prepared-document session/cache lifecycle не атомарен при overlapping selection/prepare operations;
3. TypeScript `PreparedDocumentResult` всё ещё рекламирует исторический `cropped_grayscale` / non-null `cropBoxSource`, хотя текущий native prepared runtime больше этого не возвращает.

Product-owner решение: PR #225 закрывает только finding #1 перед Surya benchmark. Findings #2–#3 остаются deferred, потому что raw-fullframe Surya benchmark не использует Android preprocessing path; их нужно закрыть до того, как этот Android path станет источником OCR job или production handoff.

PR #225 уточняет только `docs/SERVERLESS_OCR_WORKER_CONTRACT_V1.md`:

- добавляет отдельный `page_index` как authoritative document-page order и оставляет array position неавторитетным;
- требует unique `job_id`, unique `page_id`, unique contiguous `page_index = 0..N-1` и exact `(page_id, page_index)` correlation;
- требует exact result-set coverage для всех accepted jobs: без duplicate/extra/missing/remapped pages;
- определяет единый bounded non-sensitive error envelope и точные job/page status semantics, включая `not_run` и deterministic no-success precedence;
- фиксирует stable bbox space как полный raster после EXIF orientation normalization, до model-specific resize; любой inference resize должен map geometry обратно;
- `width_px` / `height_px` относятся к post-EXIF-normalization full frame; malformed/unsupported orientation fails closed;
- contract v1 не требует crop, deskew, perspective correction или grayscale для первого raw-fullframe benchmark;
- определяет permitted transient evaluation: automated quality evaluator внутри того же trusted process либо owner-controlled local ephemeral display на approved non-identifying fixtures; remote/provider result не может сохранять raw OCR text/layout;
- сохраняет Israel-only production invariant и запрет automatic cross-region fallback;
- не добавляет Android code, OCR engine, provider SDK/endpoint, network destination, dependency, permission, workflow, production upload, PII implementation, Gemini/legal-analysis call или persistent raw storage.

После merge PR #225 следующий bounded implementation — `surya-raw-fullframe-benchmark-worker-v1`: начать с ordinary full-frame approved benchmark photographs/pages после EXIF orientation normalization only, без обязательного deskew/crop/perspective/grayscale preprocessing, и только при concrete OCR evidence решать, требуется ли какое-либо дополнительное image preprocessing.

## Previous change — PR #224 model-neutral serverless OCR worker contract

После merge PR #223 product owner отдельно пересмотрел ценность ещё одного Android preprocessing device smoke. Отдельный smoke сейчас сознательно пропускается: destructive crop удалён; применение grayscale уже наблюдалось на устройстве; малый deskew порядка единиц градусов практически не оценивается по текущему уменьшенному preview; а доступная реальная выборка фотографий договоров в целом снята достаточно ровно и не даёт полезного набора плохих кадров для дополнительного тюнинга.

Это решение означает приоритизацию, а не утверждение о полной device-validation preprocessing. Трек может быть reopened при конкретном наблюдаемом дефекте, crash/OOM, потере содержимого, либо если OCR benchmark даст evidence, что входное preprocessing систематически ухудшает распознавание. Grayscale пока остаётся текущей implementation detail и не является отдельным вопросом оптимизации или A/B/C-исследования.

PR #224 фиксирует model-neutral boundary перед первой GPU OCR реализацией:

```text
bounded OCR job
→ candidate-specific worker adapter
→ OCR engine
→ validate candidate output
→ normalize text/layout evidence
→ bounded worker result
```

Границы PR #224:

- добавляет `docs/SERVERLESS_OCR_WORKER_CONTRACT_V1.md` как benchmark-only contract;
- определяет versioned job/page identifiers, bounded page metadata, text/block/line result shape, pixel-space bbox, confidence semantics, terminal statuses и non-sensitive benchmark metrics;
- raw OCR text/layout определён как transient internal result: job/page statuses включают явный `partial_failure`, а raw result нельзя трактовать как сохраняемый provider/client result;
- требует finite limits для encoded bytes, dimensions/pixels, page count, execution time, memory/VRAM where observable, output size, concurrency и retries;
- raw image bytes и raw OCR text остаются restricted transient material и не могут попадать в logs/CI/artifacts;
- repository benchmark fixtures могут быть только synthetic, public или owner-controlled redacted;
- Surya остаётся первым benchmark candidate, но stable contract не содержит Surya/provider SDK types;
- не добавляет Android upload, OCR engine implementation, network destination, provider SDK, queue/storage implementation, production auth/encryption/key management, PII pipeline, Gemini/legal analysis, dependencies, permissions или workflows;
- future production processing по-прежнему подчиняется `SECURITY.md`: restricted material только в явно approved infrastructure physically located in Israel, без automatic cross-region fallback.

Первоначально после PR #224 был записан `surya-serverless-benchmark-worker-v1`; PR #225 уточняет этот next step до raw-fullframe-first benchmark после Codex corrective.

## Previous change — PR #223 disable physical document crop

После нескольких concrete crop-дефектов product direction изменён: destructive crop больше не является частью production preprocessing. Ошибка boundary/crop detector не должна необратимо удалять край страницы, подпись, примечание или другое содержимое до OCR.

PR #223 меняет только финальный Android prepared-document consumer и binding architecture wording:

```text
local photo
→ bounded orientation / geometry evidence
→ accepted deskew when sufficiently trusted
→ full-frame preservation
→ grayscale (пока сохраняется)
→ OCR handoff later
```

Runtime semantics после PR #223:

- `accepted` и `rotation_only` больше не выполняют physical crop и возвращают `deskewed_full_frame_grayscale`;
- accepted deskew рендерится на expanded white canvas, чтобы сохранить полный oriented source frame;
- `full_frame_fallback` остаётся 0° и возвращает `full_frame_grayscale_fallback`;
- `cropBoxSource` во всех prepared results равен `null`;
- producer-generated `safeCropBounds`, content-r…5641 tokens truncated…р файла переиспользует только существующий local Android picker method; geometry handler не вызывает `recognizeAsync`;
- UI вызывает существующие `buildPreviewAsync`, `estimateAngleAsync` и `applyFullFrameDeskewAsync` без изменения native geometry implementation;
- исходный selected URI не передаётся напрямую в React Native `<Image>` до geometry validation: UI показывает только уже validated/bounded module-owned grayscale `preview.png` с long side <=1800 px;
- full-frame result показывается из bounded module-cache `deskewed.jpg`;
- UI отображает source/preview dimensions, dominant text angle, requested deskew angle, confidence, accepted/rejected decision, rejection reasons, transform decision, applied rotation, output dimensions и fallback reasons;
- ошибки выводятся только как safe module/error message; page contents и URI path не логируются новым кодом;
- нет новых network requests, analytics, upload или backend вызовов в geometry handler;
- нет OCR/Tesseract recognition в geometry handler;
- нет новых dependencies/permissions/workflows;
- нет изменения native geometry thresholds/algorithms/resource bounds;
- frozen Python geometry implementation не меняется;
- persistence не добавляется: остаются только existing bounded app/module cache artifacts, уже определённые PR #211/#213.

Исторически state после PR #214 называл следующий manual gate `android-geometry-samsung-a55-manual-validation-v1`. Product contract не привязан к одной модели телефона.

## 1. Frozen Python document geometry block

Binding freeze contract:

`docs/DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`

Frozen geometry code baseline:

`7fe4bc88df2427ea90442f7b074c3cfe4e0de33a` — merge PR #209.

Frozen reference pipeline:

```text
source PIL image
→ bounded source size/mode/resource validation
→ EXIF orientation handling
→ bounded grayscale preview
→ local-contrast text/ink mask
→ bounded text-angle estimate
→ bounded content-region estimate
→ meaningful disconnected-content and deskew edge-loss guards
→ accepted-stage structural validation
→ full-resolution deskew + conservative crop only when fully trusted
→ otherwise full-frame fallback
→ DocumentGeometryNormalizationResult
```

Relevant corrective history:

- #203 / #206: wide and compact/fragmented disconnected-content fail-safes;
- #204 / #207: accepted-stage structural contract validation;
- #205 / #208: bounded resource accounting and supported-mode alignment;
- #209: meaningful source-edge deskew clipping fail-safe;
- #210: finite freeze/reopen contract.

The code-level freeze remains valid while Android preprocessing is ported. Android/product evidence reopens the frozen Python block only if it satisfies the explicit reopen criteria in `DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`.

## 2. Android preprocessing sequence

### Completed

`android-geometry-preview-contract-v1` — PR #211

- local bounded decode;
- EXIF normalization;
- exact <=1800 px grayscale preview;
- no geometry decision.

`android-geometry-angle-estimator-v1` — PR #212

- consumes only the bounded module-owned preview;
- creates bounded text/ink evidence;
- performs fixed ±12° projection search;
- returns angle/confidence/decision/reasons;
- no physical transform.

`android-geometry-full-frame-deskew-v1` — PR #213

- binds the active preview to the exact local source URI for the current module session;
- reruns and structurally validates native angle evidence before physical transform;
- accepted angle applies full-resolution deskew after EXIF normalization;
- expanded white canvas preserves the complete source frame;
- rejected/uncertain angle uses 0° full-frame fallback;
- no crop/UI/network/OCR.

`android-geometry-validation-ui-v1` — PR #214

- chooses one local photo through the existing picker;
- keeps geometry-selected source separate from legacy OCR/backend state;
- runs only the existing bounded native geometry preview/angle/full-frame transform path;
- renders only the validated bounded source preview before showing the full-frame result;
- shows angle/confidence/decision/reasons and physical-transform metadata;
- adds no upload, OCR recognition, network destination or persistence beyond bounded app cache.

`android-geometry-content-region-bounds-v1` — PR #215

- consumes only module-owned bounded preview input;
- recomputes native angle evidence internally;
- builds content-region mask in <=1800 px preview space;
- performs candidate-only preview deskew, line-band extraction, dominant-band filtering, candidate bounds and confidence/reasons;
- rejected angle fails to candidate-level full-frame fallback;
- no safe crop authorization and no physical crop.

`android-geometry-preview-snapshot-integrity-v1` — PR #216

- closes the post-merge P2 snapshot-consistency finding from PR #215;
- decodes one bounded preview snapshot and uses it for both angle and candidate content-region analysis;
- prevents angle/mask evidence from being assembled from two different replacements of the same `preview.png` path;
- no public API or crop behavior change.

`android-geometry-validation-ui-controls-v1` — PR #217

- adds full-screen inspection for the existing bounded source preview and full-frame result;
- adds repeated-photo and reset controls for manual smoke testing;
- preserves the current result when the picker is canceled;
- changes no native geometry behavior.

`android-geometry-safe-crop-authorization-v1` — PR #218

- ports the remaining frozen crop-authorization guards into bounded Android preview space;
- returns `accepted + safeCropBounds` only when candidate, source-edge, nearly-full-frame and disconnected-content checks all pass;
- returns no physical crop and creates no new image artifact;
- establishes the safe producer contract consumed by the next physical preprocessing PR.

`android-document-preprocess-physical-crop-grayscale-v1` — PR #219

- consumes only internally recomputed safe-crop evidence from the current module-owned preview session;
- validates accepted crop structure before mutation;
- maps accepted crop to oriented full resolution with conservative independent-axis scaling;
- accepted path creates `cropped_grayscale`;
- non-accepted path originally created `full_frame_grayscale_fallback` with 0° rotation;
- development UI shows `prepared.jpg` as the target preprocessing result;
- no OCR/network/provider/dependency/permission/workflow change.

`android-document-preprocess-deskew-crop-decoupling-v1` — PR #220

- corrects the concrete device-smoke defect where `rotation_only` discarded an already accepted deskew when crop was rejected;
- `rotation_only` now creates `deskewed_full_frame_grayscale` on an expanded white canvas, with no crop;
- `full_frame_fallback` remains 0° full-frame grayscale;
- accepted crop behavior remains unchanged;
- no estimator/crop-guard tuning, perspective correction or new external data flow.

`android-document-boundary-crop-corrective-v1` — PR #221

- adds a separate bounded physical page-boundary crop recovery only for accepted-angle `rotation_only` caused solely by `content_touches_frame`;
- boundary evidence is derived from a <=900 px local source analysis, not from the text/ink crop candidate;
- requires contrast, central page occupancy, conservative padding, >=5% removable area, fixed-frame transform containment and dominant-line preservation;
- successful recovery returns existing `cropped_grayscale`; uncertainty preserves PR #220 `deskewed_full_frame_grayscale`;
- does not change normal SafeCropEstimator acceptance or any external data flow.

`android-document-disable-physical-crop-v1` — PR #223

- removes both the PR #221 boundary-recovery crop consumer and the older fully accepted SafeCrop physical crop consumer from `PreparedDocumentTransform`;
- keeps structural validation of upstream geometry evidence but does not use crop coordinates to mutate the image;
- routes `accepted` and `rotation_only` to expanded full-frame grayscale deskew with `cropBoxSource = null`;
- keeps rejected/uncertain deskew at 0° full-frame grayscale with `cropBoxSource = null`;
- leaves crop/boundary estimators available only as non-destructive advisory evidence;
- changes no OCR/network/provider/dependency/permission/workflow behavior.

### Audit status

Owner-requested bounded audit over Android geometry PR #211–#215:

- outcome: `BATCH AUDIT CLEAR`;
- blocking findings: none;
- corrective findings in that audit: none;
- coordinate/sign composition, candidate semantics, resource bounds and local-only boundary passed the stated finite checks;
- no complete final crop/grayscale real-device validation was performed.

A separate automatic post-merge Codex review then found the preview snapshot P2; PR #216 is the bounded corrective for that concrete integration issue.

Post-#224 Codex batch audit over merged PRs #216–#224 returned `CORRECTIVE PR REQUIRED` with no blocking findings. PR #225 closes worker-contract finding #1. Android session/cache atomicity and stale TypeScript crop-result contract findings remain deferred and must be resolved before Android preprocessing is reused as an OCR input path.

### Current preprocessing status — explicit product-owner prioritization

`android-document-preprocess-device-smoke-v1` is not the active next step after PR #223.

Product owner explicitly chose not to spend another iteration on a low-information manual phone smoke at this point. Existing device evidence already established that grayscale is applied and that small accepted deskew can execute; destructive crop has now been removed entirely. The available contract-photo sample is generally well captured, so searching for artificial bad cases is not an MVP priority.

This does not certify all Android devices or all capture conditions. Reopen preprocessing only on concrete evidence such as content loss, wrong orientation/deskew, crash/OOM, stale-page mixing, or OCR benchmark evidence pointing to a systematic preprocessing defect.

Grayscale remains in the current runtime path but is not an active optimization topic. No separate grayscale size/quality A/B test is required before the OCR benchmark.

## 3. Current product block — serverless GPU OCR benchmark

The approved serverless benchmark is active. PR #226 provides the first bounded raw-fullframe Surya worker; PR #227 only clarifies what that OCR evidence is ultimately for. Neither establishes production OCR/PII safety, GPU fit, latency, cost, or provider/privacy behavior.

After merge PR #227, `surya-raw-fullframe-gpu-execution-v1` must:

1. run the PR #226 worker on explicitly approved GPU infrastructure;
2. start with ordinary full-frame approved benchmark photographs/pages after EXIF orientation normalization only;
3. not require deskew, crop, perspective correction or grayscale preprocessing;
4. use approved non-identifying material for repository/automation evidence and obey the binding restricted-data region gate for any sensitive material;
5. record Surya/package/model/backend revision and concrete execution limits;
6. measure printed Hebrew/layout quality to the extent needed for PII localization/document structure, plus names/IDs/phones/emails/addresses/signature/handwriting behavior on approved fixtures where applicable;
7. measure cold start, warm execution, queue delay, one-page and multi-page latency, GPU/VRAM, OOM behavior, billed seconds and estimated cost;
8. inspect log/output hygiene and backend cleanup after success/failure/timeout;
9. verify actual regional and retention properties before making any sensitive-data claim;
10. compare OCR/layout evidence against the source and decide whether any additional preprocessing has demonstrated value;
11. still add no production Android upload, production PII masks, multimodal legal-analysis call or permanent raw-document storage.

Surya remains a benchmark candidate, not a production commitment. If raw-fullframe quality is materially usable for PII localization/document structure, deskew/crop/grayscale must not become mandatory in the OCR path without concrete contrary evidence; existing geometry work can instead support later capture-quality/advice behavior.

## 4. Active target pipeline

```text
raw phone photos
→ minimal client-side input handling (EXIF/orientation; no mandatory deskew/crop/grayscale before first OCR benchmark)
→ encryption
→ bounded asynchronous serverless job
→ GPU worker decrypts in volatile memory
→ full-page Hebrew OCR/layout as transient localization evidence
→ server-side PII detection + party/field role association
→ irreversible pixel replacement + stable semantic placeholders
→ privacy validation
→ sanitized full-page images
→ approved multimodal LLM legal-risk analysis
→ optional post-privacy deterministic evidence extraction / Python validation
→ Russian report
→ deletion of raw and transient job material
→ optional persistent storage of sanitized final report under exact account authorization
```

Tesseract full-page OCR remains NO-GO and cannot return as active fallback. Historical device testing does not make the Android implementation device-model-specific.

## 5. Review and merge policy

GitHub Actions are best-effort diagnostics and are not the normal merge gate.

Every PR requires before Ready/merge recommendation:

1. focused validation on the exact final branch version when applicable;
2. assistant final-diff self-audit for scope/state/raw data/credentials/generated files;
3. mandatory `SECURITY.md` review with exactly one `Security review: PASS` or blocking verdict;
4. explicit product-owner merge decision.

Individual Codex review is not required per PR. Codex is used for bounded periodic/targeted audits.

## 6. Privacy and security boundary

Restricted raw/transient material may exist only on the user device, encrypted transport, approved encrypted short-lived job storage when needed, volatile authorized worker memory and bounded transient worker files when unavoidable and automatically deleted.

Original images, raw OCR and PII-bearing payload may enter only explicitly approved infrastructure physically located in Israel. Any unapproved endpoint or region must fail closed before upload/job creation; automatic fallback outside Israel is prohibited.

Raw images/raw OCR are prohibited in Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable and unrelated services. Only privacy-validated sanitized derivatives may proceed to legal analysis.

Semantic placeholders do not weaken the redaction rule: original sensitive pixels must be irreversibly removed before marker rendering, and no recoverable original value may survive in alpha, metadata, overlays, caches, alternate frames, hidden text or debug payloads.

Any future Android preprocessing validation using real selected photos remains local to the device and must not log/export page contents. A separate phone smoke is not currently required by the canonical next step.

Production remains blocked until consent, authentication, authorization, key lifecycle, Israel-only provider behavior, retention/deletion, log scrubbing, cleanup, backup lifecycle, legal review, abuse controls and incident response are implemented и verified.

## 7. Recovery/work rules

Before a new privacy/OCR branch:

1. read current binding sources from `main`, including `SECURITY.md`;
2. check overlapping open PRs;
3. publish one exact Context Gate v1 before implementation;
4. implement only the declared bounded step;
5. update both state files after the actual PR number exists;
6. run final validation on the exact final head SHA;
7. perform final-diff self-audit and mandatory security review;
8. do not merge without explicit owner decision.

Do not use the abandoned experimental Android geometry branch as implementation input. Each Android preprocessing layer starts from merged `main` and the immediately preceding bounded contract only.

Last full repository cold-start audit: PR #177 after merge PR #176.

Last focused Python geometry audit: Codex at `876e49bceb0136af6ee851a2656aaf689d72e545`; concrete source-edge blocker corrected by PR #209; finite stop/freeze criteria formalized by PR #210.

Last targeted Android geometry audit: owner-requested audit over PR #211–#215 at head `b9527f046a0225c0e80f3f511e15b9a8b1eb0ea3`, outcome `BATCH AUDIT CLEAR`; later automatic review P2 snapshot finding corrected by PR #216.

Last periodic Codex batch audit: after `b9527f046a0225c0e80f3f511e15b9a8b1eb0ea3` through `eee02d32a85cf867ac84b2141e29d8f57a0fabe4`, merged PRs #216, #217, #218, #219, #220, #221, #223, #224; outcome `CORRECTIVE PR REQUIRED`, blocking findings none. PR #225 addresses finding #1; Android findings #2–#3 remain deferred as recorded above.

Frozen Python geometry code baseline: `7fe4bc88df2427ea90442f7b074c3cfe4e0de33a`.

Current PR: Draft #230 `surya-cloud-run-cpu-benchmark-v1`.

Canonical next production step remains `surya-raw-fullframe-gpu-execution-v1`; PR #230 is an experimental CPU alternative and must not replace it without a later product-owner decision supported by real benchmark evidence.
