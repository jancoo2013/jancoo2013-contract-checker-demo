# OCR Project State & Continuity v0

Последнее обновление: 2026-08-06, PR #200, `ocr-content-region-deskew-crop-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий bounded-шаг после merge PR #200: `ocr-illumination-shadow-normalization-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Подробная история сохраняется в Git history и описаниях PR.

## 0. Изменение PR #200

- Добавлен offline Python reference-компонент физического deskew/crop полного изображения.
- Входы — `TextAngleEstimate` из PR #195 и `ContentRegionBounds` из PR #196.
- Поворот и crop применяются только при одновременных `angle.accepted` и `bounds.accepted`.
- `rotation_only`, отклонённый угол и `full_frame_fallback` сохраняют полный EXIF-нормализованный кадр без геометрических изменений.
- Preview bounds отображаются в координаты полного разрешения консервативно: `floor` для левой/верхней границы и `ceil` для правой/нижней.
- Проверяются совпадение углов, coordinate space, preview size, границы crop и существующий лимит исходника 150 млн пикселей.
- Противоречивый или повреждённый upstream-контракт вызывает явную ошибку вместо небезопасного transform.
- Focused suite перед созданием PR: 8/8; `py_compile`: PASS.
- Runtime приложения, Android, OCR engine, provider integration, upload, encryption, PII, Gemini и storage не подключены.

## 1. Активная целевая цепочка

```text
raw phone photos
→ client-side capture-quality checks and normalization
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
```

Tesseract full-page OCR on Samsung A55 remains NO-GO and cannot return as active fallback.

## 2. Реализованные preprocessing reference-компоненты

| Component | Status |
|---|---|
| Local-contrast text mask | Offline Python reference, PR #194 |
| Bounded text-angle estimator | Offline Python reference, PR #195 |
| Content-region bounds/decision | Offline Python reference, PR #196 |
| Physical deskew/crop application | Offline Python reference, PR #200 |
| Perspective correction | Not implemented in active runtime path |
| Illumination/shadow normalization | Next bounded step |
| Glare/blur quality gates | Not implemented |
| Android realtime capture analyzer | Not implemented |
| Surya quality/geometry oracle | Synthetic oracle implemented, PR #191 |
| Actual Surya GPU/provider viability result | Not measured |

## 3. Review and merge policy

GitHub Actions remain enabled but are no longer part of the blocking contour:

- `validate-context` stays non-required;
- queued, delayed, missing or cancelled runs are best-effort diagnostics;
- an Actions result does not replace code review.

Every implementation PR requires before merge:

1. focused local tests on the exact final branch version;
2. assistant self-audit of scope, diff, state continuity, credentials, raw data and generated files;
3. an actually completed Codex review, with findings resolved or explicitly accepted;
4. explicit product-owner merge approval.

A Codex usage-limit message is not a completed review.

## 4. Privacy boundary

Raw material may exist only in:

- user device;
- encrypted transport;
- encrypted short-lived job storage when needed;
- volatile authorized worker memory;
- bounded transient worker files only when unavoidable and automatically deleted.

Raw images and raw OCR remain prohibited in Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable and unrelated services. Only sanitized derivatives may proceed to legal analysis.

Production remains blocked until consent, authentication, key lifecycle, approved Israel-only provider behavior, retention/deletion, log scrubbing, cleanup, legal review and incident response are separately defined and verified.

## 5. Следующий шаг — `ocr-illumination-shadow-normalization-v1`

Следующий PR должен добавить только bounded offline reference-нормализацию неравномерного освещения и мягких теней. Он не должен:

- выполнять OCR;
- подключать Android runtime или камеру;
- вызывать внешнего provider;
- отправлять или сохранять изображения;
- менять PII, Gemini, encryption или production storage.

После него:

```text
glare/blur/capture-quality gates
→ Android realtime capture analyzer
→ controlled real-photo preprocessing validation
→ Surya/provider benchmark
```

## 6. Правила восстановления и работы

Перед новой privacy/OCR веткой:

1. прочитать binding sources с актуального `main`;
2. проверить отсутствие overlapping open PRs;
3. опубликовать exact Context Gate v1;
4. менять только declared paths и approved bounded step;
5. обновить оба state-файла фактическим номером PR;
6. выполнить focused validation на exact final head SHA;
7. провести self-audit и получить завершённый Codex review;
8. не merge без явного решения владельца продукта.

Последний полный cold-start audit: PR #177 после merge PR #176.
