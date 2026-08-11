# OCR Project State & Continuity v0

Последнее обновление: 2026-08-11, PR #216, `android-geometry-preview-snapshot-integrity-v1`.

Активный трек: `android-geometry-validation`.

Следующий bounded-шаг после merge PR #216: `android-geometry-safe-crop-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления privacy/OCR-проекта. Архитектурные документы задают обязательные границы, но текущий `next_step_id` выбирается только state-файлами.

## 0. Изменение PR #216 — Android preview snapshot integrity corrective

После merge PR #215 owner-requested targeted audit Android geometry PR #211–#215 вернул `BATCH AUDIT CLEAR`: blocking/corrective findings не было, candidate content-region logic, coordinate/sign composition, local-only boundary и bounded resources были признаны согласованными в заявленном finite scope.

После merge, отдельный автоматический Codex review PR #215 обнаружил конкретный P2 integration defect: `estimateContentRegionAsync(previewUri)` сначала открывал module-owned `preview.png` для angle estimation, а затем повторно открывал тот же переиспользуемый путь для content-region mask. При замене `preview.png` другим `buildPreviewAsync` между двумя чтениями angle и bounds теоретически могли относиться к разным страницам.

PR #216 исправляет только этот дефект:

```text
module-owned preview.png
→ decode once into one bounded in-memory Bitmap
→ angle estimation from that Bitmap
→ <=1800 content-region mask from that same Bitmap
→ candidate region result
```

Границы PR #216:

- публичный Expo/TypeScript API не меняется;
- `estimateAngle(previewUri)` сохраняет прежний внешний контракт;
- добавлен только внутренний `estimateAngle(Bitmap)` для повторного использования уже декодированного snapshot;
- `estimateContentRegionAsync` больше не выполняет второе чтение `preview.png` между angle и content-region mask;
- bitmap освобождается после завершения обеих стадий;
- нет safe-crop authorization или physical crop;
- нет OCR/Tesseract recognition, upload, backend/network destination, analytics, новых dependencies/permissions/workflows, provider/serverless изменений или persistence;
- frozen Python geometry implementation не меняется.

После merge PR #216 следующий implementation step возвращается к ранее запланированному `android-geometry-safe-crop-v1`.

## 0.1. Изменение PR #215 — Android content-region candidate bounds

PR #215 добавляет только кандидатную оценку области содержимого поверх уже существующего Android geometry path:

```text
module-owned bounded preview
→ native angle evidence
→ local-contrast text/ink mask in <=1800 px preview space
→ preview deskew for analysis only
→ line bands
→ dominant bands
→ candidate content bounds + confidence/reasons
→ no crop authorization or physical crop
```

Границы PR #215:

- добавлен `estimateContentRegionAsync(previewUri)` в существующий local Expo/Kotlin geometry module;
- JS не передаёт произвольный angle contract: content-region path сам повторно получает native `estimateAngle` evidence;
- accepted angle используется только для bounded preview-space анализа;
- rejected angle возвращает candidate-level `full_frame_fallback`;
- line-band/dominant-band thresholds и confidence formula следуют frozen Python `content_region_bounds.py` для этой candidate-части;
- source-edge loss guard, disconnected-content outside-crop guard, conservative padding, nearly-full-frame guard, финальная safe-crop authorization и full-resolution crop mapping намеренно не входят в PR #215;
- никакой crop в PR #215 физически не выполняется;
- Android angle-estimator по-прежнему использует 900 px analysis mask; content-region candidate использует тот же mask builder с bounded long side до 1800 px;
- implementation additions до state/docs: 291 строк, то есть остаются внутри target <=300;
- нет OCR/Tesseract recognition, upload, backend/network destination, analytics, новых dependencies/permissions/workflows, provider/serverless изменений или persistence за пределами уже существующего module cache;
- frozen Python geometry implementation не меняется.

Owner-requested targeted Codex audit по PR #211–#215 вернул `BATCH AUDIT CLEAR`. Последующий отдельный post-merge review finding по snapshot consistency исправляется PR #216 и не меняет остальные выводы audit.

## 0.2. Изменение PR #214 — Android geometry development validation UI

После PR #211 Android validation path имеет локальный bounded grayscale preview, после PR #212 — native angle/confidence/decision, а после PR #213 — bounded full-resolution full-frame deskew/fallback. PR #214 добавил development UI поверх этих native контрактов:

```text
choose one local photo
→ build bounded native preview
→ show bounded source preview + native angle/confidence/decision/reasons
→ run bounded native full-frame deskew/fallback
→ show full-frame output for visual comparison
→ no OCR call, upload or external persistence in this geometry path
```

Границы PR #214:

- geometry panel находится сверху существующего mobile development app;
- geometry-selected photo хранится в отдельном UI state и не передаётся в legacy OCR/backend handlers;
- выбор файла переиспользует только существующий local Android picker method; geometry handler не вызывает `recognizeAsync`;
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

Исторически state после PR #214 называл следующий manual gate `android-geometry-samsung-a55-manual-validation-v1`. Product owner затем явно изменил последовательность: сначала перенести оставшуюся safe content-region/crop часть Android geometry, сделать bounded Codex audit и только затем проводить real-device validation. Название старого historical step не является требованием фиксироваться на одной модели телефона.

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

The code-level freeze remains valid while Android validation proceeds. Android/product evidence reopens the frozen Python block only if it satisfies the explicit reopen criteria in `DOCUMENT_GEOMETRY_FREEZE_CRITERIA_V1.md`.

