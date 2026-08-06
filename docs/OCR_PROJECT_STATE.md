# OCR Project State & Continuity v0

Последнее обновление: 2026-08-06, PR #199, `adopt-codex-review-fallback-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий bounded implementation-шаг: `ocr-content-region-deskew-crop-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Подробная история сохраняется в Git history и описаниях PR.

## 0. Изменение PR #199

- Владелец продукта решил прекратить блокировать разработку из-за нестабильной очереди GitHub Actions.
- `validate-context` остаётся необязательным и не должен блокировать merge.
- GitHub Actions сохраняются как best-effort diagnostics, но не считаются обязательным доказательством готовности PR.
- Обязательный контур проверки каждого implementation PR:
  1. focused local tests на финальной версии ветки;
  2. self-audit diff, scope, state continuity, credentials, raw data и generated files;
  3. фактически завершённый review в Codex;
  4. явное решение владельца продукта о merge.
- Если Codex review не выполнен из-за лимита аккаунта или временной недоступности, PR не считается проверенным до фактического завершения review.
- PR #198 изменил только документацию и state; runtime и workflow code не пострадали.
- Следующий разрешённый шаг снова `ocr-content-region-deskew-crop-v1`.

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
| Physical deskew/crop application | Next bounded step |
| Perspective correction | Not implemented in active runtime path |
| Illumination/shadow normalization | Not implemented |
| Glare/blur quality gates | Not implemented |
| Android realtime capture analyzer | Not implemented |
| Surya quality/geometry oracle | Synthetic oracle implemented, PR #191 |
| Actual Surya GPU/provider viability result | Not measured |

## 3. Проверочный контур PR

Для каждого следующего PR обязательно:

1. exact Context Gate v1 в описании PR;
2. изменения только в declared paths;
3. focused tests и syntax/import checks на final head;
4. проверка полного diff и отсутствие посторонних файлов;
5. обновление обоих state-файлов;
6. отдельный Codex review с разбором найденных замечаний;
7. merge только после явного решения владельца продукта.

GitHub Actions могут запускаться, стоять в очереди, завершаться или отсутствовать. Их состояние не блокирует работу и не заменяет перечисленные проверки.

## 4. Privacy boundary

Raw material may exist only in:

- user device;
- encrypted transport;
- encrypted short-lived job storage when needed;
- volatile authorized worker memory;
- bounded transient worker files only when unavoidable and automatically deleted.

Raw images and raw OCR remain prohibited in Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable and unrelated services. Only sanitized derivatives may proceed to legal analysis.

Production remains blocked until consent, authentication, key lifecycle, approved region/provider behavior, retention/deletion, log scrubbing, cleanup, legal review and incident response are separately defined and verified.

## 5. Следующий шаг — `ocr-content-region-deskew-crop-v1`

Этот bounded step может:

- применить rotation только при accepted angle decision;
- применить crop только при accepted content-bounds decision;
- сохранить полный кадр при любой неопределённости;
- вернуть явный transformation result и причины fallback.

Он не может добавлять Surya/provider calls, Android upload, production encryption, PII handoff, Gemini calls или permanent storage.

После него:

```text
illumination/shadow normalization
→ glare/blur/capture-quality gates
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
7. провести self-audit и Codex review;
8. не merge без явного решения владельца продукта.

Последний полный cold-start audit: PR #177 после merge PR #176.
