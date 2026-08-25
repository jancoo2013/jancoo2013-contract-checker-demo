# OCR Project State & Continuity v0

Последнее обновление: 2026-08-25, PR #238, `question-engine-template-family-discoveries-v1`.

Активный трек: `question-engine-development`.

Канонический следующий bounded-шаг: `question-engine-question-inventory-v1`.

Этот документ вместе с `docs/OCR_PROJECT_STATE.json` является канонической operational-точкой восстановления privacy/OCR-проекта. Архитектурные документы задают обязательные границы, но текущий `next_step_id` выбирается только state-файлами.

## Current change — PR #238 Question Engine template-family + statutory-baseline discoveries

PR #238 — docs-only Question Engine discovery update перед `question-engine-question-inventory-v1`.

Он фиксирует выводы из дополнительного публичного пустого шаблона аренды и добавляет отдельный поддерживаемый statutory-baseline документ `docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md`.

Зафиксированные продуктовые выводы:

- внешне и структурно похожие договоры одной template family нельзя считать семантически эквивалентными; конкретную редакцию нужно читать полностью, потому что небольшие вставки, удалённые подпункты, blanks и special conditions могут materially менять права и обязанности;
- early-exit analysis должен собирать совместно сохранение обязанности платить после выезда, replacement-tenant path и отдельные no-cause / mutual termination clauses, а не выдавать их как несвязанные findings;
- `option_exists = true` недостаточно: нужно анализировать notice, чей это option и как определяется экономическое условие продления, включая ситуацию, когда будущая rent не зафиксирована;
- broken internal references, blank sanctions и bespoke apartment-specific obligations являются first-class findings;
- standard template text и later special conditions нужно сравнивать на override/supplement/contradiction.

Statutory-layer direction:

```text
contract facts
→ Question Engine semantic map
→ statutory applicability gate
→ effective-date-aware statutory baseline
→ contract-vs-statute comparison
→ cross-clause + legal interaction analysis
→ user-facing explanation with exact section citation
```

Юридическая база для этого слоя — текущий `חוק השכירות והשאילה, התשל״א-1971` (Rental and Loan Law, 1971). Реформа, обычно называемая `שכירות הוגנת` / «справедливая аренда», фиксируется корректно как Amendment No. 1 от 2017 года к этому закону, effective `2017-09-17`, а не как отдельный неизменный закон.

`docs/QUESTION_ENGINE_STATUTORY_BASELINE_V1.md` хранит официальный Knesset source metadata, relevant section IDs, engineering summaries, applicability/non-derogation rules и freshness procedure. Он намеренно не содержит unversioned full static copy закона: официальный Knesset database уже показывает более поздние amendments, включая amendment published `2026-03-31`, а section `25י` содержит wording с future effective date `2026-09-30`. Поэтому future legal layer должен version-ить rules по effective date.

Ключевые правила statutory comparison:

- contract fact, statutory rule и legal interpretation остаются разными evidence layers;
- special residential protections нельзя применять до applicability gate, включая exclusions в `25טו`;
- `25יד` используется как central non-derogation meta-rule, но нельзя ошибочно считать mandatory любой section закона;
- user-facing report должен по возможности ссылаться на exact section (`§25ח`, `§25י`, `§25יד` и т.д.), а не писать расплывчатое «по закону 2017 года»;
- предпочтительная формулировка при unresolved interpretation — `potential conflict with §X`, а не автоматическое «незаконно»;
- если statutory freshness/version нельзя подтвердить, система должна безопасно деградировать до contract-only analysis, а не выдавать stale legal claim.

`active_track` и `next_step_id` не меняются. Следующий bounded implementation остаётся `question-engine-question-inventory-v1`.

PR #238 не добавляет source contract images, copied rental-template text, PII, handwriting values, OCR/runtime code, Gemini call, provider, network destination, dependency, permission, workflow, storage или production privacy claim.

## Previous change — PR #237 dedicated Question Engine discovery log

PR #237 — явно разрешённое product-owner docs-only исключение перед `question-engine-question-inventory-v1`. Оно добавляет `docs/QUESTION_ENGINE_DISCOVERY_LOG.md` как отдельный non-canonical рабочий журнал именно для Question Engine: текущих архитектурных гипотез, продуктовых выводов по анализу реальных договоров, правил user-facing объяснений, open questions и истории изменения этих выводов.

