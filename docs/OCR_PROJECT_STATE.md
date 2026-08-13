# OCR Project State & Continuity v0

Последнее обновление: 2026-08-13, PR #223, `android-document-disable-physical-crop-v1`.

Активный трек: `android-document-preprocessing`.

Следующий bounded-шаг после merge PR #223: `android-document-preprocess-device-smoke-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления privacy/OCR-проекта. Архитектурные документы задают обязательные границы, но текущий `next_step_id` выбирается только state-файлами.

## Current change — PR #223 disable physical document crop

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
- producer-generated `safeCropBounds`, content-region и document-boundary evidence могут сохраняться для диагностики/advisory capture-quality, но не имеют права удалять source pixels;
- full-frame dimension/memory bounds сохраняются;
- OCR recognition, upload/backend/provider, network, dependencies, permissions, workflows и privacy boundary не меняются.

Следующий gate — `android-document-preprocess-device-smoke-v1`: на двух owner-controlled photographed contract sets проверить полное сохранение листа, accepted/rejected deskew behavior, grayscale, повторный выбор страниц без stale mixing и отсутствие crash/OOM. После успешного smoke сравнить Surya OCR на A) full frame as captured, B) full frame + deskew, C) full frame + deskew + grayscale; только после фактического результата решать вопрос grayscale и проектировать live capture-quality gate.

Ниже crop-ориентированные записи PR #218–#222 сохраняются как историческое описание прежней реализации и не являются текущим production contract.

## Previous change — PR #221 physical document-boundary crop corrective

Post-#220 real-device smoke подтвердил две части preprocessing на конкретной реально сфотографированной странице: grayscale появился, а accepted deskew около 1° реально применился. При этом crop снова не сработал вообще, хотя product owner визуально оценил внешний фон примерно в 15% кадра. Upstream text/content path оставался `rotation_only` из-за `content_touches_frame`, поэтому полезная обрезка физического листа не была разрешена.

PR #221 добавляет отдельное, очень узкое physical document-boundary evidence только для этого concrete state:

```text
angle accepted
+ upstream decision = rotation_only
+ единственная причина = content_touches_frame
→ bounded <=900 px physical-page boundary analysis
→ center-vs-corner luminance contrast
→ row/column page occupancy around frame center
→ conservative boundary padding
→ >=5% removable-area requirement
→ map boundary through the same fixed-frame deskew matrix
→ require >=90% dominant line bands contained, with at most one outlier
→ if all checks pass: fixed-frame deskew + boundary crop + grayscale
→ otherwise: keep PR #220 expanded full-frame deskew + grayscale
```

Границы PR #221:

- новый `DocumentBoundaryEstimator` анализирует только уже локальный oriented source bitmap; временный analysis bitmap ограничен long side <=900 и освобождается до full-resolution output allocation;
- document boundary определяется независимо от text/ink candidate: paper-vs-background evidence строится по яркости центральной области и углов кадра, затем по occupancy строк/столбцов;
- требуется как минимум два согласованных corner-background samples с luminance contrast >=20;
- page candidate должен занимать не менее 50% каждой оси, после padding обязан оставлять не менее 5% площади кадра действительно удаляемой;
- boundary crop переводится через тот же Android deskew matrix; если mapped rectangle выходит за fixed frame, crop не разрешается;
- финальный consumer дополнительно требует сохранения dominant line bands: не менее 90% bands должны полностью лежать внутри boundary crop, допускается максимум один outlier;
- новая boundary-авторизация применяется только когда upstream rejection set ровно `content_touches_frame`; любые `low_confidence`, `source_edge_content_clipped_by_deskew`, `disconnected_content_outside_crop` и другие причины сохраняют прежний fail-safe без crop;
- успешный boundary path использует существующий result decision `cropped_grayscale` и существующий `cropBoxSource`; публичный TypeScript/API контракт не меняется;
- обычный fully accepted safe-crop path PR #218/#219 не меняется;
- `ContentRegionEstimator`, `SafeCropEstimator`, angle thresholds/search range/sign convention не меняются;
- perspective correction не добавляется;
- OCR recognition, upload/backend/provider, network, dependencies, permissions, workflows и privacy boundary не меняются;
- реальные contract pages/screenshots не добавляются в repository/CI.

Следующий gate остаётся `android-document-preprocess-device-smoke-v1`. Первым regression test после merge PR #221 нужно снова прогнать ту же страницу: ожидается сохранение grayscale и accepted ~1° deskew плюс `cropped_grayscale` с non-null crop box и заметным удалением внешнего фона без потери содержимого листа. Если boundary evidence не проходит, допустим только прежний `deskewed_full_frame_grayscale` fail-safe; это не следует маскировать принудительным crop.

## Previous change — PR #220 deskew/crop decoupling corrective

Во время real-device smoke после PR #219 конкретная реально сфотографированная страница дала уверенно accepted angle evidence (`dominant +1.00°`, `requested deskew -1.00°`, confidence `0.8608`), но safe crop был отклонён с `content_touches_frame`. Финальный prepared-image consumer трактовал любой non-accepted crop result одинаково и выбрасывал уже accepted deskew, возвращая 0° full-frame grayscale. Это concrete in-contract preprocessing defect, разрешающий bounded corrective внутри текущего smoke gate.

