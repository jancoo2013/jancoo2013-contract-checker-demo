# OCR Project State & Continuity v0

Последнее обновление: 2026-08-09, PR #202, `ocr-document-geometry-integration-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий bounded-шаг после merge PR #202: `ocr-document-geometry-block-audit-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Только он вместе с `docs/OCR_PROJECT_STATE.json` выбирает текущий `next_step_id`; архитектурные документы задают границы и обязательные будущие gates, но не выбирают следующий PR самостоятельно.

## 0. Изменение PR #202

- Добавлен `document_geometry_normalizer.py` — единая end-to-end точка входа для уже реализованного блока геометрической нормализации документа.
- Pipeline не дублирует алгоритмы и последовательно вызывает:
  - `build_text_ink_mask()` из PR #194;
  - `estimate_text_angle()` из PR #195;
  - `estimate_content_region()` из PR #196;
  - `apply_content_region_deskew_crop()` из PR #200.
- Результат сохраняет stage decisions и возвращает либо физически deskewed/cropped изображение, либо полный EXIF-нормализованный кадр при штатной неопределённости.
- Preview mask и preview image не возвращаются из нового top-level result; наружу выходят только размеры/метрики, stage contracts и итоговое изображение.
- Добавлены end-to-end synthetic tests: горизонтальный документ, наклон +7°, blank/fail-safe, downscaled preview с full-resolution transform, pixel-limit fail-closed и invalid non-image input.
- Устранён stale binding-конфликт sequencing: `docs/ARCHITECTURE.md`, `docs/CUSTOM_OCR_PIPELINE.md` и `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md` больше не объявляют собственный текущий next step. Serverless viability benchmark остаётся обязательным будущим gate, но активный шаг определяется только canonical state.
- По решению владельца продукта illumination/shadow normalization сейчас не развивается: сначала закрывается и отдельно аудируется первый блок crop/deskew.
- Runtime приложения, Android, OCR engine, PII, Gemini, provider integration, upload, encryption, permanent storage и network destinations не подключены.

### Предыдущее изменение PR #201

- Добавлен binding `SECURITY.md` и обязательная final-diff security review для каждого PR.
- Restricted raw/PII material разрешено обрабатывать только в явно approved Israel-only infrastructure; cross-region fallback запрещён.
- Individual Codex review больше не является per-PR merge gate; Codex используется для целевых/периодических batch audits.
- Финальные sanitized reports могут храниться только под отдельным authorization/encryption/deletion contract.

### Предыдущее изменение PR #200

- Добавлен offline Python reference-компонент физического deskew/crop полного изображения.
- Поворот и crop применяются только при одновременных `angle.accepted` и `bounds.accepted`.
- `rotation_only`, отклонённый угол и `full_frame_fallback` сохраняют полный EXIF-нормализованный кадр без геометрических изменений.
- Preview bounds отображаются в full-resolution coordinates консервативно: `floor` для left/top и `ceil` для right/bottom.

