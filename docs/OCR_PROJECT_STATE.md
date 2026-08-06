# OCR Project State & Continuity v0

Последнее обновление: 2026-08-06, PR #195, `ocr-text-angle-estimator-v1`.

Активный трек: `serverless-gpu-ocr`.

Канонический следующий шаг остаётся `serverless-gpu-ocr-viability-benchmark-v1`, но фактический provider run временно отложен по явному решению владельца продукта до завершения трёх bounded client-normalization шагов. После PR #195 следующее разрешённое исключение: `ocr-content-region-bounds-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Архитектуру задают `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md` и `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`. `docs/VISUAL_PII_LOCALIZATION_V1.md` сохраняет paused local-only alternative. Evidence/masking contract задаёт `docs/PII_EVIDENCE_DETECTOR_V1.md`; машиночитаемое состояние хранится в `docs/OCR_PROJECT_STATE.json`.

## 0. Изменение PR #195

- Добавлен bounded text-angle estimator поверх boolean mask из PR #194.
- Поиск ограничен диапазоном ±12° с шагом 1° и выполняется на analysis preview не более 900 px по длинной стороне.
- Выход ограничен dominant text angle, inverse deskew rotation, confidence, projection gain, peak margin, foreground ratio и `accepted / rejected` с явными rejection reasons.
- Пустая маска, случайный шум, чрезмерный foreground, слабый/неоднозначный projection peak, низкая confidence и кандидат на границе диапазона fail closed как `rejected`.
- PR не ищет строки и content bounds, не поворачивает и не обрезает изображение, не добавляет perspective correction, CLI, overlay, Android/runtime integration, OCR, Surya, upload, encryption или PII processing.
- Focused synthetic validation: 7/7 tests; покрыты нулевой угол, наклон в обе стороны, пустая маска, случайный шум, search-limit rejection и invalid input contract.
- Следующее разрешённое normalization-исключение после merge: `ocr-content-region-bounds-v1`.

## 0.1. Изменение PR #194

- PR #193 был закрыт без merge и не изменил `main`.
- Его scope разделён на три bounded шага: `ocr-local-contrast-text-mask-v1` → `ocr-text-angle-estimator-v1` → `ocr-content-region-bounds-v1`.
- PR #194 добавляет только deterministic preview-scale local-contrast mask для тёмных текстоподобных пикселей.
- Используются EXIF orientation, preview не более 1800 px, локальная оценка фона и adaptive threshold; маленькие изображения не увеличиваются.
- Выход ограничен grayscale preview, boolean mask, scale, threshold и foreground ratio.
- Угол текста, строки, content bounds, решения crop/deskew, CLI, overlay, OCR, Surya, Android integration, upload, encryption и PII processing не добавлены.
- Focused synthetic validation: 4/4 tests; покрыты текст без видимой границы листа, плавный shadow gradient, bounded preview/no-upscale и pre-conversion pixel safety limit.
- Следующее разрешённое normalization-исключение после merge: `ocr-text-angle-estimator-v1`.

## 0.2. Изменение PR #192

- Добавлен `docs/FUTURE_PRODUCT_AND_ARCHITECTURE_IDEAS.md` — документационный backlog продуктовых, UX, privacy и архитектурных идей из рабочего голосового диалога.
- Зафиксированы направления для будущей разработки: Contract Question Engine, evidence IDs вместо генерируемых LLM-цитат, ролевые PII placeholders, Israel-only Region Guard, server-side GPU OCR, UX ожидания, нейтральное звуковое уведомление и полная продуктовая обвязка.
- Документ не объявляет эти идеи реализованными и не заменяет binding architecture/state sources.
- Runtime, data handling, зависимости, OCR worker, Android-код, внешние API и production privacy boundary не изменены.
- Активный трек `serverless-gpu-ocr` и единственный следующий шаг `serverless-gpu-ocr-viability-benchmark-v1` остаются без изменений.

## 0.3. Изменение PR #191