PR #220 исправляет только композицию финального consumer:

```text
angle/crop result = accepted
→ fixed-frame grayscale deskew
→ authorized conservative crop
→ cropped_grayscale

angle accepted, crop rejected = rotation_only
→ accepted deskew сохраняется
→ expanded white-canvas full frame
→ grayscale
→ no crop
→ deskewed_full_frame_grayscale

angle rejected = full_frame_fallback
→ 0° grayscale full frame
→ no crop
```

Границы PR #220:

- `rotation_only` больше не отменяет accepted deskew только из-за отказа crop;
- full-frame deskew использует расширенный белый canvas, чтобы поворот не обрезал исходные углы/края;
- expanded output сохраняет существующие bounded limits: long side <= 10000 и accounted source+output memory <= 384 MiB;
- `full_frame_fallback` остаётся 0° и не получает crop;
- fully accepted safe-crop path PR #219 не меняется;
- новый prepared result decision `deskewed_full_frame_grayscale` добавлен только в TypeScript contract;
- angle estimator, confidence thresholds, search range, sign convention, `SafeCropEstimator`, `content_touches_frame` и другие crop guards не меняются;
- perspective correction не добавляется;
- OCR recognition, upload/backend/provider, network, dependencies, permissions, workflows и privacy boundary не меняются;
- real photographed page не добавляется в repository/CI.

## Previous change — PR #219 physical crop + grayscale final output

PR #219 завершает полезный локальный preprocessing consumer поверх merged PR #218 safe-crop authorization:

```text
local photo
→ bounded EXIF/orientation + grayscale preview
→ native angle/content-region/safe-crop evidence
→ accepted: fixed-frame grayscale transform + conservative full-resolution crop
→ non-accepted: 0° grayscale full-frame fallback
→ prepared.jpg shown in development UI
```

Границы PR #219:

- новый `prepareDocumentAsync(uri, previewUri)` не принимает crop coordinates от JavaScript и сам повторно получает producer-generated safe-crop evidence из текущего module-owned preview;
- source URI должен совпадать с текущей preview session до и после bounded analysis;
- accepted crop contract проверяет decision, coordinate space, finite/bounded rotation, expected preview dimensions, valid candidate/safe boxes и containment;
- preview safe bounds отображаются в oriented full-resolution coordinates консервативно: floor для left/top, ceil для right/bottom, с независимым X/Y scale;
- accepted path рисует grayscale fixed-size frame с тем же Android/Python sign contract, затем физически crop-ит только mapped safe bounds;
- `rotation_only` и `full_frame_fallback` в PR #219 оба давали 0° grayscale full-frame fallback; device smoke показал, что это смешивало accepted deskew и crop authorization, поэтому `rotation_only` semantics исправляются PR #220;
- максимальная геометрическая память остаётся bounded существующим 384 MiB accounting contract; encoded output ограничен существующим 64 MiB cap;
- итоговый artifact — локальный module-cache `prepared.jpg`; он не загружается и не логируется;
- validation UI показывает именно prepared grayscale document, его dimensions, decision, applied rotation, source-space crop box и fallback reasons;
- perspective correction, новые angle/crop thresholds и дальнейший standalone deskew tuning не добавляются;
- OCR recognition, upload/backend/provider, dependencies, permissions, workflows и privacy boundary не меняются.

## 0. Изменение PR #218 — safe crop authorization и product pivot к preprocessing

Во время первого real-device smoke после PR #217 product owner остановил дальнейшее развитие deskew как самостоятельной продуктовой цели. Практическое решение: пользователь получает подсказки при съёмке и не должен рассматриваться как источник произвольно сильно перекошенных кадров; уже реализованный bounded deskew остаётся небольшим страховочным механизмом, но дальнейшая разработка должна быть направлена на реальный preprocessing результата.

Целевой локальный preprocessing после этого решения:

```text
photo
→ bounded quality/orientation handling
→ content-region evidence
→ conservative safe crop when fully trusted
→ otherwise full-frame fallback
→ grayscale final prepared image
→ later OCR handoff
```

PR #218 намеренно реализует только первую половину этого перехода — safe-crop authorization поверх уже merged candidate estimator:

- `ContentRegionEstimator` по-прежнему строит candidate bounds из bounded grayscale mask;
- новый `SafeCropEstimator` добавляет frozen source-edge-loss guard;
- candidate получает conservative 4% padding with minimum 12 preview pixels;
- nearly-full-frame crop блокируется при >= 0.985 по любой оси;
- line-like и compact meaningful foreground outside proposed crop блокируют acceptance по frozen finite evidence contract;
- только полностью чистый candidate становится `accepted` и получает `safeCropBounds`;
- uncertain cases остаются `rotation_only` / `full_frame_fallback`;
- physical crop, new output artifact и grayscale final output в PR #218 ещё не выполняются;
- perspective correction, новые angle thresholds/search range и дальнейший deskew tuning не входят в scope;
- OCR recognition, network/backend/provider, dependencies, permissions, workflows и privacy boundary не меняются.