Журнал фиксирует текущую рабочую архитектуру `deterministic Question Engine → targeted LLM semantic reading → conditional follow-ups → cross-clause checks → bounded novel-issue catch-all → Python/evidence validation → overview essay → focused attention points`. Также в нём отдельно записаны различение `NOT_FOUND` / `CLAUSE_PRESENT_VALUE_BLANK` / `HANDWRITING_DEPENDENCY`, запрет угадывать handwriting, contract-defined role granularity, важность соотношений и масштаба сумм, различение видов обеспечений, internal-consistency checks и принцип практических последствий вместо банального пересказа.

Отдельно зафиксировано user-facing правило: термин `שכירות בלתי מוגנת` нельзя оставлять как голое «незащищённая аренда»; сразу нужно пояснять, что речь идёт об исключении из специального режима защищённого жильца (`דייר מוגן`), а не об отсутствии обычных прав арендатора.

Новый файл не заменяет binding architecture/security/privacy documents и не выбирает operational next step. `docs/OCR_PROJECT_STATE.md` и JSON mirror остаются canonical state; `active_track` и `next_step_id` не меняются. Следующий bounded implementation по-прежнему `question-engine-question-inventory-v1`.

PR #237 не добавляет raw real contracts, raw OCR, PII, handwritten values, Gemini/runtime integration, dependency, provider, permission, workflow, storage или production privacy claim.

## Previous change — PR #236 first sanitized golden contract corpus

PR #236 реализует первый `question-engine-golden-contract-corpus-v1` fixture на основе одного owner-controlled реального трёхстраничного договора аренды на иврите.

Repository получает только два новых persistent artifacts: обезличенный печатный Hebrew text и metadata JSON. Исходные фотографии, raw OCR output, имена, Israeli ID, телефоны, полные адреса, банковские/счётные/branch details, подписи, handwriting и stamp content не коммитятся. Handwriting не транскрибируется, не реконструируется и не угадывается.

Golden text намеренно сохраняет юридически значимые напечатанные значения и формулировки без нормализации: суммы, даты, номера пунктов, проценты, сроки, source blanks и apparent source inconsistencies остаются как в источнике. В частности, п.3 буквально содержит `12 חודשים` при напечатанных датах `1.1.26`–`31.12.27`, а п.11 описывает `שיק עירבון`, но далее говорит о возврате `הערבות הבנקאית`; PR не исправляет эти расхождения.

Роль сторон по умолчанию сохраняется ровно на гранулярности договора: `המשכיר` и коллективный `השוכר`. При этом этот первый реальный fixture дал важный concrete exception к упрощённой гипотезе: в п.24 operative printed text всё-таки различает двух членов tenant party по имени и назначает им разное payment behavior. Поэтому только эти два индивидуальных упоминания обезличены как `TENANT_A` и `TENANT_B`; глобальные `TENANT_1/2/3` по всему договору не вводятся. Правило остаётся: отдельный party placeholder появляется только тогда, когда сам юридически значимый текст различает людей.

Metadata фиксирует source-page count, transcription/sanitization policy, удалённые PII-классы, сохраняемые legal values, role model, source blank markers и отсутствие owner text-level review на момент PR. Это не production OCR evidence и не утверждение об автоматическом privacy pipeline.

Следующий bounded step после merge — `question-engine-question-inventory-v1`: на этом sanitized fixture выделить первый набор повторяющихся и условных вопросов, ожидаемые structured answer fields и evidence targets, без Gemini/runtime integration.

## Previous change — PR #235 binding-doc synchronization

Перед началом `question-engine-golden-contract-corpus-v1` был обнаружен обязательный repository-level conflict: merged PR #234 уже переключил canonical state на `question-engine-development`, но `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md` и `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md` всё ещё описывали serverless GPU OCR как активное направление. Поскольку `AGENTS.md`/`CODEX_WORKFLOW.md` требуют остановить implementation при конфликте binding sources, golden fixture не добавлялся до этого corrective.

PR #235 синхронизирует только binding documentation:

