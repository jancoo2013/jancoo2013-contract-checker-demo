# OCR Project State & Continuity v0

Последнее обновление: 2026-08-09, PR #203, `ocr-content-region-disconnected-content-failsafe-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий bounded-шаг после merge PR #203: `ocr-geometry-transform-contract-validation-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Только он вместе с `docs/OCR_PROJECT_STATE.json` выбирает текущий `next_step_id`; архитектурные документы задают границы и обязательные будущие gates, но не выбирают следующий PR самостоятельно.

## 0. Изменение PR #203

PR #203 — первый bounded corrective после focused Codex audit document geometry block.

Исправляется только блокирующий finding аудита: прежний content-region algorithm мог выбрать доминирующую группу строк, принять crop и удалить легитимный disconnected content вне этой группы, включая вторую колонку или короткую строку у края страницы.

Изменение:

- перед `accepted` crop deskewed preview проверяется вне padded candidate;
- дополнительный горизонтальный line-like foreground вне candidate добавляет reason `disconnected_content_outside_crop`;
- такой случай переводит content-region decision в `rotation_only`;
- существующий physical-transform contract для `rotation_only` сохраняет полный EXIF-нормализованный кадр без частичного transform;
- narrow vertical side noise по-прежнему не считается достаточным основанием для отказа от crop;
- добавлены synthetic unit/integration cases для двух колонок, disconnected header/footer и короткого edge content;
- OCR, PII, Android, illumination/shadow, provider/serverless, Gemini, upload, encryption, persistence, network и dependencies не меняются.

Geometry block остаётся frozen. PR #203 не закрывает два других finding аудита.

## 1. Focused Codex audit — результат

Audit endpoint:

`6b30b0a66ccebf8efac49b1b368039ca453519cc` — merge PR #202.

Audit scope был намеренно ограничен только document geometry block:

- PR #194 — text/ink mask;
- PR #195 — text-angle estimator;
- PR #196 — content-region bounds;
- PR #200 — full-resolution deskew/crop;
- PR #202 — end-to-end geometry normalizer.

Codex outcome: `FREEZE AFFECTED AREA`.

Найдено три concrete finding:

1. **BLOCKING — disconnected legitimate content could be cropped away.**
   - Исправляется PR #203.
2. **CORRECTIVE — contradictory manually constructed `accepted` stage contracts can still authorize physical crop.**
   - Следующий bounded corrective: `ocr-geometry-transform-contract-validation-v1`.
3. **CORRECTIVE — inherited 150M source-pixel limit is finite but does not prove an acceptable worst-case memory budget for full-resolution PIL operations.**
   - Отдельный последующий corrective: `ocr-geometry-resource-budget-v1`.

После завершения этих corrective PR geometry block должен пройти повторный targeted Codex audit. Только `BATCH AUDIT CLEAR` на исправленном end SHA разрешает снять freeze с первого блока.

## 2. Первый блок — document geometry normalization

Текущий contract:

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

Компоненты:

| Component | Status |
|---|---|
| Local-contrast text mask | Offline Python reference, PR #194 |
| Bounded text-angle estimator | Offline Python reference, PR #195 |
| Content-region bounds/decision | Offline Python reference, PR #196; disconnected-content corrective PR #203 |
| Physical deskew/crop application | Offline Python reference, PR #200 |
| End-to-end geometry normalizer | Offline Python integration, PR #202 |

Не входят в этот block и не должны добавляться до его clean re-audit:

- illumination/shadow normalization;
- glare/blur/capture-quality gates;
- perspective correction;
- Android camera/runtime integration;
- OCR execution;
- PII redaction;
- provider/serverless job implementation;
- Gemini/LLM integration;
- report persistence.

## 3. Следующий шаг — `ocr-geometry-transform-contract-validation-v1`

После merge PR #203 разрешён только второй corrective из focused audit.

Цель: physical deskew/crop API должен reject/fail safe на internally contradictory `accepted` objects вместо того, чтобы доверять одному только значению `decision="accepted"`.

Scope следующего corrective не должен включать resource-budget finding, изменение content-region heuristic, новый preprocessing или другие subsystem changes.

После него отдельным PR должен быть рассмотрен `ocr-geometry-resource-budget-v1`, затем повторный targeted geometry audit.

## 4. Активная целевая цепочка продукта

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

Serverless GPU OCR viability benchmark remains a required future gate. It is not part of the frozen geometry corrective sequence.

## 5. Review and merge policy

GitHub Actions остаются best-effort diagnostics и не входят в blocking contour.

Каждый PR требует до Ready/merge recommendation:

1. focused tests на exact final branch version, когда применимо;
2. assistant self-audit scope/diff/state/credentials/raw-data/generated-files;
3. mandatory final-diff security review по `SECURITY.md` с `Security review: PASS`;
4. явное решение владельца продукта о merge.

Individual Codex review перед каждым PR не требуется.

## 6. Privacy and security boundary

Restricted raw/transient material может существовать только в user device, encrypted transport, approved encrypted short-lived job storage when needed, volatile authorized worker memory и bounded transient worker files when unavoidable and automatically deleted.

Original images, raw OCR и PII-bearing payload могут входить только в явно approved infrastructure physically located in Israel. Любой неразрешённый endpoint/region должен fail closed до upload/job creation; automatic fallback/retry/replication outside Israel запрещены.

Raw images/raw OCR запрещены в Gemini, general OCR/LLM APIs, logs, analytics, crash reports, GitHub, CI, Airtable и unrelated services. Only sanitized derivatives may proceed to legal analysis.

Final reports не являются zero-retention objects. Persistent storage разрешён только для sanitized analysis/evidence без original images, raw OCR, recoverable PII, secrets или reversible hidden layers и только с exact account-scoped authorization, encryption, deletion и defined backup lifecycle.

Production остаётся blocked до реализации и проверки consent, authentication, report authorization, key lifecycle, approved Israel-only provider behavior, retention/deletion, log scrubbing, cleanup, backup lifecycle, legal review, abuse controls and incident response.

## 7. Правила восстановления и работы

Перед новой privacy/OCR веткой:

1. прочитать current binding sources с `main`, включая `SECURITY.md`;
2. проверить отсутствие overlapping open PRs;
3. опубликовать exact Context Gate v1;
4. менять только declared paths и approved bounded step/corrective;
5. обновить оба state-файла фактическим номером PR;
6. выполнить final validation на exact final head SHA;
7. провести assistant self-audit и отдельный `Security review: PASS`;
8. не merge без явного решения владельца продукта.

Последний полный repository cold-start audit: PR #177 после merge PR #176.

Последний focused geometry audit: Codex at `6b30b0a66ccebf8efac49b1b368039ca453519cc`, outcome `FREEZE AFFECTED AREA`.
