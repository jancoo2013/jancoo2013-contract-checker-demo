# OCR Project State & Continuity v0

Последнее обновление: 2026-08-06, PR #198, `pr-context-gate-canary-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий implementation-шаг: `ocr-content-region-deskew-crop-v1`, но начинать его можно только после успешного автоматического и ручного canary-run PR #198 и возврата `validate-context` в required checks.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Подробная история PR #190–#197 сохраняется в Git history и описаниях соответствующих PR.

## 0. Изменение PR #198

- Добавлен минимальный документационный canary `pr-context-gate-canary-v1` для workflow из merged PR #197.
- Canary не меняет workflow, validator, product/runtime code, OCR, Android, изображения, зависимости, provider integration, upload, encryption, PII, Gemini или storage.
- Успех требует автоматического `PR context gate / validate-context` на exact final head SHA и отдельного успешного `workflow_dispatch` для PR #198.
- Run IDs и exact-head evidence фиксируются в PR description/conversation, чтобы не создавать новый commit SHA после наблюдаемого запуска.
- `validate-context` остаётся необязательным до подтверждения обоих запусков.
- После merge canary проверка возвращается в required checks; затем разрешён `ocr-content-region-deskew-crop-v1`.

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
| Physical deskew/crop application | Not implemented |
| Perspective correction | Not implemented in the active runtime path |
| Illumination/shadow normalization | Not implemented |
| Glare/blur quality gates | Not implemented |
| Android realtime capture analyzer | Not implemented |
| Surya quality/geometry oracle | Synthetic oracle implemented, PR #191 |
| Actual Surya GPU/provider viability result | Not measured |

The next image-processing implementation remains `ocr-content-region-deskew-crop-v1`, paused until the CI canary succeeds and the required check is restored.

## 3. GitHub Actions gate status

Current policy:

1. `validate-context` is temporarily not required by the `main` ruleset.
2. PR #198 is the canary against the dependency-free workflow merged in PR #197.
3. The canary passes only if `PR context gate / validate-context` appears automatically and succeeds on the exact final head SHA.
4. Manual `workflow_dispatch` must also successfully validate PR #198.
5. Only after both observations may PR #198 be merged and `validate-context` restored as a required check.
6. A missing, permanently queued, skipped, cancelled, failed, or stale-head status is not a successful canary.

The workflow remains fail-closed for undeclared paths and invalid state continuity. It does not prove semantic correctness of implementation code.

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

До начала implementation обязательно:

- автоматический canary-run PR #198 завершён успешно на exact final head;
- ручной `workflow_dispatch` для PR #198 завершён успешно;
- PR #198 merged;
- `validate-context` снова добавлен в required checks для `main`.

После этого разрешён bounded deskew/crop step, который применяет rotation/crop только при accepted upstream decisions и сохраняет full frame при любой неопределённости.

```text
restore validate-context as required
→ ocr-content-region-deskew-crop-v1
→ illumination/shadow normalization
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
5. открыть draft PR, затем обновить оба state-файла фактическим номером;
6. выполнить focused validation на exact final head SHA;
7. проверить diff, state continuity, credentials, raw data, generated files и auto-merge;
8. не merge без явного решения владельца продукта.

Последний полный cold-start audit: PR #177 после merge PR #176.