PR #218 специально разделён до wiring physical transform: final `SafeCropEstimator.kt` занимает 259 implementation additions, а весь runtime/TypeScript diff — 263 additions, поэтому bundling physical crop + grayscale + UI вывел бы PR за target <=300 additions. Следующий bounded PR `android-document-preprocess-physical-crop-grayscale-v1` должен structurally validate accepted in-process crop evidence, conservatively map preview bounds to oriented full resolution, output grayscale cropped image only when fully accepted, otherwise output grayscale full-frame fallback, и показать именно этот final prepared image в development UI.

После этого manual validation выполняется уже над полезным продуктовым результатом: `исходная фотография -> обрезанный/необрезанный grayscale document`, а не как отдельная длительная deskew-кампания.

## 0.1. Изменение PR #217 — Android geometry validation UI controls

Во время первого реального device smoke уже готового Android geometry path product owner обнаружил две практические проблемы validation harness: встроенные изображения слишком малы для оценки крабв/наклона, а повторная проверка следующей страницы неудобна без явных controls рядом с результатом.

PR #217 меняет только development validation UI:

- tap по bounded source preview открывает тот же module-owned bounded preview в полноэкранном `Modal`;
- tap по full-frame deskew result открывает тот же existing local result artifact в полноэкранном `Modal`;
- `Select another photo` повторно запускает существующий local picker рядом с результатом;
- `Reset` очищает только React UI state текущей geometry validation;
- отмена picker больше не стирает уже показанный geometry result;
- новый dependency/pinch-zoom library не добавляется;
- native geometry module, angle/content-region algorithms, thresholds, resource bounds, safe-crop authorization и physical crop не меняются;
- OCR recognition, upload/backend/network destination, analytics, permissions, workflows, provider/serverless path и persistence не меняются;
- полноэкранный просмотр не создаёт новый файл: он читает те же существующие module-cache preview/result artifacts, которые validation UI уже показывал до PR #217.

Первоначально после PR #217 планировался продолжительный visible deskew smoke. Product owner затем явно остановил эту отдельную deskew-кампанию и перевёл следующий implementation focus на safe crop + grayscale preprocessing, что записано PR #218.

## 0.2. Изменение PR #216 — Android preview snapshot integrity corrective

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

## 0.3. Изменение PR #215 — Android content-region candidate bounds

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

Owner-requested targeted Codex audit по PR #211–#215 вернул `BATCH AUDIT CLEAR`. Последующий отдельный post-merge review finding по snapshot consistency исправлен PR #216 и не меняет остальные выводы audit.

## 0.4. Изменение PR #214 — Android geometry development validation UI

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

### Current gate — prepared-document device smoke

`android-document-preprocess-device-smoke-v1`

Use the development preprocessing UI on the available Android device and the two owner-controlled actually photographed/prepared contract sets.

PR #223 changes the regression target: crop quality is no longer under test because runtime physical crop is disabled. The smoke must verify that no source edge, signature, note, header/footer or other page content disappears.

For each tested page inspect:

- final artifact is visibly grayscale;
- `accepted`/`rotation_only` results use `deskewed_full_frame_grayscale`, apply the accepted deskew, preserve the complete oriented source frame on the expanded canvas and report `cropBoxSource = null`;
- `full_frame_grayscale_fallback` preserves the complete oriented frame at 0° and reports `cropBoxSource = null`;
- no prepared result returns `cropped_grayscale`;
- output dimensions/rotation metadata are internally plausible;
- repeated `Select another photo` use does not mix pages or stale outputs;
- no crash/OOM or severe device-memory failure occurs.

Do not turn this into a renewed deskew or crop-tuning campaign. A geometry correction is justified only by concrete evidence satisfying the frozen reopen contract.

If this smoke passes, run the bounded Surya preprocessing comparison on the approved owner-controlled inputs:

```text
A. full frame as captured
B. full frame + deskew
C. full frame + deskew + grayscale
```

Use that result to decide whether grayscale remains useful and only then design the live capture-quality advisory layer. The separate serverless GPU OCR viability work remains approved; this A/B/C comparison is the immediate evidence step after the device smoke.

## 3. Deferred next product block — `serverless-gpu-ocr-viability-benchmark-v1`

The serverless benchmark remains approved but is temporarily deferred until the Android preprocessing gate above is completed.

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
→ client-side capture-quality checks and preprocessing (orientation / conservative deskew / full-frame preservation / grayscale pending OCR evidence)
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

Raw images/raw OCR are prohibited in Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable and unrelated services. Only sanitized derivatives may proceed to legal analysis.

The Android preprocessing validation sequence is stricter: selected real photos remain local to the device. It adds no network destination and must not log/export page contents.

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

Frozen Python geometry code baseline: `7fe4bc88df2427ea90442f7b074c3cfe4e0de33a`.

Current PR: #223 `android-document-disable-physical-crop-v1`.

Next step after merge PR #223: `android-document-preprocess-device-smoke-v1`.