- активный implementation track во всех binding sources теперь согласован с canonical state: `question-engine-development`;
- Surya/cloud OCR infrastructure остаётся frozen/deferred production candidate и research asset, а не удаляется и не объявляется провалившейся;
- frozen serverless privacy constraints остаются binding для любого будущего reopen: approved Israel-only restricted-data processing, no raw Gemini/unrelated services, bounded retention/deletion, log hygiene, irreversible redaction;
- Question Engine должен оставаться OCR-provider-independent;
- sanitized golden fixtures могут сохранять печатный юридически значимый текст, суммы, даты, номера пунктов и contract-defined roles, но не recoverable PII;
- handwriting не транскрибируется, не реконструируется и не угадывается для semantic ground truth; зависимость смысла от handwriting должна оставаться explicit unresolved dependency;
- role-preserving de-identification теперь использует гранулярность, которую определяет сам договор: если несколько именованных лиц в шапке коллективно определены и далее используются только как `השוכר`, сохраняется единая роль `השוכר` / `АРЕНДАТОР`; `TENANT_1`, `TENANT_2` и т.п. не изобретаются без later operative text, которое действительно различает этих людей;
- этот corrective не добавляет real contract text/images, OCR output, runtime code, provider/API calls, dependency, permission, workflow, storage, Gemini integration или production privacy claim.

`active_track` и `next_step_id` намеренно не меняются. После merge PR #235 следующий bounded implementation остаётся `question-engine-golden-contract-corpus-v1`.

## Previous change — PR #234 Question Engine track pivot

PR #234 фиксирует явное product-owner решение заморозить Surya/cloud OCR infrastructure track и перенести основной implementation focus на Question Engine.

Причина — приоритизация продукта, а не доказанный провал Surya. После merge PR #233 targeted-region CPU runtime был начат локально: source archive загрузился, Cloud Build API был включён, но создание build остановилось на `PERMISSION_DENIED` до container build, deploy и OCR execution. Поэтому никакого вывода о реальной CPU latency/quality Surya из этой попытки делать нельзя.

Текущее решение:

- дальнейшие IAM/Cloud Build/Cloud Run/GPU/CPU infrastructure iterations для Surya сейчас не выполняются;
- существующие PR #226, #232 и #233 сохраняются как frozen research assets и могут быть переиспользованы позже;
- cloud/Surya track reopen-ится только если automatic OCR станет concrete blocker для product testing либо появится реальная multi-user нагрузка/экономический смысл вернуться к production OCR infrastructure;
- Tesseract full-page OCR остаётся `NO-GO`; исторический провал на уменьшенном изображении не является основанием снова делать его production fallback;
- Question Engine должен быть OCR-provider-independent: он получает нормализованное представление договора и не должен зависеть от того, кто когда-либо сделал OCR;
- следующий bounded-шаг — `question-engine-golden-contract-corpus-v1`: начать с нескольких owner-controlled реальных договоров аренды и получить эталонную печатную часть текста для разработки Question Engine;
- persistent repository fixtures должны быть полностью обезличены и не содержать recoverable PII; raw real contracts не добавляются в repository/CI;
- рукописный текст не должен семантически распознаваться, реконструироваться или угадываться. Если смысл ответа зависит от рукописной вставки, система должна вернуть explicit unresolved handwriting dependency, а не выводить содержание по контексту;
- de-identification должна сохранять роли сторон и направление обязательств; конкретная гранулярность placeholders уточнена и superseded текущим PR #235: не различать отдельных людей, если сам operative contract text их не различает;
- этот PR не добавляет runtime, provider, upload, masking, Gemini call, storage, production auth или production privacy claim и не ослабляет существующий `SECURITY.md` boundary.

## Previous change — PR #233 targeted-region Cloud Run CPU benchmark

PR #233 — явно разрешённое product-owner bounded research exception поверх merged PR #232. Оно переносит targeted-region benchmark в воспроизводимый CPU-only Cloud Run container для `me-west1`, чтобы измерить реальные 1/2/4 client concurrency и 1/4/8-region batches без full-page Surya transcription.

Экспериментальная runtime-схема:

```text
bounded PNG page + bounded candidate rectangles
→ Cloud Run CPU service in me-west1
→ one loopback llama.cpp backend
→ one reused Surya predictor
→ per-request client parallelism 1 / 2 / 4
→ OCR only on targeted crops
→ aggregate-only metrics
```

Границы PR #233:

- llama.cpp запускается CPU-only на `127.0.0.1` с `--parallel 4`, `--ctx-size 49152`, `--threads 8`, `--threads-batch 8` и `--n-gpu-layers 0`;
- four-slot context выбран так, чтобы не уменьшать рекомендуемый per-slot context при сравнении 1/2/4 client parallelism;
- процесс держит один `SuryaInferenceManager` и один `RecognitionPredictor`; Cloud Run `containerConcurrency = 1`, поэтому разрешённое per-request изменение `SURYA_INFERENCE_PARALLEL` не пересекается с другим benchmark request внутри того же instance;
- HTTP wrapper принимает только один bounded PNG body, bounded ASCII `X-Surya-Regions` и `X-Surya-Parallel` из `{1,2,4}`;
- геометрические/region/output bounds остаются в merged PR #232 benchmark; persistent HTTP output содержит только status/error code, region/block/character counts и timing;
- raw page/crop pixels и OCR text не возвращаются и не логируются новым wrapper;
- временный PNG удаляется до ответа; cleanup failure возвращает bounded `TEMP_CLEANUP_FAILED`;
- image build pin-ит llama.cpp revision, Surya GGUF revision/checksums и `surya-ocr==0.22.1`; runtime model resolution работает offline;
- Cloud Run template фиксирует `me-west1`, 8 vCPU, 16 GiB, minScale 0, maxScale 1, concurrency 1, startup CPU boost и отсутствие GPU/cross-region fallback;
- candidate detector, Tesseract integration, production PII decision/masking/privacy validation, Android upload, Gemini/legal-analysis integration, storage, auth, encryption/key management, billing и production provider authorization не добавляются;
- real user documents/PII не добавляются в repository or tests.

Final exact-head static validation после state sync: Python compilation PASS; `tests.test_surya_targeted_cloud_run_cpu_contract` — 4/4 PASS; entrypoint shell syntax PASS; JSON state parse PASS; exact local Git-blob hashes for the reconstructed final code/test/config files matched the GitHub branch blobs.

Фактические Cloud Run build/deploy, targeted-region latency/quality, RAM/OOM, billed cost, provider logs, cleanup/retention и actual regional behavior ещё не измерены и не заявляются как доказанные этим PR. После merge именно эти runtime measurements должны решить, оправдан ли отдельный canonical pivot на targeted-region CPU track.

`active_track` и `next_step_id` намеренно не меняются в PR #233: это bounded exception, а binding architecture/state pivot будет отдельным product-direction решением только после runtime evidence. Product owner закрыл PR #228, #229 и #230 без merge; они не являются dependencies этого PR. Закрытый #230 использован только как reference для уже проверенных bounded CPU-container patterns.

## Previous change — PR #232 targeted-region parallel Surya CPU benchmark

PR #232 — явно разрешённое product-owner bounded research exception после практического наблюдения, что Google Batch T4 provisioning остаётся непригодно долгим для интерактивного пользовательского пути, а существующий Cloud Run CPU full-page benchmark тратит основное время на полную повторную транскрипцию страницы.

Эксперимент намеренно проверяет более узкую модель вычислений:

```text
full page
→ bounded caller-supplied candidate regions
→ crop only those regions in stable post-EXIF page coordinates
→ one Surya batched recognition call for all crops
→ bounded parallelism = 1 / 2 / 4
→ aggregate-only timing/count metrics
```

Границы PR #232:

- новый benchmark не выполняет full-page OCR; Surya получает только переданные bounded crops;
- `SURYA_INFERENCE_PARALLEL` ограничен значениями 1, 2 или 4 и применяется до создания `SuryaInferenceManager`;
- до OCR проверяются encoded page bytes, decoded dimensions/pixels, count/bounds/area of candidate regions и total candidate pixels;
- OCR output дополнительно bounded по blocks и text length;
- raw crop pixels и raw OCR text остаются transient process state и не попадают в persistent result/CLI output;
- persistent result содержит только status/error code, region/block/character counts, selected parallelism и timing;
- injected-engine tests подтверждают one-batch coverage, invalid-region fail-closed, invalid parallelism rejection и malformed engine coverage safe failure;
- candidate-region detector пока не реализуется: этот PR не добавляет Tesseract integration, marker rules или production PII decision logic;
- Cloud Run deployment/runtime configuration не меняется; реальная CPU parallelism/latency ещё не измерена;
- Android upload, production auth/encryption/key management, production masking/privacy validation, Gemini/legal-analysis integration, storage и provider authorization не добавляются;
- real user documents/PII не добавляются в repository or tests.

Pre-state-sync focused validation на reconstructed new module/tests: Python compilation PASS; `tests.test_surya_targeted_region_benchmark` — 4/4 PASS. После финального state sync требуется exact-head validation, changed-path audit и mandatory security review.