## 1. Активная целевая цепочка

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
→ optional persistent storage of the sanitized final report under exact account authorization
```

Tesseract full-page OCR on Samsung A55 remains NO-GO and cannot return as active fallback.

## 2. Первый блок — document geometry normalization

Текущий первый блок теперь имеет единый bounded contract:

```text
source PIL image
→ EXIF orientation inside preview/transform contracts
→ local-contrast text/ink mask
→ bounded dominant text-angle estimate
→ bounded content-region decision
→ full-resolution deskew + conservative crop only when fully accepted
→ otherwise full-frame fail-safe
→ DocumentGeometryNormalizationResult
```

Реализованные компоненты:

| Component | Status |
|---|---|
| Local-contrast text mask | Offline Python reference, PR #194 |
| Bounded text-angle estimator | Offline Python reference, PR #195 |
| Content-region bounds/decision | Offline Python reference, PR #196 |
| Physical deskew/crop application | Offline Python reference, PR #200 |
| End-to-end geometry normalizer | Offline Python integration, PR #202 |

Не входят в этот блок и не должны добавляться до его targeted audit:

- illumination/shadow normalization;
- glare/blur/capture-quality gates;
- Android camera/runtime integration;
- OCR execution;
- PII redaction;
- provider/serverless job implementation;
- Gemini/LLM integration;
- report persistence.

## 3. Следующий шаг — `ocr-document-geometry-block-audit-v1`

После merge PR #202 разработка первого блока останавливается до комплексной проверки Codex.

Audit scope должен быть **только document geometry block**, а не весь репозиторий:

- PR #194 — text/ink mask;
- PR #195 — angle estimator;
- PR #196 — content-region bounds;
- PR #200 — full-resolution deskew/crop;
- PR #202 — end-to-end integration;
- соответствующие текущие implementation/tests на audit end SHA.

Codex должен проверить как единый блок:

1. EXIF orientation и согласованность coordinate spaces;
2. preview/full-resolution scaling и rounding;
3. знак угла и порядок rotation/crop;
4. сохранность текста и отсутствие опасного обрезания краёв;
5. fail-safe behavior при low confidence, blank/noise и противоречивых stage contracts;
6. hostile input и resource bounds;
7. достаточность synthetic/integration tests и пробелы real-photo validation;
8. cross-PR contract drift и duplicated/inconsistent assumptions;
9. security/privacy impact только этого блока.

Не включать в этот audit OCR engines, PII subsystem, serverless/provider implementation, Android UX, Contract Question Engine, отчёты или другие подсистемы проекта.

Результаты:

- `BATCH AUDIT CLEAR` → geometry block считается frozen; затем владелец продукта выбирает следующий bounded product step;
- `CORRECTIVE PR REQUIRED` → только bounded исправления найденных дефектов этого блока;
- `FREEZE AFFECTED AREA` → блок остаётся замороженным до решения владельца.

## 4. Review and merge policy

GitHub Actions остаются best-effort diagnostics и не входят в blocking contour.

Каждый PR требует до Ready/merge recommendation:

1. focused tests на exact final branch version, когда применимо;
2. assistant self-audit scope/diff/state/credentials/raw-data/generated-files;
3. mandatory final-diff security review по `SECURITY.md` с `Security review: PASS`;
4. явное решение владельца продукта о merge.

Individual Codex review перед каждым PR не требуется.

## 5. Privacy and security boundary

Restricted raw/transient material может существовать только в:

- user device;
- encrypted transport;
- approved encrypted short-lived job storage when needed;
- volatile authorized worker memory;
- bounded transient worker files only when unavoidable and automatically deleted.

Original images, raw OCR и PII-bearing payload могут входить только в явно approved infrastructure physically located in Israel. Любой неразрешённый endpoint/region должен fail closed до upload/job creation; automatic fallback/retry/replication outside Israel запрещены.

Raw images/raw OCR запрещены в Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable и unrelated services. Only sanitized derivatives may proceed to legal analysis.

Final reports не являются zero-retention objects. Их persistent storage разрешён только для sanitized analysis/evidence без original images, raw OCR, recoverable PII, secrets или reversible hidden layers и только с exact account-scoped authorization, encryption, deletion и defined backup lifecycle.

Production остаётся blocked до реализации и проверки consent, authentication, report authorization, key lifecycle, approved Israel-only provider behavior, retention/deletion, log scrubbing, cleanup, backup lifecycle, legal review, abuse controls and incident response.

## 6. Дальнейшая архитектурная последовательность

После успешного geometry-block audit canonical state выберет следующий step отдельным решением владельца продукта.

Serverless GPU OCR viability benchmark остаётся обязательным gate до production remote OCR. Он не был отменён PR #202; устранено только устаревшее дублирование current `next_step_id` в нескольких binding docs.

`FUTURE_PRODUCT_AND_ARCHITECTURE_IDEAS.md` остаётся non-binding backlog будущих продуктовых/архитектурных направлений и не расширяет scope текущего блока автоматически.

## 7. Правила восстановления и работы

Перед новой privacy/OCR веткой:

1. прочитать current binding sources с `main`, включая `SECURITY.md`;
2. проверить отсутствие overlapping open PRs;
3. опубликовать exact Context Gate v1;
4. менять только declared paths и approved bounded step;
5. обновить оба state-файла фактическим номером PR;
6. выполнить final validation на exact final head SHA;
7. провести assistant self-audit и отдельный `Security review: PASS`;
8. не merge без явного решения владельца продукта.

Последний полный cold-start audit: PR #177 после merge PR #176.

Следующий целевой audit после PR #202: только `ocr-document-geometry-block-audit-v1`.