- Добавлен первый bounded slice активного `serverless-gpu-ocr-viability-benchmark-v1`: фиксированный синтетический десятистраничный Hebrew contract-like source packet без реальных PII.
- Добавлен deterministic quality/geometry oracle поверх существующего Surya `results.json` loader.
- Oracle проверяет normalized Hebrew CER/word similarity, пять обязательных legal sentinels, семь critical values, exact ten-page set и page/block bbox integrity.
- `quality_geometry_verdict=PASS` означает только прохождение текстового и геометрического sub-gate.
- PR не добавляет renderer, serverless runner, Surya dependency, model weights, credentials, provider endpoint, real contract, raw OCR artifact, GPU execution или overall viability claim.
- Cold start, warm execution, queue delay, VRAM, OOM, worker lifetime, billed seconds, cost, provider logs/retention и cleanup остаются неизмеренными.
- Активный `next_step_id` не меняется: benchmark продолжается следующими bounded slices и фактическим provider run.

## 0.4. Изменение PR #190

- Владелец продукта явно выбрал encrypted on-demand serverless GPU OCR вместо активной local-only visual localization разработки.
- Former absolute rule `raw photos never leave the device` superseded for this consent-based mode.
- Raw contract pages могут входить только в один approved serverless worker boundary после explicit user consent.
- Worker decrypts input in volatile memory; architecture не является local, zero-access или zero-knowledge processing.
- Raw images и raw OCR запрещены в Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable и unrelated services.
- Worker обязан создать sanitized image/text derivative до legal-analysis handoff.
- Raw input, transient plaintext, job keys, temporary files и raw OCR должны удаляться после success или terminal failure согласно verified provider/runtime behavior.
- Для первого benchmark отдельный VPS, Redis, RabbitMQ, MinIO, PostgreSQL и permanent GPU не нужны.
- Surya выбран первым benchmark candidate, но не production dependency.
- `visual-pii-synthetic-baseline-v1` снят с active next step; local visual track сохранён как paused research/fallback.
- PR документационный: worker, credentials, uploads, dependencies, real contracts и Gemini calls не добавлены.

## 1. Активная целевая цепочка

```text
raw phone photos
→ client-side normalization and encryption
→ bounded asynchronous serverless job
→ GPU worker decrypts in volatile memory
→ full-page Hebrew OCR and layout extraction
→ server-side PII detection and irreversible image/text redaction
→ privacy validation
→ anonymized derivative and evidence blocks
→ approved LLM legal-risk analysis
→ Russian report
→ deletion of raw and transient job material
```

Tesseract full-page OCR on Samsung A55 remains NO-GO and cannot return as active fallback.

## 2. Privacy boundary

Raw material may exist only in:

- user device;
- encrypted transport;
- encrypted short-lived job storage when needed;
- volatile authorized worker memory;
- bounded transient worker files only when unavoidable and automatically deleted.

Production remains blocked until separate steps define and verify:

- explicit consent and plain-language disclosure;
- authentication and authorization;
- per-job key lifecycle;
- provider and data-region policy;
- retention and deletion behavior;
- log scrubbing;
- cleanup after success/failure/timeout/cancellation;
- processor terms, privacy policy, and legal review;
- incident response.

Only sanitized derivatives may proceed to Gemini or another legal-analysis model.

## 3. Preserved and paused components

| Component | Status |
|---|---|
| PII classes and evidence contract | Preserved for server-side sanitization |
| Direct-value validators/checksums | Preserved as deterministic evidence |
| `auto_mask / local_review / keep` | Preserved |
| Geometry gates and irreversible mask rules | Preserved |
| Android Tesseract full-page OCR | NO-GO; historical diagnostic only |
| Local visual PII detector | Paused research/fallback |
| Local-contrast text mask | Implemented as offline Python reference in PR #194; not integrated into Android/runtime |
| Text-angle estimator | Implemented as offline Python reference in PR #195; not integrated into Android/runtime |
| Content-region bounds/decision | Not implemented; next bounded normalization exception |
| Surya viability fixture + quality/geometry oracle | Implemented in PR #191 |
| Benchmark renderer/serverless runner | Not implemented |
| Actual Surya GPU viability result | Not measured |
| Production serverless worker | Not implemented |
| Production encryption/key management | Not implemented |
| Server-side PII sanitizer | Not implemented |
| Privacy validator | Not implemented |
| Legal-analysis handoff | Existing text prototype only; no raw-image integration |

