# OCR Project State & Continuity v0

Последнее обновление: 2026-08-09, PR #205, `ocr-geometry-resource-budget-v1`.

Активный трек: `serverless-gpu-ocr`.

Следующий bounded-шаг после merge PR #205: `ocr-document-geometry-block-reaudit-v1`.

Этот документ — каноническая operational-точка восстановления privacy/OCR-проекта. Только он вместе с `docs/OCR_PROJECT_STATE.json` выбирает текущий `next_step_id`; архитектурные документы задают границы и обязательные будущие gates, но не выбирают следующий PR самостоятельно.

## 0. Изменение PR #205

PR #205 — третий и последний bounded corrective после focused Codex audit document geometry block.

Исправляется finding #3: прежний общий лимит `150_000_000` source pixels был конечным, но не задавал практически ограниченный memory contract для full-resolution EXIF/convert/rotation/crop path.

Изменение:

- добавлен единый `geometry_resource_budget.py` для текущего offline Python reference runtime;
- абсолютный source-pixel cap снижен до `32_000_000`;
- максимальная отдельная dimension ограничена `8192` pixels;
- введён mode-aware accounted peak-memory ceiling `384 MiB`;
- accounting различает modes, которые physical transform обрабатывает нативно, и modes, требующие full-resolution RGB conversion;
- resource metadata проверяется до `ImageOps.exif_transpose`, grayscale conversion и physical full-resolution transform copies;
- неизвестные/unaccounted PIL modes fail closed;
- preview path и direct physical-transform API используют один resource contract;
- boundary tests не создают изображения максимального размера: limits проверяются по size/mode metadata;
- модель является консервативным accounting contract, а не заявлением о точно измеренном RSS/Pillow allocator peak.

Этот guard ограничивает дополнительные geometry operations над переданным PIL image. Он не является отдельной гарантией того, сколько памяти уже потратил внешний decoder до передачи image в API; production capture/decode path должен сохранять собственные pre-decode/input limits.

Geometry block остаётся frozen до повторного targeted Codex audit.

## 1. Focused Codex audit — corrective status

Исходный audit endpoint:

`6b30b0a66ccebf8efac49b1b368039ca453519cc` — merge PR #202.

Исходный audit scope был намеренно ограничен только document geometry block:

- PR #194 — text/ink mask;
- PR #195 — text-angle estimator;
- PR #196 — content-region bounds;
- PR #200 — full-resolution deskew/crop;
- PR #202 — end-to-end geometry normalizer.

Codex outcome: `FREEZE AFFECTED AREA`.

Найденные findings и corrective status:

1. **BLOCKING — disconnected legitimate content could be cropped away.**
   - Corrected by PR #203.
2. **CORRECTIVE — contradictory manually constructed `accepted` stage contracts could authorize physical crop.**
   - Corrected by PR #204.
3. **CORRECTIVE — inherited 150M source-pixel limit did not prove a practical full-resolution memory budget.**
   - Corrected by PR #205, subject to targeted re-audit.

Ни один finding не считается окончательно закрытым для freeze только на основании self-review. Geometry block должен пройти повторный targeted Codex audit на актуальном `main` после merge PR #205.

## 2. Первый блок — document geometry normalization

Текущий contract:

```text
source PIL image
→ validate bounded source dimensions/mode/accounted memory
→ EXIF orientation inside preview/transform contracts
→ local-contrast text/ink mask
→ bounded dominant text-angle estimate
→ bounded content-region decision
→ validate accepted stage-contract consistency
→ full-resolution deskew + conservative crop only when fully accepted
→ otherwise full-frame fail-safe
→ DocumentGeometryNormalizationResult
```

Компоненты:

| Component | Status |
|---|---|
| Geometry resource budget | Offline Python reference, PR #205 |
| Local-contrast text mask | Offline Python reference, PR #194; shared resource guard PR #205 |
| Bounded text-angle estimator | Offline Python reference, PR #195 |
| Content-region bounds/decision | Offline Python reference, PR #196; disconnected-content corrective PR #203 |
| Physical deskew/crop application | Offline Python reference, PR #200; accepted-contract corrective PR #204; shared resource guard PR #205 |
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

## 3. Следующий шаг — `ocr-document-geometry-block-reaudit-v1`

После merge PR #205 разработка preprocessing снова останавливается.

Codex должен повторно проверить **только document geometry block**, не весь repository. Audit должен учитывать актуальный код после corrective PRs #203, #204 и #205 и исходные implementation PRs #194, #195, #196, #200 и #202.

Основные вопросы re-audit:

1. устранён ли риск удаления disconnected legitimate content;
2. fail-closed ли contradictory accepted contracts;
3. действительно ли новый source/resource contract выполняется до дорогих full-resolution copies и разумно ограничивает mode-specific memory amplification;
4. не создали ли corrective PRs новые coordinate, EXIF, crop, fallback или resource regressions;
5. достаточны ли synthetic/adversarial tests для freeze этого блока.

Допустимые outcomes:

- `BATCH AUDIT CLEAR` → первый geometry block можно считать frozen/закрытым и только после этого выбрать следующий product step;
- `CORRECTIVE PR REQUIRED` → исправлять только конкретные defects этого же блока;
- `FREEZE AFFECTED AREA` → блок остаётся frozen.

До результата re-audit не начинать illumination/shadow, OCR, PII, Android, provider/serverless или другие соседние направления.

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

Serverless GPU OCR viability benchmark remains a required future gate. It is not part of the frozen geometry corrective/re-audit sequence.

## 5. Review and merge policy

GitHub Actions остаются best-effort diagnostics и не входят в blocking contour.

Каждый PR требует до Ready/merge recommendation:

1. focused tests на exact final branch version, когда применимо;
2. assistant self-audit scope/diff/state/credentials/raw-data/generated-files;
3. mandatory final-diff security review по `SECURITY.md` с `Security review: PASS`;
4. явное решение владельца продукта о merge.

Individual Codex review перед каждым PR не требуется. Codex используется для целевых/batch audits, включая следующий geometry re-audit.

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

Следующий audit: targeted geometry re-audit после merge PR #205.