`active_track` и `next_step_id` намеренно пока не меняются: PR #232 проверяет вычислительную гипотезу до отдельного product-direction commit. Если targeted-region CPU runtime materially сокращает latency без потери PII-localization utility, следующий owner decision может заменить full-page/GPU benchmark path отдельным canonical targeted-region CPU track. Draft PR #229/#230 остаются отдельными незавершёнными experiments и не являются dependency этого PR.

## Previous change — PR #231 Surya PNG verification-order corrective

PR #231 — явно разрешённый product-owner bounded corrective существующего PR #226 raw-fullframe worker. Во время Draft PR #230 Cloud Run CPU benchmark approved non-identifying PNG дошёл до worker, но был отклонён как `INVALID_IMAGE` до OCR. Локальная reproduction теми же Pillow semantics подтвердила, что PNG исправен: `verify()` проходит, если вызывается сразу после `Image.open()`, но current worker сначала читал EXIF через `getexif()`, а затем вызывал `verify()` на том же image object; current Pillow для PNG отвечает `RuntimeError: verify must be called directly after open`.

Исправление намеренно минимальное:

```text
bounded encoded bytes
→ fresh Image.open
→ verify() immediately
→ close
→ fresh Image.open of the same bytes
→ EXIF/oriented-dimension inspection
→ existing bounds/digest/OCR path unchanged
```

Границы corrective:

- добавлен synthetic PNG regression test, который должен успешно пройти preflight и вызвать injected fake OCR engine ровно один раз;
- malformed images по-прежнему fail closed как `INVALID_IMAGE`;
- encoded-size, page-count, dimension, pixel, digest, EXIF-orientation, OCR-output и geometry bounds не ослабляются;
- raw OCR/layout persistence, safe aggregate metrics и error-envelope semantics не меняются;
- provider, endpoint, network destination, model, dependency, Android code, production upload, encryption/key management, PII masking, Gemini/legal-analysis integration и storage не меняются;
- real user documents/PII не добавляются в repository or tests.

Pre-state-sync focused validation на exact worker/test branch content: Python compilation PASS; `tests.test_surya_fullframe_worker` — 9/9 PASS. После финального state sync требуется повторная exact-head validation и security review перед Ready.

`active_track` и `next_step_id` намеренно не меняются. Draft PR #230 должен после merge этого corrective обновиться на исправленный worker, пересобрать immutable image и повторить Cloud Run cold/warm OCR benchmark; его прежний `INVALID_IMAGE` ответ не является OCR-performance evidence.

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
- при известной роли чувствительное значение должно заменяться stable semantic marker; исторические numbered examples в этом разделе не задают текущую role granularity и superseded PR #235;
- исходные PII pixels сначала удаляются необратимо, и только после этого поверх очищенного raster рисуется semantic placeholder;
- одна и та же contract-defined role должна иметь стабильный marker на всех страницах одного contract job, если operative text не различает отдельных участников;
- если область явно sensitive, но роль не удаётся определить безопасно, допустим generic safe placeholder; если неясно, полностью ли закрыто PII, downstream handoff блокируется;
- development overlay может оставаться полупрозрачным для визуальной проверки покрытия, но любой artifact, который может покинуть trusted worker, должен содержать opaque irreversible pixel replacement;
- privacy-validated sanitized full-page images являются primary downstream representation для approved multimodal legal-analysis model;
- raw OCR JSON/text остаётся restricted transient worker state и не является canonical LLM payload;
- sanitized structured text/evidence разрешается производить после privacy validation, если это понадобится deterministic validation/citation layer;
- PR #227 не добавляет runtime mask renderer, PII detector, provider, endpoint, dependency, upload path, LLM call или production privacy claim.

`active_track` и `next_step_id` намеренно не меняются. Следующий bounded implementation остаётся `surya-raw-fullframe-gpu-execution-v1`: выполнить существующий PR #226 worker на explicitly approved GPU infrastructure с approved non-identifying full-frame pages и собрать реальные quality/layout/PII-localization, latency, GPU/VRAM/OOM, cost, log hygiene, cleanup, region и retention evidence. Этот исторический next-step record superseded PR #234/PR #235 and is not current.

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

Следующий bounded step `surya-raw-fullframe-gpu-execution-v1` в этой исторической записи superseded PR #234/PR #235 и не является current next step.

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
- raw OCR text/layout определён как transient internal result: job/page statuses включают явный `partial_failure`, а raw result нельзя трактовать как сохраняемый provider job result;
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
- producer-generated `safeCropBounds`, content-region и document-boundary evidence могут сохраняться для диагностики/advisory capture-quality, но не имеют права удалять source pixels;
- full-frame dimension/memory bounds сохраняются;
- OCR recognition, upload/backend/provider, network, dependencies, permissions, workflows и privacy boundary не меняются.