## 4. Cost and latency assumptions

Serverless cost includes:

1. container/model cold start;
2. execution;
3. idle timeout before scale-down;
4. storage/transfer where applicable;
5. failures and retries.

Therefore `model throughput` does not equal end-to-end contract latency or per-contract cost.

Current provider pricing and Surya benchmarks are planning inputs only. The repository must not claim that one contract is processed in fractions of a second until single-job cold and warm measurements exist.

## 5. Канонический benchmark и временный normalization gate

**`serverless-gpu-ocr-viability-benchmark-v1`** remains the canonical architecture step.

По явному решению владельца продукта фактический Surya/provider run временно отложен до завершения следующей bounded sequence:

1. `ocr-local-contrast-text-mask-v1` — PR #194;
2. `ocr-text-angle-estimator-v1` — PR #195;
3. `ocr-content-region-bounds-v1` — следующий разрешённый шаг после merge; строки, основная область и fail-safe decision без применения crop/deskew.

Эта sequence не разрешает автоматически добавлять perspective correction, shadow cleanup, glare/blur gates, Android realtime analyzer или runtime crop. Каждый из них требует отдельного bounded решения.

После normalization sequence remaining benchmark work:

1. add a deterministic renderer for the checked-in synthetic source packet and record font/page hashes;
2. add one serverless-compatible Surya runner without production upload or permanent storage;
3. pin package/model/backend/GPU configuration;
4. measure queue delay when available, cold first-page time, warm ten-page time, worker lifetime, billed seconds, provider price, total/peak VRAM and OOM status;
5. feed the output through the PR #191 quality/geometry oracle;
6. inspect provider/runtime logs and retained artifacts for raw image/OCR leakage;
7. record licensing, provider retention/deletion and data-region status as verified or unresolved;
8. keep generated pages, raw OCR, reports, logs and provider artifacts outside version control;
9. do not add Android upload, production encryption, real user contracts, production masks, Gemini calls, permanent storage or a custom VPS queue.

Provisional go/no-go gate:

- materially usable Hebrew output on the fixed packet;
- stable line/block geometry;
- one ten-page job completes without OOM on an economically acceptable GPU class;
- all required legal sentinels and critical values survive normalization;
- cold and warm latency, VRAM and billed cost are measured rather than inferred;
- no raw content appears in logs or retained benchmark metadata;
- licensing and provider retention are verified or explicitly recorded unresolved.

A PASS on the synthetic packet permits a later held-out owner-controlled photo benchmark. It does not permit production upload, PII sanitization or legal-analysis integration.

## 6. Deferred infrastructure

Do not build before the benchmark:

- always-on GPU instances;
- custom VPS API/queue;
- Redis/RabbitMQ;
- MinIO/PostgreSQL/permanent document store;
- production authentication and key mediation;
- consent UI and privacy-policy implementation;
- production PII sanitization;
- billing;
- Gemini/legal-analysis integration.

## 7. Правила восстановления и работы

Перед новой privacy/OCR веткой:

1. прочитать all binding sources с актуального `main`;
2. проверить отсутствие overlapping open PRs;
3. опубликовать exact Context Gate v1;
4. менять только declared paths и approved bounded step;
5. открыть draft PR, затем обновить оба state-файла фактическим номером;
6. выполнить focused tests/benchmarks на exact final head SHA;
7. проверить diff, state continuity, generated files, credentials, raw data и auto-merge;
8. не merge без явного решения владельца продукта.

Последний полный cold-start audit: PR #177 после merge PR #176.