## 2. Android geometry validation sequence

The Android validation implementation is intentionally split before coding each layer.

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

### Audit status

Owner-requested bounded audit over Android geometry PR #211–#215:

- outcome: `BATCH AUDIT CLEAR`;
- blocking findings: none;
- corrective findings in that audit: none;
- coordinate/sign composition, candidate semantics, resource bounds and local-only boundary passed the stated finite checks;
- no real-device validation was performed.

A separate automatic post-merge Codex review then found the preview snapshot P2 described above; PR #216 is the bounded corrective for that concrete integration issue.

### Next — safe crop

`android-geometry-safe-crop-v1`

This step will add the remaining safety contract before any crop can be authorized or applied:

- source-edge loss guard;
- conservative padding / nearly-full-frame guard;
- disconnected meaningful-content outside-crop guard;
- structural validation of accepted candidate evidence;
- bounded mapping from preview crop to full-resolution deskew output;
- physical crop only when all guards pass;
- otherwise full-frame fallback.

A separate final UI integration step will display the actual final geometry result. Only after that should manual validation run on representative Android devices / real local photos. One available device may be used for the first smoke test, but the product contract is not tied to a single phone model.

Success standard for manual validation remains:

- accepted deskew/crop visibly improves alignment without obvious meaningful-content loss;
- uncertain/rejected cases preserve the full frame;
- angle sign is correct;
- crop never removes meaningful edge/header/footer/signature-like content in tested cases;
- no photo leaves the device during validation;
- concrete product failure is recorded rather than hidden by threshold tuning.

## 3. Deferred next product block — `serverless-gpu-ocr-viability-benchmark-v1`

The serverless benchmark remains approved but is temporarily deferred until the Android geometry validation gate above is completed.

When resumed, the benchmark must:

1. use one OCR candidate through a model-neutral worker contract;
2. use only synthetic, public or owner-controlled redacted repository test material;
3. measure Hebrew text/layout quality, cold start, warm execution, queue delay, multi-page latency, GPU/VRAM, OOM behavior, billed seconds and estimated cost;
4. verify absence of raw page content/raw OCR text in logs and retained metadata;
5. preserve scale-to-zero and bounded queue execution;
6. not add production Android upload, production encryption/key management, production PII masks, Gemini/legal-analysis calls, permanent storage or real-user-data claims.

Surya remains the first benchmark candidate, not a production commitment.

## 4. Active target pipeline

```text
raw phone photos
→ client-side capture-quality checks and geometry normalization
→ encryption
→ bounded asynchronous serverless job
→ GPU worker decrypts in volatile memory
→ full-page Hebrew OCR and layout extraction
→ server-side PII detection and irreversible image/text redaction
→ privacy validation
→ anonymized derivative and evidence blocks
→ approved LLM legal-risk analysis
→ Russian report
→ deletion of raw and transient job material
→ optional persistent storage of sanitized final report under exact account authorization
```

Tesseract full-page OCR on Samsung A55 remains NO-GO and cannot return as active fallback. That historical measurement does not make the Android geometry implementation device-model-specific.

## 5. Review and merge policy

GitHub Actions are best-effort diagnostics and are not the normal merge gate.

Every PR requires before Ready/merge recommendation:

1. focused validation on the exact final branch version when applicable;
2. assistant final-diff self-audit for scope/state/raw data/credentials/generated files;
3. mandatory `SECURITY.md` review with exactly one `Security review: PASS` or blocking verdict;
4. explicit product-owner merge decision.

Individual Codex review is not required per PR. Codex is used for bounded periodic/targeted audits. The owner-requested targeted audit after PR #215 has completed; PR #216 records the subsequent concrete P2 corrective before safe-crop work continues.

## 6. Privacy and security boundary

Restricted raw/transient material may exist only on the user device, encrypted transport, approved encrypted short-lived job storage when needed, volatile authorized worker memory and bounded transient worker files when unavoidable and automatically deleted.

Original images, raw OCR and PII-bearing payload may enter only explicitly approved infrastructure physically located in Israel. Any unapproved endpoint or region must fail closed before upload/job creation; automatic fallback outside Israel is prohibited.

Raw images/raw OCR are prohibited in Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable and unrelated services. Only sanitized derivatives may proceed to legal analysis.

The Android geometry validation sequence is stricter: selected real photos remain local to the device. It adds no network destination and must not log/export page contents.

Production remains blocked until consent, authentication, authorization, key lifecycle, Israel-only provider behavior, retention/deletion, log scrubbing, cleanup, backup lifecycle, legal review, abuse controls and incident response are implemented and verified.

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

Do not use the abandoned experimental Android geometry branch as implementation input. Each Android validation layer starts from merged `main` and the immediately preceding bounded contract only.

Last full repository cold-start audit: PR #177 after merge PR #176.

Last focused Python geometry audit: Codex at `876e49bceb0136af6ee851a2656aaf689d72e545`; concrete source-edge blocker corrected by PR #209; finite stop/freeze criteria formalized by PR #210.

Last targeted Android geometry audit: owner-requested audit over PR #211–#215 at head `b9527f046a0225c0e80f3f511e15b9a8b1eb0ea3`, outcome `BATCH AUDIT CLEAR`; later automatic review P2 snapshot finding corrected by PR #216.

Frozen Python geometry code baseline: `7fe4bc88df2427ea90442f7b074c3cfe4e0de33a`.

Current PR: #216 `android-geometry-preview-snapshot-integrity-v1`.

Next step after merge PR #216: `android-geometry-safe-crop-v1`.
