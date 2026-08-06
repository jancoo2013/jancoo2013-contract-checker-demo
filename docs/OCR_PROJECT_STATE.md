# OCR Project State & Continuity v0

Последнее обновление: 2026-08-06, PR #199, `record-failed-context-gate-canary-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий обязательный шаг: `github-actions-trigger-settings-audit-v1`. До его завершения `validate-context` остаётся необязательным, а `ocr-content-region-deskew-crop-v1` приостановлен.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Подробная история сохраняется в Git history и описаниях PR.

## 0. Изменение PR #199

- PR #198 был ошибочно merged после того, как canary уже дал отрицательный результат.
- Для exact head `6d6406c352a353cfdc3c5a8ce804c288d1cfd58b` не появился ни один автоматический `PR context gate / validate-context` run.
- Отсутствие запуска подтверждено отдельно после событий `opened` и `edited`; head SHA между проверками не менялся.
- Успешный ручной `workflow_dispatch` для PR #198 не подтверждён.
- Merge PR #198 изменил только документацию и state; runtime, workflow, OCR, Android, изображения и privacy boundary не менялись.
- `validate-context` нельзя возвращать в required checks.
- Следующий шаг — аудит repository-level GitHub Actions settings и статуса workflow, затем новый canary PR.

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
| Physical deskew/crop application | Not implemented; paused by CI incident |
| Perspective correction | Not implemented in active runtime path |
| Illumination/shadow normalization | Not implemented |
| Glare/blur quality gates | Not implemented |
| Android realtime capture analyzer | Not implemented |
| Surya quality/geometry oracle | Synthetic oracle implemented, PR #191 |
| Actual Surya GPU/provider viability result | Not measured |

## 3. GitHub Actions gate status

Current facts:

1. Dependency-free `PR context gate` workflow exists in `main` after PR #197.
2. Job ID remains `validate-context`.
3. PR #198 did not create an automatic workflow run for `opened` or `edited`.
4. This means the canary failed before validator execution; correctness of validator logic was not tested end to end.
5. `validate-context` remains absent from required checks.
6. No implementation PR may rely on this gate until a fresh canary succeeds.

The next audit must verify in the GitHub UI:

- repository **Settings → Actions → General** allows Actions to run;
- allowed-actions policy does not disable the workflow;
- `PR context gate` is enabled on the Actions page;
- a manual `workflow_dispatch` run can be started from `main`;
- the resulting run reaches job execution rather than remaining absent;
- after settings are corrected, a new documentation-only canary gets an automatic green `validate-context` on its exact head.

## 4. Privacy boundary

Raw material may exist only in:

- user device;
- encrypted transport;
- encrypted short-lived job storage when needed;
- volatile authorized worker memory;
- bounded transient worker files only when unavoidable and automatically deleted.

Raw images and raw OCR remain prohibited in Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable and unrelated services. Only sanitized derivatives may proceed to legal analysis.

Production remains blocked until consent, authentication, key lifecycle, approved region/provider behavior, retention/deletion, log scrubbing, cleanup, legal review and incident response are separately defined and verified.

## 5. Следующий шаг — `github-actions-trigger-settings-audit-v1`

Порядок:

1. проверить repository-level Actions settings и enabled-state workflow;
2. запустить `workflow_dispatch` вручную для диагностического PR или нового canary;
3. исправить настройки, если run не создаётся;
4. открыть новый минимальный canary PR;
5. подтвердить автоматический и ручной green run на exact head;
6. только затем вернуть `validate-context` в required checks;
7. после этого продолжить `ocr-content-region-deskew-crop-v1`.

## 6. Правила восстановления и работы

Перед новой privacy/OCR веткой:

1. прочитать binding sources с актуального `main`;
2. проверить отсутствие overlapping open PRs;
3. опубликовать exact Context Gate v1;
4. менять только declared paths и approved bounded step;
5. обновить оба state-файла фактическим номером PR;
6. выполнить focused validation на exact final head SHA;
7. проверить diff, credentials, raw data, generated files и auto-merge;
8. не merge без явного решения владельца продукта.

Последний полный cold-start audit: PR #177 после merge PR #176.