После merge PR #223 отдельный `android-document-preprocess-device-smoke-v1` был сознательно снят с active next step решением product owner; rationale и reopen conditions записаны в PR #224 выше.

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

## 0.1. Изменение PR #217 — Android geometry development validation UI controls

Во время первого реального device smoke уже готового Android geometry path product owner обнаружил две практические проблемы validation harness: встроенные изображения слишком малы для оценки краёв/наклона, а повторная проверка следующей страницы неудобна без явных controls рядом с результатом.

PR #217 меняет только development validation UI:

- tap по bounded source preview открывает тот же module-owned bounded preview в полноэкранном `Modal`;
- tap по full-frame deskew result открывает тот же existing local result artifact в полноэкранном `Modal`;
- `Select another photo` повторно запускает существующий local Android picker рядом с результатом;
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
- UI отображает source/preview dimensions, dominant text angle, requested deskew angle, confidence, accepted/rejected decision/reasons, transform decision, applied rotation, output dimensions и fallback reasons;
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
- routes `accepted` и `rotation_only` to expanded full-frame grayscale deskew with `cropBoxSource = null`;
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

## 3. Frozen product block — Surya/cloud OCR infrastructure

Surya/cloud OCR infrastructure is no longer the active development track after PR #234.

The repository keeps the merged benchmark contracts and implementations from PR #224–#233 as frozen research assets. They are not deleted and are not interpreted as production approval.

The attempted targeted-region CPU runtime after PR #233 did not reach container build or OCR execution: local `gcloud builds submit` uploaded the source archive and enabled the Cloud Build API, then build creation failed with `PERMISSION_DENIED`. Therefore:

- no measured CPU latency/quality result exists;
- no conclusion is recorded that targeted-region Surya CPU is too slow or unusable;
- no further IAM, Cloud Build, Cloud Run, GPU queue/provisioning or cost tuning is scheduled now;
- the infrastructure track can reopen when automatic OCR becomes a concrete blocker for product validation or real multi-user demand justifies renewed infrastructure work;
- any reopened production OCR path must still satisfy the existing Israel-only, restricted-data, retention/deletion and log-hygiene requirements in `SECURITY.md`;
- Tesseract full-page OCR remains NO-GO and is not promoted as fallback by this freeze.

Question Engine development must not depend on a particular OCR provider. The current task is to validate the semantic/product layer first.

## 4. Active target pipeline — Question Engine development

Current development pipeline:

```text
owner-controlled real rental contracts
→ obtain reliable printed-text ground truth outside the production OCR dependency
→ exclude handwriting from semantic transcription
→ de-identify PII while preserving contract-defined party roles
→ sanitized golden contract corpus
→ recurring-question inventory + conditional branches
→ Question Engine
→ structured answers with evidence references
→ deterministic / Python verification
→ statutory applicability + effective-date-aware baseline comparison where relevant
→ Russian user-facing report with contract facts separated from legal references
```

This is a development/testing pipeline, not a new production data path.

Binding constraints:

- raw real contracts and recoverable PII must not be committed to repository/CI;
- persisted golden fixtures must be sanitized before repository storage;
- handwriting is never guessed or reconstructed for semantic analysis; an answer that depends on handwriting must remain explicitly unresolved;
- role-preserving placeholders must retain who owes, pays, returns, guarantees or may demand something from whom, using the role granularity actually defined by the contract;
- multiple names in the header do not by themselves justify numbered party identities if later operative text treats them collectively under one role;
- Question Engine input/output contracts should remain independent of OCR implementation so future Surya/other OCR infrastructure can be reattached without redesigning semantic logic;
- statutory claims must come from a current effective-date-aware baseline and remain distinguishable from contract facts and model interpretation;
- production photo/OCR/privacy infrastructure remains deferred, not waived.

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

Current PR: #238 `question-engine-template-family-discoveries-v1`.

Canonical next step after merge PR #238: `question-engine-question-inventory-v1`.

Surya/cloud OCR infrastructure remains frozen; PR #238 adds only Question Engine design/statutory-baseline documentation and canonical state metadata, with no OCR/runtime evidence.
