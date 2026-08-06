# OCR Project State & Continuity v0

Последнее обновление: 2026-08-06, PR #197, `restore-pr-context-gate-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий обязательный шаг: `pr-context-gate-canary-v1`. До успешного canary-run проверка `validate-context` остаётся необязательной. После подтверждённого зелёного запуска её нужно снова сделать required и вернуться к `ocr-content-region-deskew-crop-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Подробная история PR #190–#196 сохраняется в Git history и описаниях соответствующих PR.

## 0. Изменение PR #197

- Workflow `PR context gate` сохранён с прежним job ID `validate-context`.
- Удалена зависимость от скачиваемых `actions/checkout` и `actions/setup-python`, на разрешении которых последний реальный запуск был отменён до выполнения валидатора.
- Exact base/head snapshots загружаются через GitHub REST API встроенными `curl` и `tar`; Python берётся из стандартного GitHub-hosted runner.
- Автоматический trigger остаётся `pull_request_target`, поэтому workflow и исполняемый validator берутся из trusted default branch.
- Candidate revision извлекается только как данные; выполняется исключительно `trusted/scripts/check_pr_context_gate.py`.
- Добавлен `workflow_dispatch` с положительным целочисленным `pr_number` для ручной post-merge диагностики.
- Permissions остаются read-only: `contents: read`, `pull-requests: read`.
- Добавлен dependency-free structural test workflow-контракта; focused suite: 5/5.
- Этот PR не может доказать собственный end-to-end trigger: `pull_request_target` использует workflow из `main`. После merge обязателен отдельный canary PR.
- Runtime приложения, OCR, Android, изображения, upload, encryption, PII, Gemini, provider calls и storage не изменены.

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

The next image-processing implementation remains `ocr-content-region-deskew-crop-v1`, but it is paused until the CI canary succeeds.

## 3. GitHub Actions gate status

Current policy:

1. `validate-context` is temporarily not required by the `main` ruleset.
2. PR #197 must be merged manually while that requirement is absent.
3. A small `pr-context-gate-canary-v1` PR must then be opened against the merged workflow.
4. The canary passes only if `PR context gate / validate-context` appears automatically and succeeds on the exact canary head SHA.
5. Manual `workflow_dispatch` should also successfully validate that PR number.
6. Only after both observations may `validate-context` be restored as a required check.
7. A missing, permanently queued, skipped, cancelled, or stale-head status is not a successful canary.

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

## 5. Следующий шаг — `pr-context-gate-canary-v1`

Canary scope должен быть минимальным и не менять product/runtime behavior. Он должен:

- содержать точный Context Gate v1;
- обновить оба state-файла;
- не менять OCR, Android, dependencies, images, PII, provider integration или privacy boundary;
- дождаться автоматического `PR context gate / validate-context` на exact head;
- отдельно пройти manual `workflow_dispatch` по номеру PR;
- зафиксировать run IDs и итог без преждевременного возврата required-check.

После успешного canary:

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
